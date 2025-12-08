from django.urls import path

from . import views

app_name = "households"

urlpatterns = [
    path("dashboard/", views.head_dashboard, name="head_dashboard"),
    path("members/", views.member_list, name="member_list"),
    path("members/create/", views.member_create, name="member_create"),
    path("members/<int:member_id>/edit/", views.member_edit, name="member_edit"),
    path("members/<int:member_id>/delete/", views.member_delete, name="member_delete"),
]
