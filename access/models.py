from django.conf import settings
from django.db import models

from devices.models import Device
from households.models import Household


class DoorCommand(models.Model):
    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="commands", verbose_name="دستگاه"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="door_commands",
        verbose_name="درخواست‌دهنده",
    )
    executed = models.BooleanField(default=False, verbose_name="اجرا شده")
    expired = models.BooleanField(default=False, verbose_name="منقضی شده")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    executed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="زمان اجرا"
    )

    def __str__(self) -> str:
        return f"Command {self.id} for {self.device}"


class AccessLog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        DENIED = "denied", "Denied"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="کاربر",
    )
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="access_logs",
        verbose_name="خانوار",
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="زمان ثبت")
    status = models.CharField(
        max_length=20, choices=Status.choices, verbose_name="وضعیت"
    )
    reason = models.TextField(blank=True, verbose_name="دلیل")

    def __str__(self) -> str:
        username = self.user.username if self.user else "Unknown"
        return f"{username} - {self.status}"
