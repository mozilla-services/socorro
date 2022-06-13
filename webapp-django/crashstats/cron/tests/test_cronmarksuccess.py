# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from io import StringIO

from django.core.management import call_command

from crashstats.cron import JOBS
from crashstats.cron.models import Job


def test_mark_success(db):
    """Verify --mark-success works."""
    # Assert there's nothing in the db to start with
    assert Job.objects.all().count() == 0

    # Call it and make sure all the jobs now have Job records and are all
    # successes
    out = StringIO()
    call_command("cronmarksuccess", stdout=out)
    jobs = list(Job.objects.all())
    assert len(jobs) == len(JOBS)
    for job in jobs:
        assert job.last_success is not None
