# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
import time
from urllib.parse import urlparse

import requests

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import connection
from django.shortcuts import render

from crashstats.manage.decorators import superuser_required
from crashstats.supersearch.models import SuperSearchStatus


@superuser_required
def crash_me_now(request):
    # NOTE(willkg): This intentionally throws an error so that we can test
    # unhandled error handling.
    1 / 0  # noqa


@superuser_required
def site_status(request):
    context = {}

    # Get version information for deployed parts
    version_info = {}
    for url in settings.OVERVIEW_VERSION_URLS.split(","):
        hostname = urlparse(url).netloc
        url = url.strip()
        try:
            data = requests.get(url).json()
        except Exception as exc:
            data = {"error": str(exc)}
        version_info[hostname] = data

    context["version_info"] = version_info

    # Get settings
    context["site_settings"] = []
    keys = (
        "LOCAL_DEV_ENV",
        "DEBUG",
        "TOOL_ENV",
    )
    for key in keys:
        value = getattr(settings, key)
        context["site_settings"].append({"key": key, "value": str(value)})

    # Get Django migration data
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, app, name, applied FROM django_migrations")
            cols = [col[0] for col in cursor.description]
            django_db_data = [dict(zip(cols, row)) for row in cursor.fetchall()]
            django_db_error = ""
    except Exception as exc:
        django_db_data = []
        django_db_error = "error: %s" % exc
    context["django_db_data"] = django_db_data
    context["django_db_error"] = django_db_error

    # Get some table counts
    tables = [
        "auth_user",
        "django_session",
        "tokens_token",
        "cron_job",
        "cron_log",
        "crashstats_bugassociation",
        "crashstats_graphicsdevice",
        "crashstats_missingprocessedcrash",
        "crashstats_platform",
        "crashstats_productversion",
        "crashstats_signature",
    ]
    context["table_counts"] = []
    for table_name in tables:
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute("select count(*) from %s" % table_name)
            row = cursor.fetchone()
            (value,) = row
        timing = time.time() - start_time
        context["table_counts"].append(
            {
                "key": table_name,
                "value": f"{value:,}",
                "timing": f"{timing:,.2f}",
            }
        )

    context["title"] = "Site status"

    return render(request, "admin/site_status.html", context)


@superuser_required
def supersearch_status(request):
    context = {}
    status = SuperSearchStatus().get()
    context["indices"] = status["indices"]
    context["latest_index"] = status["latest_index"]
    context["mapping"] = json.dumps(status["mapping"], indent=2)
    context["title"] = "Super Search status"

    return render(request, "admin/supersearch_status.html", context)


@superuser_required
def protected_data_users(request):
    email_addresses = []

    try:
        hackers_group = Group.objects.get(name="Hackers")
    except Group.DoesNotExist:
        hackers_group = []

    email_addresses.extend(
        [user.email for user in hackers_group.user_set.all() if user.is_active]
    )

    try:
        hackers_plus_group = Group.objects.get(name="Hackers Plus")
    except Group.DoesNotExist:
        hackers_plus_group = []

    email_addresses.extend(
        [user.email for user in hackers_plus_group.user_set.all() if user.is_active]
    )

    context = {"addresses": set(email_addresses)}
    return render(request, "admin/protected_data_users.html", context)
