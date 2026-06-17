import uuid

from django.contrib.auth.models import User
from django.db import models


class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    title = models.CharField(max_length=255, default="New Navigation")
    eligibility_state = models.JSONField(default=dict, blank=True)
    cached_policy_text = models.TextField(blank=True, default="")
    has_valid_document = models.BooleanField(default=False)
    invalid_doc_attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Message(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("ai", "AI"),
    ]

    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    is_error = models.BooleanField(default=False)
    is_gatekeeper = models.BooleanField(default=False)
    attached_file = models.FileField(
        upload_to="policy_docs/",
        null=True,
        blank=True,
    )
    attached_url = models.URLField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"
