from channels.generic.websocket import AsyncWebsocketConsumer
import asyncio, aiohttp, json, time, uuid, base64
from . import conversation_response, conversation_context
from decouple import config

class WebVoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.scope["session"]["session_id"] = str(uuid.uuid4())
        self.recording = False           # True if actively recording
        self.user_stop = False           # True if user manually stops recording
        self.aiohttp_session = aiohttp.ClientSession()
        self.deepgram_ws = None

        await self.accept()
        print("WebSocket Connected: ", self.scope["session"]["session_id"])

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            message = json.loads(text_data)
            command = message.get("command")
    
            if command == "start":
                self.recording = True
                self.user_stop = False    
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
                            "command":"user_speech_end",
                            "transcription": transcript
                        }))
                        
                        gpt_response = await conversation_response.get_response(self.aiohttp_session, transcript, self.scope["session"]["session_id"])
                        
                        # Convert OpenAI response to speech via Deepgram TTS and stream audio.
                        asyncio.create_task(self.text_to_speech(gpt_response))
                        break
                    else:
                        # Final transcript is empty - indicating speech inactivity
                        if time.time() - speech_session_start >= inactivity_threshold:
                            # 30 seconds of empty final transcripts detected: auto-stop.
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

    async def text_to_speech(self, text):

        TTS_URL = f"{config('DEEPGRAM_TTS_API_ENDPOINT')}?model={config('DEEPGRAM_TTS_MODEL')}&encoding=mp3"
        headers = {
            "Authorization": f"Token {config('DEEPGRAM_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = { "text": text }

        try:
           async with self.aiohttp_session.post(TTS_URL, json=payload, headers=headers) as response:
                async for chunk in response.content.iter_chunked(1024):
                    if chunk:
                        await self.send(bytes_data=chunk)

        
        except Exception as e:
            print('Deepgram TTS error: ', e)
        finally:
            await self.send(text_data=json.dumps({
                "command": "final",
                "response": text,
                "auto_restart": not self.user_stop
            }))

    
    async def disconnect(self, close_code):
        print("WebSocket Disconnected", self.scope["session"]["session_id"])
        if self.deepgram_ws:
            await self.deepgram_ws.close()
        if self.aiohttp_session:
            await self.aiohttp_session.close()

        await conversation_context.remove_conversation_context(key=self.scope["session"]["session_id"])
        self.deepgram_ws, self.aiohttp_session = None, None


class TwilioVoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.scope["session"]["session_id"] = str(uuid.uuid4())
        self.aiohttp_session = aiohttp.ClientSession()
        self.deepgram_ws = None

        await self.accept()
        print("Twilio WebSocket Connected: ", self.scope["session"]["session_id"])

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            data = json.loads(text_data)
            event = data.get('event')
            if event == 'start':
                self.deepgram_ws = await self.aiohttp_session.ws_connect(
                    f"{config('DEEPGRAM_WS_URL')}?model={config('DEEPGRAM_STT_MODEL')}"
                    f"&smart_format=true&interim_results=false&endpointing={config('DEEPGRAM_STT_ENDPOINTING')}&encoding=mulaw&sample_rate=8000",
                    headers={"Authorization": f"Token {config('DEEPGRAM_API_KEY')}"}
                )
                self.streamSid = data['start']['streamSid']
                greet_prompt = "Greet with humor and tell your name. Ask what's me on my mind?"
                greet_user = await conversation_response.get_response(self.aiohttp_session, greet_prompt, user_session=self.scope["session"]["session_id"], no_context=True)
                await self.text_to_speech(greet_user)

                asyncio.create_task(self.speech_to_text())
                
            elif event == 'media':
                audio_chunk_b64 = data['media']['payload']
                if self.deepgram_ws:
                    await self.deepgram_ws.send_bytes(base64.b64decode(audio_chunk_b64))
                
            elif event == 'stop':
                if self.deepgram_ws:
                    await self.deepgram_ws.close()
                    self.deepgram_ws = None
       
    async def speech_to_text(self):
        speech_session_start = time.time()
        inactivity_threshold = config('SPEECH_INACTIVITY_THRESHOLD', cast=int)

        try:
            async for message in self.deepgram_ws:
                if message.type == aiohttp.WSMsgType.TEXT:
                    response = json.loads(message.data)
                    transcript = response.get("channel", {}).get("alternatives", [{}])[0].get("transcript", "").strip()
                    
                    if transcript:
                        
                        gpt_response = await conversation_response.get_response(self.aiohttp_session, transcript, self.scope["session"]["session_id"])
                        # Convert OpenAI response to speech via Deepgram TTS and stream audio.
                        asyncio.create_task(self.text_to_speech(gpt_response))
                        speech_session_start = time.time()

                    elif time.time() - speech_session_start >= inactivity_threshold:
                        # Final transcript is empty - indicating speech inactivity
                        gpt_response = "Hello? Are we playing the world’s quietest game of charades? Speak up dear!"
                        # 30 seconds of empty transcripts detected: prompt the user to talk lol.
                        asyncio.create_task(self.text_to_speech(gpt_response))
                        speech_session_start = time.time()

        except Exception as e:
            print("Deepgram WS error:", e)

        finally:
            if self.deepgram_ws:
                await self.deepgram_ws.close()
            self.deepgram_ws = None
     

    async def text_to_speech(self, text):
        TTS_URL = f"{config('DEEPGRAM_TTS_API_ENDPOINT')}?model={config('DEEPGRAM_TTS_MODEL')}&encoding=mulaw&sample_rate=8000&container=none"
        headers = {
            "Authorization": f"Token {config('DEEPGRAM_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = { "text": text }
        
        try:
           await self.send(text_data=json.dumps({"event": "start", })) 

           async with self.aiohttp_session.post(TTS_URL, json=payload, headers=headers) as response:
                async for chunk in response.content.iter_chunked(1024):
                    if chunk:
                        encoded_chunk = base64.b64encode(chunk).decode("utf-8")
                        await self.send(text_data=json.dumps({
                            "event": "media",
                            "streamSid": self.streamSid,
                            "media": {
                                "payload": encoded_chunk
                                }
                        }))

           await self.send(text_data=json.dumps({"event": "stop"}))

        except Exception as e:
            print('Twilio Deepgram TTS error: ', e)


    async def disconnect(self, close_code):
        print("Twilio WS disconnected: ", self.scope["session"]["session_id"])
        if self.deepgram_ws:
            await self.deepgram_ws.close()
        if self.aiohttp_session:
            await self.aiohttp_session.close()

        await conversation_context.remove_conversation_context(key=self.scope["session"]["session_id"])
        self.deepgram_ws, self.aiohttp_session = None, None

