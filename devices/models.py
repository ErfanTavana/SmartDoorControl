import secrets

from django.db import models

from households.models import Household


def generate_api_token() -> str:
    while True:
        token = secrets.token_urlsafe(32)
        if not Device.objects.filter(api_token=token).exists():
            return token


class Device(models.Model):
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="devices"
    )
    api_token = models.CharField(
        max_length=255, unique=True, editable=False, default=generate_api_token
    )
    last_seen = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Device {self.id} for {self.household}"
