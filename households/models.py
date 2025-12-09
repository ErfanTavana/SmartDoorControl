from django.db import models
from django.conf import settings


class Building(models.Model):
    title = models.CharField(max_length=255, verbose_name="عنوان")
    address = models.CharField(
        max_length=255, blank=True, verbose_name="آدرس"
    )

    def __str__(self) -> str:
        return self.title


class Household(models.Model):
    title = models.CharField(max_length=255, verbose_name="عنوان")
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="households",
        verbose_name="سرپرست",
    )
    building = models.ForeignKey(
        Building,
        on_delete=models.CASCADE,
        related_name="households",
        verbose_name="ساختمان",
    )

    def __str__(self) -> str:
        return self.title


class MemberProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="member_profile",
        verbose_name="کاربر",
    )
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name="خانوار",
    )
    allowed_from_time = models.TimeField(verbose_name="زمان شروع مجاز")
    allowed_to_time = models.TimeField(verbose_name="زمان پایان مجاز")
    active = models.BooleanField(default=True, verbose_name="فعال")

    def __str__(self) -> str:
        return f"{self.user.username} ({self.household})"
