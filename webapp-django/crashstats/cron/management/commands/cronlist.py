# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


from django.core.management.base import BaseCommand

from crashstats.cron import JOBS, DEFAULT_FREQUENCY
from crashstats.cron.models import Job


class Command(BaseCommand):
    help = 'List available cron jobs.'

    def handle(self, **options):
        for job_spec in JOBS:
            self.stdout.write(job_spec['cmd'])
            schedule = []
            schedule.append('every ' + job_spec.get('frequency', DEFAULT_FREQUENCY))
            if job_spec.get('time'):
                schedule.append(job_spec['time'] + ' UTC')
            schedule = ' @ '.join(schedule)
            self.stdout.write('    schedule:     %s' % schedule)

            try:
                job = Job.objects.get(app_name=job_spec['cmd'])
                self.stdout.write('    last run:     %s' % job.last_run)
                self.stdout.write('    last_success: %s' % job.last_success)
                self.stdout.write('    next run:     %s' % job.next_run)
                if job.last_error:
                    self.stdout.write('    ' + job.last_error)
            except Job.DoesNotExist:
                self.stdout.write('    Never run.')
