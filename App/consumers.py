from channels.generic.websocket import AsyncWebsocketConsumer
import json

class VoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Handles WebSocket connection."""
        await self.accept()
        print("WebSocket Connected")

        # Audio storage attributes
        self.audio_file_path = "received_audio.wav"
        self.audio_data = bytearray()
        self.recording = False  # Flag to track recording state

    async def receive(self, text_data=None, bytes_data=None):
        """Handles incoming audio data and control commands from the frontend."""
        if text_data:
            # Handle control messages (start/stop)
            message = json.loads(text_data)
            command = message.get("command")
    
            if command == "start":
                self.recording = True
                self.audio_data.clear()
                print("Recording started...")
    
            elif command == "stop":
                self.recording = False
                print("Recording stopped. Saving audio...")
    
                # Save the recorded audio
                if self.audio_data:
                    with open(self.audio_file_path, "wb") as audio_file:
                        audio_file.write(self.audio_data)
                    print(f"Audio saved: {self.audio_file_path}")
    
        if bytes_data and self.recording:
            # Append received audio bytes only if recording is active
            self.audio_data.extend(bytes_data)


    async def disconnect(self, close_code):
        """Handles WebSocket disconnection."""
        print("WebSocket Disconnected")
