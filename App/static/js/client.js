document.addEventListener("DOMContentLoaded", function () {
    const protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
    const wsUrl = `${protocol}${window.location.host}/ws/voice/`;

    let mediaRecorder;
    let isRecording = false;
    const voiceButton = document.getElementById("voiceControl");
    
    const socket = new WebSocket(wsUrl);
    
    socket.onopen = function () {
        console.log("WebSocket connection established.");
    };
    
    socket.onmessage = function (event) {
        const data = JSON.parse(event.data);
        if (data.command === "final") {
            console.log("Final transcription:", data.transcription);
            if (data.auto_restart) {
                stopRecording();
                setTimeout(() => {
                    startRecording();
                }, 500);
            } else {
                stopRecording();
            }
        } else if (data.command === "auto_stop") {
            console.log("Auto-stop triggered due to inactivity.");
            stopRecording();
        } else {
            console.log("Message from server:", data);
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
    
    function stopRecording() {
        if (!isRecording) return;
        isRecording = false;
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
