from django.contrib import admin

from .models import AccessLog, DoorCommand


@admin.register(DoorCommand)
class DoorCommandAdmin(admin.ModelAdmin):
    list_display = ("id", "device", "requested_by", "executed", "created_at")
    list_filter = ("executed", "device")


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    list_display = ("user", "household", "status", "timestamp")
    list_filter = ("status", "household")
    search_fields = ("user__username", "household__title")
