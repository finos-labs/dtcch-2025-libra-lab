import requests
from flask import Flask, render_template, request, session, send_file,send_from_directory, url_for
import json
import uuid
import os
import json
import base64
import requests
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from openai import OpenAI
from PyPDF2 import PdfReader
import azure.cognitiveservices.speech as speechsdk
import base64
import datetime
import html
import json
import numpy as np
import os
import pytz
import random
import re
import requests
import threading
import time
import torch
import traceback
import uuid
from flask import Flask, Response, render_template, request
from flask_socketio import SocketIO, join_room
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from vad_iterator import VADIterator, int2float

app = Flask(__name__)
app.secret_key = 'BAD_SECRET_KEY'
socketio = SocketIO(app)
##FUNCTION STARTS FROM HERE

YOUR_API_KEY = "YOUR API KEY"

client = OpenAI(api_key=YOUR_API_KEY, base_url="https://api.perplexity.ai")


client1 = OpenAI(api_key="YOUR API KEY")

def get_system_message():
    return {
        "role": "system",
        "content": (
            """
            Task:
You are an AI assistant designed to process and extract corporate action (Indian Companies only) reference data for Indian companies listed on the Indian stock market.

Objective:
Ingest data from multiple unstructured and semi-structured sources, including regulatory filings, exchange announcements, emails, and news feeds. Extract key corporate action details such as issuer, event type, event date, affected securities, and additional details.

Requirements:

Source Analysis: Identify and process reliable sources such as:

1. SEBI filings.
2. Stock exchange announcements (e.g., BSE, NSE).
3. Press releases from company websites.
4. News articles and feeds from reputable financial news outlets.
5. Make sure to browse from NSE / BSE website to get recent updates.

Data Extraction Goals: Extract specific details:

Issuer: The name of the company or organization.
Event Type: Types of corporate actions (e.g., dividends, mergers, stock splits, rights issues, etc.).
Affected Securities: Identify securities impacted (e.g., ISIN, stock symbol).
Event Date: Critical dates such as record date, announcement date, and effective date.
Additional Details: Ratios, percentage changes, or special conditions.
Citations: Provide references to the original source for every extracted piece of information to ensure traceability and validation.

Try to get information from official websites as much as possible like NSE, BSE, official company websites.

            """
        ),
    }


def classify_citations(citations):
    user_message = {
        "role": "user",
        "content": (
            f"""You are assigned a task of classifying web urls to one of the classes namely "official" and "not_official".
            You need to carefully look at urls, if the urls are from 3rd party sources, news feeds, etc. If urls are from company's website, NSE, BSE
            or any official websites then it will be put under official category.
            You are provided with a list of citations and you need to return the output in the JSON format. In the Final_Output if first link is official
            you mention it accordingly in first index of list, similarly second link is unofficial you mention it as not_unofficial in second index and goes on

Citations to be classified:
{citations}
"""+
"""Provide output in following JSON Format

{ "Final_Output" : ["official","not_official", "official" etc],
}"""
        )
    }
    completion = client1.chat.completions.create(
        model="gpt-4o",  # or "gpt-3.5-turbo-16k", etc.
        response_format={ "type": "json_object" },
        messages=[user_message]
    )

    return completion.choices[0].message.content.strip()
# Setup Selenium WebDriver (Headless Chrome)
def setup_driver():
    options = Options()
    options.add_argument("--headless")  # Run without opening a browser
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Extract title and favicon from websites
def get_title_favicon(url, use_selenium=False):
    if url.endswith('.pdf'):
        return {"title": url.split("/")[-1].replace(".pdf","").replace("_"," ").replace("-"," "), "favicon": "https://www.adobe.com/favicon.ico", "link": url}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        '''if use_selenium:
            driver = setup_driver()
            driver.get(url)
            time.sleep(3)  # Wait for JavaScript to load
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            driver.quit()
        else:'''
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"title": url.split("/")[-1].split(".")[0].replace("_"," ").replace("-"," "), "favicon": "https://www.moneycontrol.com/favicon.ico", "link": url}
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract Title
        title = soup.find("title").get_text(strip=True) if soup.find("title") else "No Title"

        # Extract Favicon
        favicon_link = soup.find("link", rel=lambda x: x and "icon" in x.lower())
        parsed_url = urlparse(url)

        if favicon_link and "href" in favicon_link.attrs:
            favicon = urljoin(url, favicon_link["href"])  # Handle relative URLs
        else:
            favicon = f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"  # Default favicon path

        return {"title": title, "favicon": favicon, "link": url}

    except Exception as e:
        return {"title": url.split("/")[-1].split(".")[0].replace("_"," ").replace("-"," "), "favicon": "https://www.moneycontrol.com/favicon.ico", "link": url, "error": str(e)}


def extract_text_from_pdf(pdf_path):
    try:
        pdf_reader = PdfReader(pdf_path)
        detected_text = ''

        for page in pdf_reader.pages:
            detected_text += page.extract_text() + '\n\n'

        return detected_text.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return None

# Initial system message
def get_system_message_fake():
    return {
        "role": "system",
        "content": (
            """
            Task:
"You are an AI specializing in financial information. The user has provided a PDF containing financial content and a specific question related to it. Your task is to:

Based on the PDF provided cross check and give detailed explanation, citing sources etc. If the company name does not match with other information in PDF then its fake.
If a user asks Can I invest in that particular stock please do your research and based on results you need to flag if any red flags are found.
Strictly do not mention anything about Date discrepency.

Output Format:
Verdict: Fake / Real
Reasoning: (Explain the verification process, key evidence, and sources used)
            """
        ),
    }
    
def suggest_question(question):
    user_message = {
        "role": "user",
        "content": (
            f"""You are assigned a task of generating related questions based on what question user has asked. This is displayed after fintech based chatbot
            replies to the users query. For example:
            User Query: Has Tata Motors declared a stock split recently?
            Related Questions : What was the last stock split ratio for Tata Motors?
                                When did Tata Motors last announce a stock split?
                                How has Tata Motors' stock performance been since the last split?
                                What are the benefits of a stock split for Tata Motors shareholders?
                                Are there any upcoming stock splits planned for Tata Motors?


Question asked by user:
{question}
"""+
"""Provide output in following JSON Format

{ "related_questions" : []
}"""
        )
    }
    completion = client1.chat.completions.create(
        model="gpt-4o",  # or "gpt-3.5-turbo-16k", etc.
        response_format={ "type": "json_object" },
        messages=[user_message]
    )

    return completion.choices[0].message.content.strip()
    
def avatar_summary(user_question, reply):
    user_message = {
        "role": "user",
        "content": (
            f"""You need to generate a short summary by looking at the query and the reponse given by AI. The short summary generated by you will be
            an input to the AI based human avatar. So try to keep it more a conversation way. Limit the summary to 2-3 lines. Do not go beyond that.

User query:
{user_question}
Response:
{reply}
"""+
"""Provide output in following JSON Format

{ "summary" : ,
}"""
        )
    }
    completion = client1.chat.completions.create(
        model="gpt-4o",  # or "gpt-3.5-turbo-16k", etc.
        response_format={ "type": "json_object" },
        messages=[user_message]
    )

    return completion.choices[0].message.content.strip()
    
@app.route('/')
def query():
    return render_template("home_index.html")
  
@app.route('/chat_page')

def chat_main():
    query = request.args.get('query')
    print(query)
    messages = [get_system_message()]
    messages.append({"role": "user", "content": query})
    response = client.chat.completions.create(
                model="sonar",
                messages=messages,
            )

    # Extract the AI response content
    ai_response = response.choices[0].message.content
    print(f"AI Response: {ai_response}")
    print("Citations: ", response.citations)
    para = ai_response
    
    links = response.citations
    
    cite_state = json.loads(classify_citations(str(links)))["Final_Output"]
    rq = json.loads(suggest_question(query))["related_questions"]
    summary = json.loads(avatar_summary(query,ai_response.strip()))["summary"]
    converted_para = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", para)
    converted_para = re.sub(r"^###\s*(.*)", r"<h3>\1</h3>", converted_para)
    converted_para = re.sub(r"^##\s*(.*)", r"<h2>\1</h2>", converted_para)
    
    new_para = ""
    for i in converted_para.split("\n"):
        
        if "- " in i.strip()[0:2]:
            new_para = new_para+"<dd>&emsp; "+i+"</dd>"
        elif ". " in i.strip()[1:3]:
            new_para = new_para+"<dd>&ensp; "+i+"</dd>"
          
        else:
          new_para = "<p>"+new_para+i+"</p>"
          
    source_data = {"Title":[],"Favicon":[],"Links":[],"Sites":[],"Pdf_Status":[]}
          
    for idx,i in enumerate(links):
      
      new_para = new_para.replace("["+str(idx+1)+"]",'<a style="color:yellow;" href="'+i+'">'+"["+str(idx+1)+"]"+"</a>")
      result = get_title_favicon(i, use_selenium=("cbonds.com" in i))
      source_data["Title"].append(result["title"])
      source_data["Favicon"].append(result["favicon"])
      source_data["Links"].append(result["link"])
      source_data["Sites"].append(".".join(i.split("/")[2].replace("www.","").split(".")[0:-1]))
      if i.endswith(".pdf"):
        source_data["Pdf_Status"].append("pdf")
      else:
        source_data["Pdf_Status"].append("link")
        
    source_data["cite_state"]=cite_state
    source_data["related_questions"] = rq
    source_data["summary"] = summary
        
    print(new_para)
    messages.append({"role": "assistant", "content": ai_response})
    
    
    
    
    
    return render_template("index.html",info={"para":new_para,"query":query,"messages":messages,"query_no":0},sd = source_data,methods=["GET"], client_id=initializeClient())
    
    
@app.route('/follow_up_query',methods=["POST"])

def follow_up_chat():
    query = request.json['query']
    messages = request.json["messages"]
    messages.append({"role": "user", "content": query})
    #print(query)
    #messages = [get_system_message()]
    #messages.append({"role": "user", "content": query})
    print(messages)
    response = client.chat.completions.create(
                model="sonar",
                messages=messages,
            )

    # Extract the AI response content
    ai_response = response.choices[0].message.content
    print(f"AI Response: {ai_response}")
    print("Citations: ", response.citations)
    para = ai_response
    
    links = response.citations
    cite_state = json.loads(classify_citations(str(links)))["Final_Output"]
    rq = json.loads(suggest_question(query))["related_questions"]
    converted_para = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", para)
    converted_para = re.sub(r"^###\s*(.*)", r"<h3>\1</h3>", converted_para)
    converted_para = re.sub(r"^##\s*(.*)", r"<h2>\1</h2>", converted_para)
    
    new_para = ""
    for i in converted_para.split("\n"):
        
        if "- " in i.strip()[0:2]:
            new_para = new_para+"<dd>&emsp; "+i+"</dd>"
        elif ". " in i.strip()[1:3]:
            new_para = new_para+"<dd>&ensp; "+i+"</dd>"
          
        else:
          new_para = "<p>"+new_para+i+"</p>"
          
    source_data = {"Title":[],"Favicon":[],"Links":[],"Sites":[],"Pdf_Status":[]}
          
    for idx,i in enumerate(links):
      
      new_para = new_para.replace("["+str(idx+1)+"]",'<a style="color:yellow;" href="'+i+'">'+"["+str(idx+1)+"]"+"</a>")
      result = get_title_favicon(i, use_selenium=("cbonds.com" in i))
      source_data["Title"].append(result["title"])
      source_data["Favicon"].append(result["favicon"])
      source_data["Links"].append(result["link"])
      source_data["Sites"].append(".".join(i.split("/")[2].replace("www.","").split(".")[0:-1]))
      if i.endswith(".pdf"):
        source_data["Pdf_Status"].append("pdf")
      else:
        source_data["Pdf_Status"].append("link")
    print(new_para)
    
    messages.append({"role": "assistant", "content": ai_response})
    source_data["para"] = new_para
    source_data["query"]=query
    source_data["messages"]=messages    
    source_data["query_no"]=request.json["query_no"] +1
    source_data["cite_state"]=cite_state
    source_data["related_questions"] = rq
    
    return source_data
    
@app.route('/pdf_save',methods=["POST"])
def pdf_Data():

  filename = list(request.files.keys())[0]
  file_data = request.files[filename]
  file_data.save("static/pdf_files/"+filename)
  session["filename"] = "static/pdf_files/"+filename
  print(session["filename"])
    
  pdf_url = url_for('static', filename="pdf_files/"+filename)
  session["url"] = pdf_url

  print(request.files)
  
  return "success"
  
@app.route('/audio_save',methods=["POST"])
def audio_Data():

  myuuid = uuid.uuid4()
  filename = str(myuuid) +".wav"
  file_data = request.files["audio_data"]
  file_data.save("audio_files/"+filename)
  session["filename_audio"] = "audio_files/"+filename
  audio_file= open("audio_files/"+filename, "rb")
  transcription = client1.audio.translations.create(
      model="whisper-1",
      file=audio_file,
  )

  final_trans = transcription.text

  print(request.files)
  
  return {"message":"success","transcript":final_trans}
  
@app.route('/fake_detection')
def fraud():
    return render_template("fraud_home.html")
    
@app.route('/news_feed')
def news():
    return render_template("news_index.html")
    
    
@app.route('/fake_chat_page')

def fraud_chat():
    query = request.args.get('query')
    print(query)
    pdf_text = extract_text_from_pdf(session["filename"])
    messages = [get_system_message_fake()]
    messages.append({
        "role": "user",
        "content": f"The following is the extracted text from the PDF:\n\n{pdf_text}\n\nUser's question: {query}"
    })
    response = client.chat.completions.create(
                model="sonar-pro",
                messages=messages,
            )

    # Extract the AI response content
    ai_response = response.choices[0].message.content
    print(f"AI Response: {ai_response}")
    print("Citations: ", response.citations)
    para = ai_response
    
    links = response.citations
    
    cite_state = json.loads(classify_citations(str(links)))["Final_Output"]
    
    converted_para = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", para)
    converted_para = re.sub(r"^###\s*(.*)", r"<h3>\1</h3>", converted_para)
    converted_para = re.sub(r"^##\s*(.*)", r"<h2>\1</h2>", converted_para)
    
    new_para = ""
    for i in converted_para.split("\n"):
        
        if "- " in i.strip()[0:2]:
            new_para = new_para+"<dd>&emsp; "+i+"</dd>"
        elif ". " in i.strip()[1:3]:
            new_para = new_para+"<dd>&ensp; "+i+"</dd>"
          
        else:
          new_para = "<p>"+new_para+i+"</p>"
          
    source_data = {"Title":[],"Favicon":[],"Links":[],"Sites":[],"Pdf_Status":[]}
          
    for idx,i in enumerate(links):
      
      new_para = new_para.replace("["+str(idx+1)+"]",'<a style="color:yellow;" href="'+i+'">'+"["+str(idx+1)+"]"+"</a>")
      result = get_title_favicon(i, use_selenium=("cbonds.com" in i))
      source_data["Title"].append(result["title"])
      source_data["Favicon"].append(result["favicon"])
      source_data["Links"].append(result["link"])
      source_data["Sites"].append(".".join(i.split("/")[2].replace("www.","").split(".")[0:-1]))
      if i.endswith(".pdf"):
        source_data["Pdf_Status"].append("pdf")
      else:
        source_data["Pdf_Status"].append("link")
        
    source_data["cite_state"]=cite_state
        
    print(new_para)
    messages.append({"role": "assistant", "content": ai_response})
    
    with open(session["filename"], 'rb') as file:
        blob_data1 = file.read()
    blob_dat=base64.b64encode(blob_data1).decode('utf-8') 
    
    
    
    return render_template("fraud_main.html",info={"para":new_para,"query":query,"messages":messages,"url":blob_dat,"query_no":0},sd = source_data)
    

speech_region = "westus2" # e.g. westus2
speech_key = "Your API Key"
speech_private_endpoint = os.environ.get('SPEECH_PRIVATE_ENDPOINT') # e.g. https://my-speech-service.cognitiveservices.azure.com/ (optional)
speech_resource_url = os.environ.get('SPEECH_RESOURCE_URL') # e.g. /subscriptions/6e83d8b7-00dd-4b0a-9e98-dab9f060418b/resourceGroups/my-rg/providers/Microsoft.CognitiveServices/accounts/my-speech (optional, only used for private endpoint)
user_assigned_managed_identity_client_id = os.environ.get('USER_ASSIGNED_MANAGED_IDENTITY_CLIENT_ID') # e.g. the client id of user assigned managed identity accociated to your app service (optional, only used for private endpoint and user assigned managed identity)
# OpenAI resource (required for chat scenario)
azure_openai_endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT') # e.g. https://my-aoai.openai.azure.com/
azure_openai_api_key = os.environ.get('AZURE_OPENAI_API_KEY')
azure_openai_deployment_name = os.environ.get('AZURE_OPENAI_DEPLOYMENT_NAME') # e.g. my-gpt-35-turbo-deployment
# Cognitive search resource (optional, only required for 'on your data' scenario)
cognitive_search_endpoint = os.environ.get('COGNITIVE_SEARCH_ENDPOINT') # e.g. https://my-cognitive-search.search.windows.net/
cognitive_search_api_key = os.environ.get('COGNITIVE_SEARCH_API_KEY')
cognitive_search_index_name = os.environ.get('COGNITIVE_SEARCH_INDEX_NAME') # e.g. my-search-index
# Customized ICE server (optional, only required for customized ICE server)
ice_server_url = os.environ.get('ICE_SERVER_URL') # The ICE URL, e.g. turn:x.x.x.x:3478
ice_server_url_remote = os.environ.get('ICE_SERVER_URL_REMOTE') # The ICE URL for remote side, e.g. turn:x.x.x.x:3478. This is only required when the ICE address for remote side is different from local side.
ice_server_username = os.environ.get('ICE_SERVER_USERNAME') # The ICE username
ice_server_password = os.environ.get('ICE_SERVER_PASSWORD') # The ICE password

# Const variables
enable_websockets = False # Enable websockets between client and server for real-time communication optimization
enable_vad = False # Enable voice activity detection (VAD) for interrupting the avatar speaking
enable_token_auth_for_speech = False # Enable token authentication for speech service
default_tts_voice = 'en-US-JennyMultilingualV2Neural' # Default TTS voice
sentence_level_punctuations = [ '.', '?', '!', ':', ';', '?', '?', '!', ':', ';' ] # Punctuations that indicate the end of a sentence
enable_quick_reply = False # Enable quick reply for certain chat models which take longer time to respond
quick_replies = [ 'Let me take a look.', 'Let me check.', 'One moment, please.' ] # Quick reply reponses
oyd_doc_regex = re.compile(r'\[doc(\d+)\]') # Regex to match the OYD (on-your-data) document reference

# Global variables
client_contexts = {} # Client contexts
speech_token = None # Speech token
ice_token = None # ICE token
if azure_openai_endpoint and azure_openai_api_key:
    azure_openai = AzureOpenAI(
        azure_endpoint=azure_openai_endpoint,
        api_version='2024-06-01',
        api_key=azure_openai_api_key)

# VAD
vad_iterator = None
if enable_vad and enable_websockets:
    vad_model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad')
    vad_iterator = VADIterator(model=vad_model, threshold=0.5, sampling_rate=16000, min_silence_duration_ms=150, speech_pad_ms=100)

# The default route, which shows the default web page (basic.html)


# The API route to get the speech token
@app.route("/api/getSpeechToken", methods=["GET"])
def getSpeechToken() -> Response:
    global speech_token
    response = Response(speech_token, status=200)
    response.headers['SpeechRegion'] = speech_region
    if speech_private_endpoint:
        response.headers['SpeechPrivateEndpoint'] = speech_private_endpoint
    return response

# The API route to get the ICE token
@app.route("/api/getIceToken", methods=["GET"])
def getIceToken() -> Response:
    # Apply customized ICE server if provided
    if ice_server_url and ice_server_username and ice_server_password:
        custom_ice_token = json.dumps({
            'Urls': [ ice_server_url ],
            'Username': ice_server_username,
            'Password': ice_server_password
        })
        return Response(custom_ice_token, status=200)
    return Response(ice_token, status=200)

# The API route to connect the TTS avatar
@app.route("/api/connectAvatar", methods=["POST"])
def connectAvatar() -> Response:
    global client_contexts
    client_id = uuid.UUID(request.headers.get('ClientId'))
    # disconnect avatar if already connected
    disconnectAvatarInternal(client_id)
    client_context = client_contexts[client_id]

    # Override default values with client provided values
    client_context['azure_openai_deployment_name'] = request.headers.get('AoaiDeploymentName') if request.headers.get('AoaiDeploymentName') else azure_openai_deployment_name
    client_context['cognitive_search_index_name'] = request.headers.get('CognitiveSearchIndexName') if request.headers.get('CognitiveSearchIndexName') else cognitive_search_index_name
    client_context['tts_voice'] = request.headers.get('TtsVoice') if request.headers.get('TtsVoice') else default_tts_voice
    client_context['custom_voice_endpoint_id'] = request.headers.get('CustomVoiceEndpointId')
    client_context['personal_voice_speaker_profile_id'] = request.headers.get('PersonalVoiceSpeakerProfileId')

    custom_voice_endpoint_id = client_context['custom_voice_endpoint_id']

    try:
        if speech_private_endpoint:
            speech_private_endpoint_wss = speech_private_endpoint.replace('https://', 'wss://')
            if enable_token_auth_for_speech:
                while not speech_token:
                    time.sleep(0.2)
                speech_config = speechsdk.SpeechConfig(endpoint=f'{speech_private_endpoint_wss}/tts/cognitiveservices/websocket/v1?enableTalkingAvatar=true')
                speech_config.authorization_token = speech_token
            else:
                speech_config = speechsdk.SpeechConfig(subscription=speech_key, endpoint=f'{speech_private_endpoint_wss}/tts/cognitiveservices/websocket/v1?enableTalkingAvatar=true')
        else:
            if enable_token_auth_for_speech:
                while not speech_token:
                    time.sleep(0.2)
                speech_config = speechsdk.SpeechConfig(endpoint=f'wss://{speech_region}.tts.speech.microsoft.com/cognitiveservices/websocket/v1?enableTalkingAvatar=true')
                speech_config.authorization_token = speech_token
            else:
                speech_config = speechsdk.SpeechConfig(subscription=speech_key, endpoint=f'wss://{speech_region}.tts.speech.microsoft.com/cognitiveservices/websocket/v1?enableTalkingAvatar=true')

        if custom_voice_endpoint_id:
            speech_config.endpoint_id = custom_voice_endpoint_id

        client_context['speech_synthesizer'] = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        speech_synthesizer = client_context['speech_synthesizer']
        
        ice_token_obj = json.loads(ice_token)
        # Apply customized ICE server if provided
        if ice_server_url and ice_server_username and ice_server_password:
            ice_token_obj = {
                'Urls': [ ice_server_url_remote ] if ice_server_url_remote else [ ice_server_url ],
                'Username': ice_server_username,
                'Password': ice_server_password
            }
        local_sdp = request.data.decode('utf-8')
        avatar_character = request.headers.get('AvatarCharacter')
        avatar_style = request.headers.get('AvatarStyle')
        background_color = '#FFFFFFFF' if request.headers.get('BackgroundColor') is None else request.headers.get('BackgroundColor')
        background_image_url = request.headers.get('BackgroundImageUrl')
        is_custom_avatar = request.headers.get('IsCustomAvatar')
        transparent_background = 'false' if request.headers.get('TransparentBackground') is None else request.headers.get('TransparentBackground')
        video_crop = 'false' if request.headers.get('VideoCrop') is None else request.headers.get('VideoCrop')
        avatar_config = {
            'synthesis': {
                'video': {
                    'protocol': {
                        'name': "WebRTC",
                        'webrtcConfig': {
                            'clientDescription': local_sdp,
                            'iceServers': [{
                                'urls': [ ice_token_obj['Urls'][0] ],
                                'username': ice_token_obj['Username'],
                                'credential': ice_token_obj['Password']
                            }]
                        },
                    },
                    'format':{
                        'crop':{
                            'topLeft':{
                                'x': 600 if video_crop.lower() == 'true' else 0,
                                'y': 0
                            },
                            'bottomRight':{
                                'x': 1320 if video_crop.lower() == 'true' else 1920,
                                'y': 1080
                            }
                        },
                        'bitrate': 1000000
                    },
                    'talkingAvatar': {
                        'customized': is_custom_avatar.lower() == 'true',
                        'character': avatar_character,
                        'style': avatar_style,
                        'background': {
                            'color': '#00FF00FF' if transparent_background.lower() == 'true' else background_color,
                            'image': {
                                'url': background_image_url
                            }
                        }
                    }
                }
            }
        }
        
        connection = speechsdk.Connection.from_speech_synthesizer(speech_synthesizer)
        connection.connected.connect(lambda evt: print(f'TTS Avatar service connected.'))
        def tts_disconnected_cb(evt):
            print(f'TTS Avatar service disconnected.')
            client_context['speech_synthesizer_connection'] = None
        connection.disconnected.connect(tts_disconnected_cb)
        connection.set_message_property('speech.config', 'context', json.dumps(avatar_config))
        client_context['speech_synthesizer_connection'] = connection

        speech_sythesis_result = speech_synthesizer.speak_text_async('').get()
        print(f'Result id for avatar connection: {speech_sythesis_result.result_id}')
        if speech_sythesis_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_sythesis_result.cancellation_details
            print(f"Speech synthesis canceled: {cancellation_details.reason}")
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print(f"Error details: {cancellation_details.error_details}")
                raise Exception(cancellation_details.error_details)
        turn_start_message = speech_synthesizer.properties.get_property_by_name('SpeechSDKInternal-ExtraTurnStartMessage')
        remoteSdp = json.loads(turn_start_message)['webrtc']['connectionString']

        return Response(remoteSdp, status=200)

    except Exception as e:
        return Response(f"Result ID: {speech_sythesis_result.result_id}. Error message: {e}", status=400)

# The API route to connect the STT service
@app.route("/api/connectSTT", methods=["POST"])
def connectSTT() -> Response:
    global client_contexts
    client_id = uuid.UUID(request.headers.get('ClientId'))
    # disconnect STT if already connected
    disconnectSttInternal(client_id)
    system_prompt = request.headers.get('SystemPrompt')
    client_context = client_contexts[client_id]
    try:
        if speech_private_endpoint:
            speech_private_endpoint_wss = speech_private_endpoint.replace('https://', 'wss://')
            if enable_token_auth_for_speech:
                while not speech_token:
                    time.sleep(0.2)
                speech_config = speechsdk.SpeechConfig(endpoint=f'{speech_private_endpoint_wss}/stt/speech/universal/v2')
                speech_config.authorization_token = speech_token
            else:
                speech_config = speechsdk.SpeechConfig(subscription=speech_key, endpoint=f'{speech_private_endpoint_wss}/stt/speech/universal/v2')
        else:
            if enable_token_auth_for_speech:
                while not speech_token:
                    time.sleep(0.2)
                speech_config = speechsdk.SpeechConfig(endpoint=f'wss://{speech_region}.stt.speech.microsoft.com/speech/universal/v2')
                speech_config.authorization_token = speech_token
            else:
                speech_config = speechsdk.SpeechConfig(subscription=speech_key, endpoint=f'wss://{speech_region}.stt.speech.microsoft.com/speech/universal/v2')

        audio_input_stream = speechsdk.audio.PushAudioInputStream()
        client_context['audio_input_stream'] = audio_input_stream

        audio_config = speechsdk.audio.AudioConfig(stream=audio_input_stream)
        speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        client_context['speech_recognizer'] = speech_recognizer

        speech_recognizer.session_started.connect(lambda evt: print(f'STT session started - session id: {evt.session_id}'))
        speech_recognizer.session_stopped.connect(lambda evt: print(f'STT session stopped.'))

        speech_recognition_start_time = datetime.datetime.now(pytz.UTC)

        def stt_recognized_cb(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                try:
                    user_query = evt.result.text.strip()
                    if user_query == '':
                        return

                    socketio.emit("response", { 'path': 'api.chat', 'chatResponse': '\n\nUser: ' + user_query + '\n\n' }, room=client_id)
                    recognition_result_received_time = datetime.datetime.now(pytz.UTC)
                    speech_finished_offset = (evt.result.offset + evt.result.duration) / 10000
                    stt_latency = round((recognition_result_received_time - speech_recognition_start_time).total_seconds() * 1000 - speech_finished_offset)
                    print(f'STT latency: {stt_latency}ms')
                    socketio.emit("response", { 'path': 'api.chat', 'chatResponse': f"<STTL>{stt_latency}</STTL>" }, room=client_id)
                    chat_initiated = client_context['chat_initiated']
                    if not chat_initiated:
                        initializeChatContext(system_prompt, client_id)
                        client_context['chat_initiated'] = True
                    first_response_chunk = True
                    for chat_response in handleUserQuery(user_query, client_id):
                        if first_response_chunk:
                            socketio.emit("response", { 'path': 'api.chat', 'chatResponse': 'Assistant: ' }, room=client_id)
                            first_response_chunk = False
                        socketio.emit("response", { 'path': 'api.chat', 'chatResponse': chat_response }, room=client_id)
                except Exception as e:
                    print(f"Error in handling user query: {e}")
        speech_recognizer.recognized.connect(stt_recognized_cb)

        def stt_recognizing_cb(evt):
            if not vad_iterator:
                stopSpeakingInternal(client_id)
        speech_recognizer.recognizing.connect(stt_recognizing_cb)

        def stt_canceled_cb(evt):
            cancellation_details = speechsdk.CancellationDetails(evt.result)
            print(f'STT connection canceled. Error message: {cancellation_details.error_details}')
        speech_recognizer.canceled.connect(stt_canceled_cb)

        speech_recognizer.start_continuous_recognition()
        return Response(status=200)

    except Exception as e:
        return Response(f"STT connection failed. Error message: {e}", status=400)

# The API route to disconnect the STT service
@app.route("/api/disconnectSTT", methods=["POST"])
def disconnectSTT() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    try:
        disconnectSttInternal(client_id)
        return Response('STT Disconnected.', status=200)
    except Exception as e:
        return Response(f"STT disconnection failed. Error message: {e}", status=400)


# The API route to speak a given SSML
@app.route("/api/speak", methods=["POST"])
def speak() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    try:
        ssml = request.data.decode('utf-8')
        result_id = speakSsml(ssml, client_id, True)
        return Response(result_id, status=200)
    except Exception as e:
        return Response(f"Speak failed. Error message: {e}", status=400)

# The API route to stop avatar from speaking
@app.route("/api/stopSpeaking", methods=["POST"])
def stopSpeaking() -> Response:
    global client_contexts
    client_id = uuid.UUID(request.headers.get('ClientId'))
    stopSpeakingInternal(client_id)
    return Response('Speaking stopped.', status=200)

# The API route for chat
# It receives the user query and return the chat response.
# It returns response in stream, which yields the chat response in chunks.
@app.route("/api/chat", methods=["POST"])
def chat() -> Response:
    global client_contexts
    client_id = uuid.UUID(request.headers.get('ClientId'))
    client_context = client_contexts[client_id]
    chat_initiated = client_context['chat_initiated']
    if not chat_initiated:
        initializeChatContext(request.headers.get('SystemPrompt'), client_id)
        client_context['chat_initiated'] = True
    user_query = request.data.decode('utf-8')
    return Response(handleUserQuery(user_query, client_id), mimetype='text/plain', status=200)

# The API route to clear the chat history
@app.route("/api/chat/clearHistory", methods=["POST"])
def clearChatHistory() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    client_context = client_contexts[client_id]
    initializeChatContext(request.headers.get('SystemPrompt'), client_id)
    client_context['chat_initiated'] = True
    return Response('Chat history cleared.', status=200)

# The API route to disconnect the TTS avatar
@app.route("/api/disconnectAvatar", methods=["POST"])
def disconnectAvatar() -> Response:
    client_id = uuid.UUID(request.headers.get('ClientId'))
    try:
        disconnectAvatarInternal(client_id)
        return Response('Disconnected avatar', status=200)
    except:
        return Response(traceback.format_exc(), status=400)

# The API route to release the client context, to be invoked when the client is closed
@app.route("/api/releaseClient", methods=["POST"])
def releaseClient() -> Response:
    global client_contexts
    client_id = uuid.UUID(json.loads(request.data)['clientId'])
    try:
        disconnectAvatarInternal(client_id)
        disconnectSttInternal(client_id)
        time.sleep(2) # Wait some time for the connection to close
        client_contexts.pop(client_id)
        print(f"Client context released for client {client_id}.")
        return Response('Client context released.', status=200)
    except Exception as e:
        print(f"Client context release failed. Error message: {e}")
        return Response(f"Client context release failed. Error message: {e}", status=400)

@socketio.on("connect")
def handleWsConnection():
    client_id = uuid.UUID(request.args.get('clientId'))
    join_room(client_id)
    print(f"WebSocket connected for client {client_id}.")

@socketio.on("message")
def handleWsMessage(message):
    global client_contexts
    client_id = uuid.UUID(message.get('clientId'))
    path = message.get('path')
    client_context = client_contexts[client_id]
    if path == 'api.audio':
        chat_initiated = client_context['chat_initiated']
        audio_chunk = message.get('audioChunk')
        audio_chunk_binary = base64.b64decode(audio_chunk)
        audio_input_stream = client_context['audio_input_stream']
        if audio_input_stream:
            audio_input_stream.write(audio_chunk_binary)
        if vad_iterator:
            audio_buffer = client_context['vad_audio_buffer']
            audio_buffer.extend(audio_chunk_binary)
            if len(audio_buffer) >= 1024:
                audio_chunk_int = np.frombuffer(bytes(audio_buffer[:1024]), dtype=np.int16)
                audio_buffer.clear()
                audio_chunk_float = int2float(audio_chunk_int)
                vad_detected = vad_iterator(torch.from_numpy(audio_chunk_float))
                if vad_detected:
                    print("Voice activity detected.")
                    stopSpeakingInternal(client_id)
    elif path == 'api.chat':
        chat_initiated = client_context['chat_initiated']
        if not chat_initiated:
            initializeChatContext(message.get('systemPrompt'), client_id)
            client_context['chat_initiated'] = True
        user_query = message.get('userQuery')
        for chat_response in handleUserQuery(user_query, client_id):
            socketio.emit("response", { 'path': 'api.chat', 'chatResponse': chat_response }, room=client_id)
    elif path == 'api.stopSpeaking':
        stopSpeakingInternal(client_id)

# Initialize the client by creating a client id and an initial context
def initializeClient() -> uuid.UUID:
    client_id = uuid.uuid4()
    client_contexts[client_id] = {
        'audio_input_stream': None, # Audio input stream for speech recognition
        'vad_audio_buffer': [], # Audio input buffer for VAD
        'speech_recognizer': None, # Speech recognizer for user speech
        'azure_openai_deployment_name': azure_openai_deployment_name, # Azure OpenAI deployment name
        'cognitive_search_index_name': cognitive_search_index_name, # Cognitive search index name
        'tts_voice': default_tts_voice, # TTS voice
        'custom_voice_endpoint_id': None, # Endpoint ID (deployment ID) for custom voice
        'personal_voice_speaker_profile_id': None, # Speaker profile ID for personal voice
        'speech_synthesizer': None, # Speech synthesizer for avatar
        'speech_synthesizer_connection': None, # Speech synthesizer connection for avatar
        'speech_token': None, # Speech token for client side authentication with speech service
        'ice_token': None, # ICE token for ICE/TURN/Relay server connection
        'chat_initiated': False, # Flag to indicate if the chat context is initiated
        'messages': [], # Chat messages (history)
        'data_sources': [], # Data sources for 'on your data' scenario
        'is_speaking': False, # Flag to indicate if the avatar is speaking
        'spoken_text_queue': [], # Queue to store the spoken text
        'speaking_thread': None, # The thread to speak the spoken text queue
        'last_speak_time': None # The last time the avatar spoke
    }
    return client_id

# Refresh the ICE token which being called
def refreshIceToken() -> None:
    global ice_token
    ice_token_response = None
    if speech_private_endpoint:
        if enable_token_auth_for_speech:
            while not speech_token:
                time.sleep(0.2)
            ice_token_response = requests.get(f'{speech_private_endpoint}/tts/cognitiveservices/avatar/relay/token/v1', headers={'Authorization': f'Bearer {speech_token}'})
        else:
            ice_token_response = requests.get(f'{speech_private_endpoint}/tts/cognitiveservices/avatar/relay/token/v1', headers={'Ocp-Apim-Subscription-Key': speech_key})
    else:
        if enable_token_auth_for_speech:
            while not speech_token:
                time.sleep(0.2)
            ice_token_response = requests.get(f'https://{speech_region}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1', headers={'Authorization': f'Bearer {speech_token}'})
        else:
            ice_token_response = requests.get(f'https://{speech_region}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1', headers={'Ocp-Apim-Subscription-Key': speech_key})
    if ice_token_response.status_code == 200:
        ice_token = ice_token_response.text
    else:
        raise Exception(f"Failed to get ICE token. Status code: {ice_token_response.status_code}")

# Refresh the speech token every 9 minutes
def refreshSpeechToken() -> None:
    global speech_token
    while True:
        # Refresh the speech token every 9 minutes
        if speech_private_endpoint:
            credential = DefaultAzureCredential(managed_identity_client_id=user_assigned_managed_identity_client_id)
            token = credential.get_token('https://cognitiveservices.azure.com/.default')
            speech_token = f'aad#{speech_resource_url}#{token.token}'
        else:
            speech_token = requests.post(f'https://{speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken', headers={'Ocp-Apim-Subscription-Key': speech_key}).text
        time.sleep(60 * 9)

# Initialize the chat context, e.g. chat history (messages), data sources, etc. For chat scenario.
def initializeChatContext(system_prompt: str, client_id: uuid.UUID) -> None:
    global client_contexts
    client_context = client_contexts[client_id]
    cognitive_search_index_name = client_context['cognitive_search_index_name']
    messages = client_context['messages']
    data_sources = client_context['data_sources']

    # Initialize data sources for 'on your data' scenario
    data_sources.clear()
    if cognitive_search_endpoint and cognitive_search_api_key and cognitive_search_index_name:
        # On-your-data scenario
        data_source = {
            'type': 'azure_search',
            'parameters': {
                'endpoint': cognitive_search_endpoint,
                'index_name': cognitive_search_index_name,
                'authentication': {
                    'type': 'api_key',
                    'key': cognitive_search_api_key
                },
                'semantic_configuration': '',
                'query_type': 'simple',
                'fields_mapping': {
                    'content_fields_separator': '\n',
                    'content_fields': ['content'],
                    'filepath_field': None,
                    'title_field': 'title',
                    'url_field': None
                },
                'in_scope': True,
                'role_information': system_prompt
            }
        }
        data_sources.append(data_source)

    # Initialize messages
    messages.clear()
    if len(data_sources) == 0:
        system_message = {
            'role': 'system',
            'content': system_prompt
        }
        messages.append(system_message)

# Handle the user query and return the assistant reply. For chat scenario.
# The function is a generator, which yields the assistant reply in chunks.
def handleUserQuery(user_query: str, client_id: uuid.UUID):
    global client_contexts
    client_context = client_contexts[client_id]
    azure_openai_deployment_name = client_context['azure_openai_deployment_name']
    messages = client_context['messages']
    data_sources = client_context['data_sources']

    chat_message = {
        'role': 'user',
        'content': user_query
    }

    messages.append(chat_message)

    # For 'on your data' scenario, chat API currently has long (4s+) latency
    # We return some quick reply here before the chat API returns to mitigate.
    if len(data_sources) > 0 and enable_quick_reply:
        speakWithQueue(random.choice(quick_replies), 2000)

    assistant_reply = ''
    tool_content = ''
    spoken_sentence = ''

    aoai_start_time = datetime.datetime.now(pytz.UTC)
    response = azure_openai.chat.completions.create(
        model=azure_openai_deployment_name,
        messages=messages,
        extra_body={ 'data_sources' : data_sources } if len(data_sources) > 0 else None,
        stream=True)

    is_first_chunk = True
    is_first_sentence = True
    for chunk in response:
        if len(chunk.choices) > 0:
            response_token = chunk.choices[0].delta.content
            if response_token is not None:
                # Log response_token here if need debug
                if is_first_chunk:
                    first_token_latency_ms = round((datetime.datetime.now(pytz.UTC) - aoai_start_time).total_seconds() * 1000)
                    print(f"AOAI first token latency: {first_token_latency_ms}ms")
                    yield f"<FTL>{first_token_latency_ms}</FTL>"
                    is_first_chunk = False
                if oyd_doc_regex.search(response_token):
                    response_token = oyd_doc_regex.sub('', response_token).strip()
                yield response_token # yield response token to client as display text
                assistant_reply += response_token  # build up the assistant message
                if response_token == '\n' or response_token == '\n\n':
                    if is_first_sentence:
                        first_sentence_latency_ms = round((datetime.datetime.now(pytz.UTC) - aoai_start_time).total_seconds() * 1000)
                        print(f"AOAI first sentence latency: {first_sentence_latency_ms}ms")
                        yield f"<FSL>{first_sentence_latency_ms}</FSL>"
                        is_first_sentence = False
                    speakWithQueue(spoken_sentence.strip(), 0, client_id)
                    spoken_sentence = ''
                else:
                    response_token = response_token.replace('\n', '')
                    spoken_sentence += response_token  # build up the spoken sentence
                    if len(response_token) == 1 or len(response_token) == 2:
                        for punctuation in sentence_level_punctuations:
                            if response_token.startswith(punctuation):
                                if is_first_sentence:
                                    first_sentence_latency_ms = round((datetime.datetime.now(pytz.UTC) - aoai_start_time).total_seconds() * 1000)
                                    print(f"AOAI first sentence latency: {first_sentence_latency_ms}ms")
                                    yield f"<FSL>{first_sentence_latency_ms}</FSL>"
                                    is_first_sentence = False
                                speakWithQueue(spoken_sentence.strip(), 0, client_id)
                                spoken_sentence = ''
                                break

    if spoken_sentence != '':
        speakWithQueue(spoken_sentence.strip(), 0, client_id)
        spoken_sentence = ''

    if len(data_sources) > 0:
        tool_message = {
            'role': 'tool',
            'content': tool_content
        }
        messages.append(tool_message)

    assistant_message = {
        'role': 'assistant',
        'content': assistant_reply
    }
    messages.append(assistant_message)

# Speak the given text. If there is already a speaking in progress, add the text to the queue. For chat scenario.
def speakWithQueue(text: str, ending_silence_ms: int, client_id: uuid.UUID) -> None:
    global client_contexts
    client_context = client_contexts[client_id]
    spoken_text_queue = client_context['spoken_text_queue']
    is_speaking = client_context['is_speaking']
    spoken_text_queue.append(text)
    if not is_speaking:
        def speakThread():
            nonlocal client_context
            nonlocal spoken_text_queue
            nonlocal ending_silence_ms
            tts_voice = client_context['tts_voice']
            personal_voice_speaker_profile_id = client_context['personal_voice_speaker_profile_id']
            client_context['is_speaking'] = True
            while len(spoken_text_queue) > 0:
                text = spoken_text_queue.pop(0)
                try:
                    speakText(text, tts_voice, personal_voice_speaker_profile_id, ending_silence_ms, client_id)
                except Exception as e:
                    print(f"Error in speaking text: {e}")
                client_context['last_speak_time'] = datetime.datetime.now(pytz.UTC)
            client_context['is_speaking'] = False
            print(f"Speaking thread stopped.")
        client_context['speaking_thread'] = threading.Thread(target=speakThread)
        client_context['speaking_thread'].start()

# Speak the given text.
def speakText(text: str, voice: str, speaker_profile_id: str, ending_silence_ms: int, client_id: uuid.UUID) -> str:
    ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='en-US'>
                 <voice name='{voice}'>
                     <mstts:ttsembedding speakerProfileId='{speaker_profile_id}'>
                         <mstts:leadingsilence-exact value='0'/>
                         {html.escape(text)}
                     </mstts:ttsembedding>
                 </voice>
               </speak>"""
    if ending_silence_ms > 0:
        ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='http://www.w3.org/2001/mstts' xml:lang='en-US'>
                     <voice name='{voice}'>
                         <mstts:ttsembedding speakerProfileId='{speaker_profile_id}'>
                             <mstts:leadingsilence-exact value='0'/>
                             {html.escape(text)}
                             <break time='{ending_silence_ms}ms' />
                         </mstts:ttsembedding>
                     </voice>
                   </speak>"""
    return speakSsml(ssml, client_id, False)

# Speak the given ssml with speech sdk
def speakSsml(ssml: str, client_id: uuid.UUID, asynchronized: bool) -> str:
    global client_contexts
    speech_synthesizer = client_contexts[client_id]['speech_synthesizer']
    speech_sythesis_result = speech_synthesizer.start_speaking_ssml_async(ssml).get() if asynchronized else speech_synthesizer.speak_ssml_async(ssml).get()
    if speech_sythesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_sythesis_result.cancellation_details
        print(f"Speech synthesis canceled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Result ID: {speech_sythesis_result.result_id}. Error details: {cancellation_details.error_details}")
            raise Exception(cancellation_details.error_details)
    return speech_sythesis_result.result_id

# Stop speaking internal function
def stopSpeakingInternal(client_id: uuid.UUID) -> None:
    global client_contexts
    client_context = client_contexts[client_id]
    spoken_text_queue = client_context['spoken_text_queue']
    spoken_text_queue.clear()
    avatar_connection = client_context['speech_synthesizer_connection']
    if avatar_connection:
        avatar_connection.send_message_async('synthesis.control', '{"action":"stop"}').get()

# Disconnect avatar internal function
def disconnectAvatarInternal(client_id: uuid.UUID) -> None:
    global client_contexts
    client_context = client_contexts[client_id]
    stopSpeakingInternal(client_id)
    time.sleep(2) # Wait for the speaking thread to stop
    avatar_connection = client_context['speech_synthesizer_connection']
    if avatar_connection:
        avatar_connection.close()

# Disconnect STT internal function
def disconnectSttInternal(client_id: uuid.UUID) -> None:
    global client_contexts
    client_context = client_contexts[client_id]
    speech_recognizer = client_context['speech_recognizer']
    audio_input_stream = client_context['audio_input_stream']
    if speech_recognizer:
        speech_recognizer.stop_continuous_recognition()
        connection = speechsdk.Connection.from_recognizer(speech_recognizer)
        connection.close()
        client_context['speech_recognizer'] = None
    if audio_input_stream:
        audio_input_stream.close()
        client_context['audio_input_stream'] = None

# Start the speech token refresh thread
speechTokenRefereshThread = threading.Thread(target=refreshSpeechToken)
speechTokenRefereshThread.daemon = True
speechTokenRefereshThread.start()

# Fetch ICE token at startup
refreshIceToken()


if __name__ == '__main__':
 
    
    app.run(host="0.0.0.0",port=8081,debug=True,ssl_context=('cert.pem', 'key.pem'))
