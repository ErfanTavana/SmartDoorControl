import hashlib
import secrets

from django.db import models
from django.utils import timezone

from households.models import Building


def generate_api_token() -> str:
    while True:
        token = secrets.token_urlsafe(32)
        if not Device.objects.filter(api_token=token).exists():
            return token


class Device(models.Model):
    building = models.ForeignKey(
        Building, on_delete=models.CASCADE, related_name="devices"
    )
    api_token = models.CharField(
        max_length=255, unique=True, editable=False, default=generate_api_token
    )
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Device {self.id} for {self.building}"


class DeviceFirmware(models.Model):
    device = models.OneToOneField(
        Device, on_delete=models.CASCADE, related_name="firmware"
    )
    version = models.CharField(max_length=50)
    content = models.TextField()
    checksum = models.CharField(max_length=64, blank=True)
    config = models.TextField(blank=True, default="")
    config_version = models.CharField(max_length=50, blank=True, default="")
    config_checksum = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Firmware {self.version} for {self.device}"

    def save(self, *args, **kwargs):
        if self.content:
            self.checksum = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        else:
            self.checksum = ""

        if self.config:
            self.config_checksum = hashlib.sha256(
                self.config.encode("utf-8")
            ).hexdigest()
        else:
            self.config_checksum = ""

        super().save(*args, **kwargs)


class DeviceLog(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="logs"
    )
    level = models.CharField(max_length=20, blank=True)
    event_type = models.CharField(max_length=50, blank=True, default="")
    message = models.TextField()
    firmware_version = models.CharField(max_length=50, blank=True, default="")
    metadata = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        level = self.level or "log"
        event = f" ({self.event_type})" if self.event_type else ""
        return f"{level.upper()}{event} for {self.device}"
