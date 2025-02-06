document.addEventListener('DOMContentLoaded', () => {
  const attachBtn = document.getElementById('attach-btn');
  const pdfViewer = document.getElementById('pdf-viewer');
  const pdfFrame = document.getElementById('pdf-frame');
  const pdfInput = document.getElementById('pdf-input');
  const micBtn = document.querySelector('.mic-btn');

  // Handle PDF viewer
  attachBtn.addEventListener('click', () => {
    pdfInput.click(); // Trigger file input click
  });

  // Handle file selection
  pdfInput.addEventListener('change', (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/pdf') {
      const fileUrl = URL.createObjectURL(file);
      pdfFrame.src = fileUrl;
      var form = new FormData();
      document.getElementById("myInput").disabled = false;
      form.append(file.name, file);
      form.append("file_url", fileUrl);
       $.ajax({
            type: 'POST',
            url: '/pdf_save',
            data: form,
            cache: false,
            processData: false,
            contentType: false

        }).done(function(data) {
        console.log(data);
  
});
      pdfViewer.classList.add('visible');
    }
  });

  // Handle microphone
   // Audio Recording
  let mediaRecorder;
  let audioChunks = [];
  let isRecording = false;

  // Request microphone access
  async function setupMicrophone() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);

      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        console.log('Recording stopped, audio URL:', audioUrl);
        
        var form = new FormData();

            form.append("audio_data", audioBlob);
             $.ajax({
                  type: 'POST',
                  url: '/audio_save',
                  data: form,
                  cache: false,
                  processData: false,
                  contentType: false
      
              }).done(function(data) {
              console.log(data);
              input.value = data["transcript"]
      });
        // Reset chunks for next recording
        audioChunks = [];
      };

      return true;
    } catch (error) {
      console.error('Error accessing microphone:', error);
      return false;
    }
  }

  // Handle microphone button
  micBtn.addEventListener('click', async () => {
    if (!mediaRecorder) {
      const initialized = await setupMicrophone();
      if (!initialized) {
        alert('Could not access microphone');
        return;
      }
    }

    isRecording = !isRecording;
    micBtn.style.color = isRecording ? '#ef4444' : '#9ca3af';

    if (isRecording) {
      audioChunks = [];
      mediaRecorder.start();
      console.log('Recording started');
    } else {
      mediaRecorder.stop();
      console.log('Recording stopped');
    }
  });
});

var input = document.getElementById("myInput");

// Execute a function when the user presses a key on the keyboard
input.addEventListener("keypress", function(event) {
  // If the user presses the "Enter" key on the keyboard
  if (event.key === "Enter") {
    // Cancel the default action, if needed
    console.log("dfd");
    event.preventDefault();
    // Trigger the button element with a click
    swal({
     text:"LibraFinFact is Acquiring Data and Performing Analysis for You",
    title: 'Please Wait...',
    allowEscapeKey: false,
    allowOutsideClick: false,
    onOpen: () => {
      swal.showLoading();
    }
  }).catch(
    () => {}
  );
    window.location.href = "/fake_chat_page?query="+ document.getElementById("myInput").value;
  }
});
