from django.contrib import admin

from .models import Device, DeviceFirmware, DeviceLog


class DeviceLogInline(admin.TabularInline):
    model = DeviceLog
    extra = 0
    readonly_fields = ("level", "message", "created_at")
    ordering = ("-created_at",)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("id", "building", "api_token", "last_seen")
    search_fields = ("api_token", "building__title")
    inlines = (DeviceLogInline,)


@admin.register(DeviceFirmware)
class DeviceFirmwareAdmin(admin.ModelAdmin):
    list_display = ("device", "version", "created_at")
    search_fields = ("device__building__title", "version")
    autocomplete_fields = ("device",)


@admin.register(DeviceLog)
class DeviceLogAdmin(admin.ModelAdmin):
    list_display = ("device", "level", "message", "created_at")
    list_filter = ("level", "created_at")
    search_fields = ("device__building__title", "message")
    autocomplete_fields = ("device",)
