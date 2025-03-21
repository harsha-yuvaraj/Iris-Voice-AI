from django.urls import path
from . import views

# define application namespace
app_name = 'App'

urlpatterns = [
    path('', views.index, name="home"),
    path('iris-inbound-via-twilio/', views.receive_twilio_call, name="twilio_inbound_handler")
]
