from django.contrib.auth.models import User
from django.db import models

from .i18n import DEFAULT_LANGUAGE, PREFERRED_LANGUAGE_CHOICES


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    preferred_language = models.CharField(
        max_length=10,
        choices=PREFERRED_LANGUAGE_CHOICES,
        default=DEFAULT_LANGUAGE,
    )
    onboarding_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({self.preferred_language})"
