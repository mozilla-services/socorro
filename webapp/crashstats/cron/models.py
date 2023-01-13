# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.db import models


class Job(models.Model):
    app_name = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        unique=True,
        help_text="the Django command",
    )
    next_run = models.DateTimeField(
        null=True, blank=True, help_text="the datetime of the next time to run"
    )
    first_run = models.DateTimeField(
        null=True, blank=True, help_text="the datetime of the first time ever run"
    )
    last_run = models.DateTimeField(
        null=True, blank=True, help_text="the datetime of the last time this was run"
    )
    last_success = models.DateTimeField(
        null=True, blank=True, help_text="the datetime of the last successful run"
    )
    error_count = models.IntegerField(
        default=0, help_text="the number of consecutive error runs"
    )
    depends_on = models.TextField(
        null=True,
        blank=True,
        help_text="comma separated list of apps this app depends on",
    )
    last_error = models.TextField(
        null=True, blank=True, help_text="JSON blob of the last error"
    )
    ongoing = models.DateTimeField(
        null=True, blank=True, help_text="the datetime this job entry was locked"
    )

    def __str__(self):
        return "<Job: %s>" % self.app_name


class Log(models.Model):
    app_name = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        help_text="the Django command this log entry is for",
    )
    log_time = models.DateTimeField(
        auto_now_add=True, help_text="the datetime for this entry"
    )
    duration = models.FloatField(help_text="duration in seconds")
    success = models.DateTimeField(blank=True, null=True, help_text="")
    exc_type = models.TextField(
        null=True, blank=True, help_text="the exc type of an error if any"
    )
    exc_value = models.TextField(
        null=True, blank=True, help_text="the exc value of an error if any"
    )
    exc_traceback = models.TextField(
        null=True, blank=True, help_text="the exc traceback of an error if any"
    )

    def __str__(self):
        return "<Log: %s@%s, %s>" % (
            self.app_name,
            self.log_time.strftime("%Y-%m-%d %H:%M"),
            bool(self.success),
        )
