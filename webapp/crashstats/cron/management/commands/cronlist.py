# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django.core.management.base import BaseCommand

from crashstats.cron import JOBS, DEFAULT_FREQUENCY
from crashstats.cron.models import Job


class Command(BaseCommand):
    help = "List available cron jobs."

    def handle(self, **options):
        for job_spec in JOBS:
            self.stdout.write(job_spec["cmd"])

            cmdline = [job_spec["cmd"]]
            if job_spec.get("cmd_args"):
                cmdline.extend(job_spec["cmd_args"])
            if job_spec.get("backfill"):
                cmdline.append("--run-time=RUNTIME")
            if job_spec.get("last_success"):
                cmdline.append("--last-success=LASTSUCCESS")
            cmdline = " ".join(cmdline)
            self.stdout.write("    cmdline:      %s" % cmdline)

            schedule = []
            schedule.append("every " + job_spec.get("frequency", DEFAULT_FREQUENCY))
            if job_spec.get("time"):
                schedule.append(job_spec["time"] + " UTC")
            schedule = " @ ".join(schedule)
            self.stdout.write("    schedule:     %s" % schedule)

            try:
                job = Job.objects.get(app_name=job_spec["cmd"])
                self.stdout.write("    last run:     %s" % job.last_run)
                self.stdout.write("    last_success: %s" % job.last_success)
                self.stdout.write("    next run:     %s" % job.next_run)
                if job.last_error:
                    self.stdout.write("    " + job.last_error)
            except Job.DoesNotExist:
                self.stdout.write("    Never run.")
