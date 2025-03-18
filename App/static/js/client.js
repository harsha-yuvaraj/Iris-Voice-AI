document.addEventListener("DOMContentLoaded", function () {
    const protocol = (window.location.protocol === "https:") ? "wss://" : "ws://";
    const wsUrl = `${protocol}${window.location.host}/ws/voice/`;

    let mediaRecorder;
    let isRecording = false;
    const voiceButton = document.getElementById("voiceControl");
    
    const socket = new WebSocket(wsUrl);
    
    socket.onopen = function () {
        console.log("WebSocket connection established.");
    };
    
    socket.onmessage = function (event) {
        console.log("Received from backend:", event.data);
    };
    
    socket.onclose = function () {
        console.log("WebSocket connection closed.");
    };
    
    socket.onerror = function (error) {
        console.error("WebSocket error:", error);
    };
        
    async function toggleRecording() {
        isRecording = !isRecording;

        if (isRecording) {
            socket.send(JSON.stringify({ command: "start" })); // Notify backend to start

            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
    
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
                        socket.send(event.data);
                    }
                };
    
                mediaRecorder.start(150); // Stream audio in small chunks
                voiceButton.textContent = "Stop Recording";
                console.log("Recording started...");
            } catch (error) {
                console.error("Error accessing microphone:", error);
            }
        } else {
            socket.send(JSON.stringify({ command: "stop" })); // Notify backend to stop
            mediaRecorder?.stop();
            voiceButton.textContent = "Start Recording";
            console.log("Recording stopped.");
        }
    }
    
    voiceButton.addEventListener("click", toggleRecording);
});
