from django.urls import path

from . import views

app_name = "access"

urlpatterns = [
    path("door/", views.member_panel, name="member_panel"),
    path("logs/", views.access_logs, name="access_logs"),
]
