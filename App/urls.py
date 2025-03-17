from django.urls import path
from . import views

# define application namespace
app_name = 'App'

urlpatterns = [
    path('', views.index, name="home"),
]
