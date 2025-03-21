from django.urls import path
from .consumers import WebVoiceConsumer, TwilioVoiceConsumer

websocket_urlpatterns = [
    path("ws/voice/", WebVoiceConsumer.as_asgi()),
    path("ws/twilio/", TwilioVoiceConsumer.as_asgi())
]

