from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio, aiohttp, json, time
from decouple import config

class VoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("WebSocket Connected")
        self.recording = False           # True if actively recording
        self.user_stop = False           # True if user manually stops recording
        self.aiohttp_session = aiohttp.ClientSession()
        self.deepgram_ws = None

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            message = json.loads(text_data)
            command = message.get("command")
    
            if command == "start":
                self.recording = True
                self.user_stop = False    # Reset manual stop flag
                print("Recording started...")
                self.deepgram_ws = await self.aiohttp_session.ws_connect(
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
                    transcript = response.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "").strip()
                    
                    if transcript:
                        self.recording = False

                        # Non-empty final transcript
                        await self.send(text_data=json.dumps({
                            "command":"speech_end",
                            "transcription": transcript
                        }))

                        gpt_response = await self.get_response(transcript)
                        
                        await self.send(text_data=json.dumps({
                            "command": "final",
                            "response": gpt_response,
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
            self.recording = False
            if self.deepgram_ws:
                await self.deepgram_ws.close()
            self.deepgram_ws = None
            print("Recording Stopped.")

    async def get_response(self, user_query):
        headers = {
            "Authorization": f"Bearer {config('OPENAI_API_KEY')}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": config('OPENAI_MODEL'),
            "messages": [
                {
                    "role": "system", 
                    "content": "Act and generate response like the Daisy O2 time-wasting bot. Response should not exceed 30 words."
                },
                {
                    "role": "user", 
                    "content": user_query
                }
            ],
            "max_tokens": 40,
            "temperature": 0.8
        }

        try:
            async with self.aiohttp_session.post(config('OPENAI_API_ENDPOINT'), json=payload, headers=headers) as response:
                response_json = await response.json()
                return response_json.get("choices", [{}])[0].get("message", {}).get("content", "I couldn't hear you well. Mind repeating?")
        except Exception as e:
            print("GPT API error:", e)
            return "I'm having trouble responding right now."


    async def disconnect(self, close_code):
        print("WebSocket Disconnected")
        if self.deepgram_ws:
            await self.deepgram_ws.close()
        if self.aiohttp_session:
            await self.aiohttp_session.close()
        self.deepgram_ws, self.aiohttp_session = None, None
