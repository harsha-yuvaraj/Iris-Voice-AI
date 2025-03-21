from twilio.twiml.voice_response import VoiceResponse, Stream, Connect
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import HttpResponse
from decouple import config


def index(request):
    return render(request, 'main/home.html')

@csrf_exempt
@require_POST
def receive_twilio_call(request):
    response = VoiceResponse()
    # Connect the call and stream audio to your WebSocket endpoint.
    connect = Connect()
    stream = Stream(url=config('TWILIO_STREAM_WS_URL'))
    connect.append(stream)
    response.append(connect)
    
    return HttpResponse(str(response), content_type="application/xml")
    
