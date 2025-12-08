from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        HEAD = "HEAD", "Head"
        MEMBER = "MEMBER", "Member"

    role = models.CharField(
        max_length=10,
        choices=Roles.choices,
        default=Roles.MEMBER,
    )

    @property
    def is_head(self) -> bool:
        return self.role == self.Roles.HEAD

    @property
    def is_member(self) -> bool:
        return self.role == self.Roles.MEMBER
