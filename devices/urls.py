from django.urls import path

from . import views

app_name = "devices"

urlpatterns = [
    path("devices/logs/", views.device_logs, name="device_logs"),
    path("api/device/command/", views.poll_command, name="poll_command"),
    path("api/device/command/ack/", views.ack_command, name="ack_command"),
    path("api/device/firmware/", views.firmware_payload, name="firmware"),
    path("api/device/logs/", views.ingest_log, name="ingest_log"),
]
