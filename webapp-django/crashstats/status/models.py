# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models
from django.utils import timezone


class StatusMessage(models.Model):
    message = models.TextField(
        help_text='Plain text, but will linkify "bug #XXXXXXX" strings'
    )
    severity = models.CharField(
        max_length=20,
        choices=(("info", "Info"), ("warning", "Warning"), ("critical", "Critical")),
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
