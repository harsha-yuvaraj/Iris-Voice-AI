from django.urls import path
from .consumers import VoiceConsumer

websocket_urlpatterns = [
    path("ws/voice/", VoiceConsumer.as_asgi()),
]
