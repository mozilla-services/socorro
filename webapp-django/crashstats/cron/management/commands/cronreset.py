# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.core.management.base import BaseCommand

from crashstats.cron.models import Job
from crashstats.cron.utils import get_matching_job_specs


class Command(BaseCommand):
    help = "Reset jobs."

    def add_arguments(self, parser):
        parser.add_argument(
            "jobs",
            help='Comma-delimited list of job names to reset or "all" for all of them.',
        )

    def handle(self, **options):
        cmds = options["jobs"].split(",")
        job_specs = get_matching_job_specs(cmds)

        for job_spec in job_specs:
            cmd = job_spec["cmd"]
            try:
                job = Job.objects.get(app_name=cmd)
                job.delete()
                self.stdout.write("Job %s is reset." % cmd)
            except Job.DoesNotExist:
                self.stdout.write("Job %s already reset" % cmd)
