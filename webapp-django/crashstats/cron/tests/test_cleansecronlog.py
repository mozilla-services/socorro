# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.utils import timezone

from crashstats.cron.models import Log


def test_cleanse_cronlog(db):
    today = timezone.now()
    cutoff = today - datetime.timedelta(days=180)

    # Create some Log records from before cutoff
    with mock.patch("django.utils.timezone.now") as mock_now:
        mock_now.return_value = cutoff - datetime.timedelta(days=1)
        Log.objects.create(app_name="log1", duration=10)
        Log.objects.create(app_name="log2", duration=10)

    # Create one Log after cutoff
    with mock.patch("django.utils.timezone.now") as mock_now:
        mock_now.return_value = cutoff + datetime.timedelta(days=1)
        Log.objects.create(app_name="log3", duration=10)

    out = StringIO()
    call_command("cleanse_cronlog", dry_run=True, stdout=out)
    assert "DRY RUN" in out.getvalue()
    assert Log.objects.all().count() == 3

    out = StringIO()
    call_command("cleanse_cronlog", dry_run=False, stdout=out)
    assert "DRY RUN" not in out.getvalue()
    assert list(Log.objects.all().values_list("app_name", flat=True)) == ["log3"]
