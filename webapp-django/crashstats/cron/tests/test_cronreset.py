# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management import call_command

from crashstats.cron import JOBS
from crashstats.cron.models import Job


def test_reset_job(db):
    """Verify cronresetjob works."""
    call_command("cronmarksuccess")
    assert Job.objects.all().count() == len(JOBS)

    call_command("cronreset", "all")
    assert Job.objects.all().count() == 0
