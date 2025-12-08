from django.urls import path

from . import views

app_name = "devices"

urlpatterns = [
    path("api/device/command/", views.poll_command, name="poll_command"),
    path("api/device/command/ack/", views.ack_command, name="ack_command"),
]
