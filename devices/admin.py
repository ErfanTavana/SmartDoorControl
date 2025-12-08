from django.contrib import admin

from .models import Device, DeviceFirmware, DeviceLog


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "building", "api_token", "last_seen")
    search_fields = ("api_token", "building__title")


@admin.register(DeviceFirmware)
class DeviceFirmwareAdmin(admin.ModelAdmin):
    list_display = ("device", "version", "created_at")
    search_fields = ("device__building__title", "version")
    autocomplete_fields = ("device",)


@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ("device", "level", "created_at")
    list_filter = ("level", "created_at")
    search_fields = ("device__building__title", "message")
    autocomplete_fields = ("device",)
