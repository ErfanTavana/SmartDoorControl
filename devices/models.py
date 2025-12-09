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
        Building, on_delete=models.CASCADE, related_name="devices", verbose_name="ساختمان"
    )
    api_token = models.CharField(
        max_length=255,
        unique=True,
        editable=False,
        default=generate_api_token,
        verbose_name="توکن API",
    )
    last_seen = models.DateTimeField(null=True, blank=True, verbose_name="آخرین مشاهده")

    def __str__(self) -> str:
        return f"Device {self.id} for {self.building}"


class DeviceFirmware(models.Model):
    device = models.OneToOneField(
        Device, on_delete=models.CASCADE, related_name="firmware", verbose_name="دستگاه"
    )
    version = models.CharField(max_length=50, verbose_name="نسخه")
    content = models.TextField(verbose_name="محتوا")
    checksum = models.CharField(max_length=64, blank=True, verbose_name="چک‌سام")
    config = models.TextField(blank=True, default="", verbose_name="پیکربندی")
    config_version = models.CharField(
        max_length=50, blank=True, default="", verbose_name="نسخه پیکربندی"
    )
    config_checksum = models.CharField(
        max_length=64, blank=True, verbose_name="چک‌سام پیکربندی"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")

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
        Device, on_delete=models.CASCADE, related_name="logs", verbose_name="دستگاه"
    )
    level = models.CharField(max_length=20, blank=True, verbose_name="سطح")
    event_type = models.CharField(
        max_length=50, blank=True, default="", verbose_name="نوع رویداد"
    )
    message = models.TextField(verbose_name="پیام")
    firmware_version = models.CharField(
        max_length=50, blank=True, default="", verbose_name="نسخه میان‌افزار"
    )
    metadata = models.JSONField(blank=True, default=dict, verbose_name="متادیتا")
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name="زمان ایجاد"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        level = self.level or "log"
        event = f" ({self.event_type})" if self.event_type else ""
        return f"{level.upper()}{event} for {self.device}"
