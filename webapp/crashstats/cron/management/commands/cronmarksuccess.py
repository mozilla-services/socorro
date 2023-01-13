# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand
from django.utils import timezone

from crashstats.cron.models import Job
from crashstats.cron.utils import convert_time, get_matching_job_specs


class Command(BaseCommand):
    help = "Mark jobs successful."

    def add_arguments(self, parser):
        parser.add_argument(
            "jobs",
            default="all",
            nargs="?",
            help='Comma-delimited list of job names to mark successful or "all" for all of them.',
        )

    def handle(self, **options):
        cmds = options["jobs"].split(",")
        job_specs = get_matching_job_specs(cmds)

        now = timezone.now()
        for job_spec in job_specs:
            cmd = job_spec["cmd"]
            self.stdout.write("Marking %s for success at %s..." % (cmd, now))

            next_run = now
            if job_spec.get("time"):
                hh, mm = convert_time(job_spec["time"])
                next_run = next_run.replace(hour=hh, minute=mm, second=0, microsecond=0)

            job = Job.objects.get_or_create(app_name=cmd)[0]
            job.first_run = job.first_run if job.first_run is not None else now
            job.last_success = now
            job.next_run = next_run
            job.save()
