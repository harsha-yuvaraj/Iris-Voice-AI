document.addEventListener("DOMContentLoaded", function () {

    let mediaRecorder;
    let isRecording = false;
    let mediaSource;
    let sourceBuffer;
    const chunkQueue = [];
    let isAppending = false;
    let receivedFinal = false; // Flag to check final command received

    const protocol = (window.location.protocol === "https:") ? "wss://" : "ws://";
    const wsUrl = `${protocol}${window.location.host}/ws/voice/`;

    const voiceButton = document.getElementById("voiceControl");
    const audioPlayer = document.getElementById("audioPlayer");

    // Establish WebSocket connection and set binary type
    const socket = new WebSocket(wsUrl);
    socket.binaryType = "arraybuffer";

    socket.onopen = function () {
        console.log("WebSocket connection established.");
        // Initialize MediaSource on connection open
        initMediaSource();
    };

    // Initialize MediaSource and setup SourceBuffer
    function initMediaSource() {
        mediaSource = new MediaSource();
        audioPlayer.src = URL.createObjectURL(mediaSource);
        mediaSource.addEventListener("sourceopen", () => {
            const mimeCodec = 'audio/mpeg';

            if (!MediaSource.isTypeSupported(mimeCodec)) {
                console.error('Codec not supported:', mimeCodec);
                alert(`Codec not supported: ${mimeCodec}`);
                return;
            }

            sourceBuffer = mediaSource.addSourceBuffer(mimeCodec);
            sourceBuffer.mode = "sequence"; // Append in sequence order

            // When the SourceBuffer is ready, process any queued chunks
            sourceBuffer.addEventListener('updateend', () => {
                isAppending = false;
                appendFromQueue();
            });
        });
    }

    // Append chunk from the queue if possible
    function appendFromQueue() {
        if (chunkQueue.length > 0 && !isAppending && !sourceBuffer.updating) {
            isAppending = true;
            const chunk = chunkQueue.shift();
            sourceBuffer.appendBuffer(chunk);
        }
    }

    // Programmatically start playback when enough data is buffered
    audioPlayer.addEventListener("canplay", () => {
        // Start playback if not already playing
        if (audioPlayer.paused) {
            audioPlayer.play().catch(e => console.error("Playback error:", e));
        }
    });

    socket.onmessage = async function (event) {
        if (typeof event.data === "string") {
            const data = JSON.parse(event.data);

            if (data.command === "final") {
                console.log("Final command received, streaming done. \n" + data.response);
                receivedFinal = true;
                // End the stream once SourceBuffer is finished updating
                if (!sourceBuffer.updating && chunkQueue.length === 0) {
                    mediaSource.endOfStream();
                } else {
                    // Poll until updating is finished then end stream
                    const checkBuffer = setInterval(() => {
                        if (!sourceBuffer.updating && chunkQueue.length === 0) {
                            clearInterval(checkBuffer);
                            mediaSource.endOfStream();
                        }
                    }, 100);
                }

                // Wait for audio playback to complete before resetting
                audioPlayer.onended = () => {
                    console.log("Speech Audio playback complete. Resetting.");
                    resetMediaSource();
                    
                    if (data.auto_restart) {
                        startRecording();
                    }
                };
            } else if (data.command === "user_speech_end") {
                console.log("Speech end detected:", data.transcription);
                stopRecording(false);
                voiceButton.textContent = "Responding...";
            } else if (data.command === "auto_stop") {
                console.log("Auto-stop triggered due to inactivity.");
                stopRecording(false);
            } else {
                console.log("Message from server:", data);
            }
        } else {
            // For binary data (audio chunks), enqueue and attempt to append
            if (event.data instanceof ArrayBuffer) {
                chunkQueue.push(event.data);
                if (sourceBuffer && !sourceBuffer.updating) {
                    appendFromQueue();
                }
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
        alert("Reload the page! Connection issue.")
    };

    // Reset MediaSource for a fresh stream
    function resetMediaSource() {
        // Remove the old source and reinitialize for next stream
        audioPlayer.pause();
        audioPlayer.src = "";
        mediaSource = null;
        sourceBuffer = null;
        chunkQueue.length = 0;
        receivedFinal = false;
        initMediaSource();
    }

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
            mediaRecorder.start(250); // Send small audio chunks
            voiceButton.textContent = "Recording...";
            console.log("Recording started...");
        } catch (error) {
            alert("Error accessing microphone:", error);
        }
    }

    function stopRecording(notify = true) {
        if (!isRecording) return;
        isRecording = false;
        if (notify) {
            socket.send(JSON.stringify({ command: "stop" }));
        }
        if (mediaRecorder) {
            mediaRecorder.stop();
            voiceButton.textContent = "Start Recording";
            console.log("Recording stopped.");
        }
    }

    voiceButton.addEventListener("click", function () {
        if (!isRecording) {
            startRecording();
        } else {
            stopRecording();
        }
    });
});
