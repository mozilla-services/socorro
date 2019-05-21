# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import re
from unittest import mock

import freezegun
import pytest
from markus.testing import GAUGE, MetricsMock

from django.core.management import call_command
from django.utils import timezone

from crashstats.cron import (
    JOBS,
    MAX_ONGOING,
    OngoingJobError,
)
from crashstats.cron.models import Job
from crashstats.cron.management.commands import cronrun


class TestCronrun:
    def test_lock_job_works(self, db):
        cron_command = cronrun.Command()
        now = timezone.now()

        # Create a job with no ongoing and then lock it
        Job.objects.create(app_name='testjob', ongoing=None)
        with freezegun.freeze_time(now, tz_offset=0):
            with cron_command.lock_job('testjob'):
                # Verify it's locked
                assert Job.objects.filter(app_name='testjob', ongoing=now).get()

        # Verify it's no longer locked
        assert Job.objects.filter(app_name='testjob', ongoing__isnull=True).get()

    def test_lock_job_ongoing_job(self, db):
        cron_command = cronrun.Command()
        now = timezone.now()

        # Create a job that has an ongoing under MAX_ONGOING so it's still
        # locked
        Job.objects.create(
            app_name='testjob',
            ongoing=now - datetime.timedelta(seconds=MAX_ONGOING - 10)
        )

        with freezegun.freeze_time(now, tz_offset=0):
            with pytest.raises(OngoingJobError):
                with cron_command.lock_job('testjob'):
                    pass

    def test_lock_job_zombie_job(self, db):
        cron_command = cronrun.Command()
        now = timezone.now()

        # Create a job that has an ongoing over MAX_ONGOING so we break
        # the lock
        Job.objects.create(
            app_name='testjob',
            ongoing=now - datetime.timedelta(seconds=MAX_ONGOING + 10)
        )

        with freezegun.freeze_time(now, tz_offset=0):
            with cron_command.lock_job('testjob'):
                # Verify it's locked with now as the datetime
                assert Job.objects.filter(app_name='testjob', ongoing=now).get()

        # Verify it's no longer locked
        assert Job.objects.filter(app_name='testjob', ongoing__isnull=True).get()

    def test_run_one_pass_args(self, db, caplog):
        """Verify --job=JOB works and that you can pass arguments."""
        caplog.set_level('INFO')
        job_args = {
            'job': 'crontest',
            'job_arg': ['print="fun fun fun"']
        }

        call_command('cronrun', **job_args)
        recs = [rec.message for rec in caplog.records]
        assert 'crontest: To print: \'"fun fun fun"\'' in recs

    def test_run_all(self, db):
        """Verify that running "cron" runs all the jobs."""
        # Patch out call_command because otherwise this'd take forrrrever
        with mock.patch('crashstats.cron.management.commands.cronrun.call_command'):
            call_command('cronrun')

        assert Job.objects.all().count() == len(JOBS)

    def test_exception(self, db, caplog):
        """Exceptions are caught, and logged multiple ways."""
        caplog.set_level('INFO')
        job_args = {
            'job': 'crontest',
            'job_arg': ['print="die die die"']
        }

        with mock.patch('crashstats.cron.management.commands.cronrun.call_command') as call, \
                mock.patch('sentry_sdk.capture_exception') as capture, \
                MetricsMock() as metrics_mock:
            call.side_effect = RuntimeError('I Died')
            call_command('cronrun', **job_args)

        # The exception is captured by Sentry
        capture.assert_called_once_with()

        # The exception is logged
        err_re = re.compile(r'error when running crontest.*\\nRuntimeError: I Died\\n$')
        recs = [rec.message for rec in caplog.records]
        assert any(err_re.match(rec) for rec in recs), recs

        # The job duration is recorded as a failure
        assert metrics_mock.has_record(
            fun_name=GAUGE,
            stat='cron.job_failure_runtime',
            tags=['job:crontest']
        )
