# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime

from django.contrib import admin

from crashstats.cron import models


@admin.register(models.Job)
class JobAdmin(admin.ModelAdmin):
    date_hierarchy = "next_run"

    list_display = [
        "app_name",
        "next_run",
        "last_run",
        "last_success",
        "first_run",
        "error_count",
        "pretty_last_error",
        "ongoing",
    ]

    def pretty_last_error(self, obj):
        if not obj.last_error:
            return ""
        if len(obj.last_error) > 100:
            return obj.last_error[:100] + "..."
        return obj.last_error


@admin.register(models.Log)
class LogAdmin(admin.ModelAdmin):
    list_display = [
        "app_name",
        "log_time",
        "pretty_duration",
        "success",
        "pretty_error",
    ]
    list_filter = ["app_name"]

    def pretty_duration(self, obj):
        if not obj.duration:
            return ""
        return str(datetime.timedelta(seconds=obj.duration))

    def pretty_error(self, obj):
        if obj.exc_type and obj.exc_value:
            return "%s %s" % (obj.exc_type, obj.exc_value)
