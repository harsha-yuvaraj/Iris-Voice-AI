from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio, aiohttp, json, time
from decouple import config

class VoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("WebSocket Connected")
        self.recording = False           # True if actively recording
        self.user_stop = False           # True if user manually stops recording
        self.deepgram_session = aiohttp.ClientSession()
        self.deepgram_ws = None

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            message = json.loads(text_data)
            command = message.get("command")
    
            if command == "start":
                self.recording = True
                self.user_stop = False    # Reset manual stop flag
                print("Recording started...")
                self.deepgram_ws = await self.deepgram_session.ws_connect(
                    f"{config('DEEPGRAM_WS_URL')}?model={config('DEEPGRAM_STT_MODEL')}"
                    f"&smart_format=true&interim_results=false&endpointing={config('DEEPGRAM_STT_ENDPOINTING')}",
                    headers={"Authorization": f"Token {config('DEEPGRAM_API_KEY')}"}
                )
                asyncio.create_task(self.speech_to_text())
    
            elif command == "stop":
                self.recording = False
                self.user_stop = True
                if self.deepgram_ws:
                    await self.deepgram_ws.close()
                self.deepgram_ws = None
                print("Recording manually stopped.")
    
        elif bytes_data and self.recording and self.deepgram_ws:
            await self.deepgram_ws.send_bytes(bytes_data)
    
    async def speech_to_text(self):
        """
        Listens to Deepgram's WebSocket for final transcription messages.
        - If a final transcript is non-empty, sends it immediately.
        - If a final transcript is empty, waits until 10 seconds. If no non-empty final transcript is received still, send the 'auto_stop' command to frontend.
        """
        speech_session_start = time.time()
        inactivity_threshold = config('SPEECH_INACTIVITY_THRESHOLD', cast=int)

        try:
            async for message in self.deepgram_ws:
                if message.type == aiohttp.WSMsgType.TEXT:
                    response = json.loads(message.data)
                    alternative = response.get("channel", {}).get("alternatives", [{}])[0]
                    transcript = alternative.get("transcript", "").strip()

                    if transcript:
                        # Non-empty final transcript: send it and break
                        await self.send(text_data=json.dumps({
                            "command": "final",
                            "transcription": transcript,
                            "auto_restart": not self.user_stop
                        }))
                        break
                    else:
                        # Final transcript is empty - indicating speech inactivity
                        if time.time() - speech_session_start >= inactivity_threshold:
                            # 10 seconds of empty final transcripts detected: auto-stop.
                            await self.send(text_data=json.dumps({
                                "command": "auto_stop"
                            }))
                            break

        except Exception as e:
            print("Deepgram WS error:", e)

        finally:
            if self.deepgram_ws:
                await self.deepgram_ws.close()
            self.deepgram_ws = None

    async def disconnect(self, close_code):
        print("WebSocket Disconnected")
        if self.deepgram_ws:
            await self.deepgram_ws.close()
        if self.deepgram_session:
            await self.deepgram_session.close()
        self.deepgram_ws, self.deepgram_session = None, None
