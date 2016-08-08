from django.db import models
from django.utils import timezone


class StatusMessage(models.Model):
    message = models.TextField()
    severity = models.CharField(max_length=20)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
