from django.db import models
from django.conf import settings


class Building(models.Model):
    title = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return self.title


class Household(models.Model):
    title = models.CharField(max_length=255)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="households",
    )
    building = models.ForeignKey(
        Building, on_delete=models.CASCADE, related_name="households"
    )

    def __str__(self) -> str:
        return self.title


class MemberProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="member_profile"
    )
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="members"
    )
    allowed_from_time = models.TimeField()
    allowed_to_time = models.TimeField()
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.user.username} ({self.household})"
