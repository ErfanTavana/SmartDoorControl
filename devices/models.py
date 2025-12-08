from django.conf import settings
from django.db import models

from households.models import Household


class Device(models.Model):
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="devices"
    )
    api_token = models.CharField(max_length=255, unique=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Device {self.id} for {self.household}"
