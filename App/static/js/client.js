document.addEventListener("DOMContentLoaded", function () {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const wsUrl = `${protocol}${window.location.host}/ws/voice/`;

    let mediaRecorder;
    let isRecording = false;
    const voiceButton = document.getElementById("voiceControl");
    const audioPlayer = document.getElementById("audioPlayer");  // Reference to the audio element
    

    let sourceBuffer = [];
    
    const socket = new WebSocket(wsUrl);
    socket.binaryType = "arraybuffer"; // Expect binary messages for TTS audio.
    
    socket.onopen = function () {
        console.log("WebSocket connection established.");
    };
    
    socket.onmessage = async function (event) {
        if (typeof event.data === "string") {
            const data = JSON.parse(event.data);
            if (data.command === "final") {
                console.log("Response:", data.response);
                const mp3Blob = new Blob(sourceBuffer, { type: 'audio/mpeg' });
                const mp3Url = URL.createObjectURL(mp3Blob);
            
                // Set the audio source and play
                audioPlayer.src = mp3Url;
                audioPlayer.onended = () => {
                    sourceBuffer = [];
                    
                    if (data.auto_restart) {
                        setTimeout(() => {
                            startRecording();
                        }, 500);
                    }
                };
    
                /*
                if (data.auto_restart) {
                    stopRecording(false); // Stop recording without sending stop command
                    setTimeout(() => {
                        startRecording();
                    }, 500);
                } else {
                    stopRecording(false);
                }
                */
            } else if (data.command === "user_speech_end") {
                console.log("Speech end detected:", data.transcription);
                stopRecording(false); 
                voiceButton.textContent = "Responding..."
            } else if (data.command === "auto_stop") {
                console.log("Auto-stop triggered due to inactivity.");
                stopRecording(false);
            } else {
                console.log("Message from server:", data);
            }
        } else {       
            if (event.data instanceof ArrayBuffer) {
                sourceBuffer.push(event.data);
              } else {
                console.log("Received data is not an ArrayBuffer");
              }
            
        }
    };
    
    socket.onclose = function () {
        console.log("WebSocket connection closed.");
    };
    
    socket.onerror = function (error) {
        console.error("WebSocket error:", error);
    };

    async function startRecording() {
        if (isRecording) return;
        isRecording = true;
        socket.send(JSON.stringify({ command: "start" }));
        
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
    
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
                    socket.send(event.data);
                }
            };
    
            mediaRecorder.start(250); // Stream small audio chunks
            voiceButton.textContent = "Recording...";
            console.log("Recording started...");
        } catch (error) {
            console.error("Error accessing microphone:", error);
        }
    }


    function stopRecording(notify=true) {
        if(!isRecording) return;

        isRecording = false;

        if(notify)
            socket.send(JSON.stringify({ command: "stop" }));

        if (mediaRecorder) {
            mediaRecorder.stop();
            voiceButton.textContent = "Start Recording";
            console.log("Recording stopped.");
        }
    }
    
    voiceButton.addEventListener("click", function() {
        if (!isRecording) {
            startRecording();
        } else {
            stopRecording();
        }
    });
});
