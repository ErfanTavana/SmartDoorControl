from django.conf import settings
from django.db import models

from devices.models import Device
from households.models import Household


class DoorCommand(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="commands"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="door_commands",
    )
    executed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Command {self.id} for {self.device}"


class AccessLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        DENIED = "denied", "Denied"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="access_logs"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    reason = models.TextField(blank=True)

    def __str__(self) -> str:
        username = self.user.username if self.user else "Unknown"
        return f"{username} - {self.status}"
