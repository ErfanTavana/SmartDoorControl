from django.contrib import admin

from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "household", "api_token", "last_seen")
    search_fields = ("api_token", "household__title")
