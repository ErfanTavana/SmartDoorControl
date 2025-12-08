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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Firmware {self.version} for {self.device}"


class DeviceLog(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="logs"
    )
    level = models.CharField(max_length=20, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        level = self.level or "log"
        return f"{level.upper()} for {self.device}"
