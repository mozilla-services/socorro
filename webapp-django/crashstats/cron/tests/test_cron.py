# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from io import StringIO
from unittest import mock

import freezegun
import pytest

from django.core.management import call_command
from django.utils import timezone

from crashstats.cron.models import Job
from crashstats.cron.management.commands import cron


@pytest.mark.parametrize('freq, expected', [
    ('1d', 86400),
    ('2h', 7200),
    ('3m', 180),
])
def test_convert_frequency_good(freq, expected):
    assert cron.convert_frequency(freq) == expected


def test_convert_frequency_error():
    with pytest.raises(cron.FrequencyDefinitionError):
        cron.convert_frequency('1t')


@pytest.mark.parametrize('value', [
    '00:00',
    '12:00',
    '23:59',
])
def test_check_time_good(value):
    # check_time doesn't return anything, so we're just verifying
    # that some things raise an error and others don't
    cron.check_time(value)


@pytest.mark.parametrize('value', [
    '',
    '000:000',
    '23:69',
])
def test_check_time_bad(value):
    with pytest.raises(cron.TimeDefinitionError):
        cron.check_time(value)


def test_time_to_run(db):
    now = timezone.now()

    job_spec = {
        'cmd': 'fakejob'
    }
    job = Job.objects.create(
        app_name=job_spec['cmd'],
        next_run=None
    )

    with freezegun.freeze_time(now, tz_offset=0):
        # With no next_run and no time
        job.next_run = None
        assert cron.time_to_run(job_spec, job) is True

        # With no next_run and bad time
        job_spec['time'] = '%02d:%02d' % (now.hour + 1, now.minute + 1)
        assert cron.time_to_run(job_spec, job) is False

        # With no next_run and good time
        job_spec['time'] = '%02d:%02d' % (now.hour - 1, now.minute - 1)
        assert cron.time_to_run(job_spec, job) is True

        # With next_run
        job.next_run = now - datetime.timedelta(minutes=5)
        assert cron.time_to_run(job_spec, job) is True


def test_get_run_times(db):
    now = timezone.now()

    job_spec = {
        'cmd': 'fakejob',
        'backfill': False,
    }

    with freezegun.freeze_time(now, tz_offset=0):
        # With backfill=False, yield [now]
        assert list(cron.get_run_times(job_spec, last_success=now)) == [now]


def test_get_run_times_for_backfill_job(db):
    now = timezone.now()
    now.replace(
        hour=12,
        minute=0,
        second=0,
        microsecond=0
    )

    job_spec = {
        'cmd': 'fakejob',
        'backfill': True,
        'frequency': '1h',
    }

    with freezegun.freeze_time(now, tz_offset=0):
        # With backfill=True, but never been run, yield [now]
        last_success = None
        assert list(cron.get_run_times(job_spec, last_success=last_success)) == [now]

        # frequency, but no time, last_success one hour ago, yield [now]
        last_success = now - datetime.timedelta(hours=1)
        actual = list(cron.get_run_times(job_spec, last_success=last_success))
        expected = [now]
        assert actual == expected

        # frequency, but no time, last_success three hours ago, yields
        # [2 hours ago, 1 hour ago, now]
        last_success = now - datetime.timedelta(hours=3)
        actual = list(cron.get_run_times(job_spec, last_success=last_success))
        expected = [
            now - datetime.timedelta(hours=2),
            now - datetime.timedelta(hours=1),
            now
        ]
        assert actual == expected

        # frequency and time
        last_success = now - datetime.timedelta(hours=24)
        job_spec['frequency'] = '1d'
        job_spec['time'] = '10:30'
        actual = list(cron.get_run_times(job_spec, last_success=last_success))
        expected = [
            datetime.datetime(
                year=now.year,
                month=now.month,
                day=now.day,
                hour=10,
                minute=30,
                second=0,
                microsecond=0,
                tzinfo=now.tzinfo
            )
        ]
        assert actual == expected


class TestCron:
    def test_lock_job_works(self, db):
        cron_command = cron.Command()
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
        cron_command = cron.Command()
        now = timezone.now()

        # Create a job that has an ongoing under MAX_ONGOING so it's still
        # locked
        Job.objects.create(
            app_name='testjob',
            ongoing=now - datetime.timedelta(seconds=cron.MAX_ONGOING - 10)
        )

        with freezegun.freeze_time(now, tz_offset=0):
            with pytest.raises(cron.OngoingJobError):
                with cron_command.lock_job('testjob'):
                    pass

    def test_lock_job_zombie_job(self, db):
        cron_command = cron.Command()
        now = timezone.now()

        # Create a job that has an ongoing over MAX_ONGOING so we break
        # the lock
        Job.objects.create(
            app_name='testjob',
            ongoing=now - datetime.timedelta(seconds=cron.MAX_ONGOING + 10)
        )

        with freezegun.freeze_time(now, tz_offset=0):
            with cron_command.lock_job('testjob'):
                # Verify it's locked with now as the datetime
                assert Job.objects.filter(app_name='testjob', ongoing=now).get()

        # Verify it's no longer locked
        assert Job.objects.filter(app_name='testjob', ongoing__isnull=True).get()

    def test_run_one_pass_args(self, db):
        """Verify --job=JOB works and that you can pass arguments."""
        job_args = {
            'job': 'crontest',
            'job_arg': ['print="fun fun fun"']
        }
        out = StringIO()
        call_command('cron', stdout=out, **job_args)
        assert '"fun fun fun"' in out.getvalue()

    def test_mark_success(self, db):
        """Verify --mark-success works."""
        # Assert there's nothing in the db to start with
        assert Job.objects.all().count() == 0

        # Call it and make sure all the jobs now have Job records and are all
        # successes
        out = StringIO()
        call_command('cron', stdout=out, mark_success='all')
        jobs = list(Job.objects.all())
        assert len(jobs) == len(cron.JOBS)
        for job in jobs:
            assert job.last_success is not None

    def test_reset_job(self, db):
        """Verify --reset-job works."""
        call_command('cron', mark_success='all')
        assert Job.objects.all().count() == len(cron.JOBS)

        call_command('cron', reset_job='all')
        assert Job.objects.all().count() == 0

    def test_run_all(self, db):
        """Verify that running "cron" runs all the jobs."""
        # Patch out call_command because otherwise this'd take forrrrever
        with mock.patch('crashstats.cron.management.commands.cron.call_command'):
            call_command('cron')

        assert Job.objects.all().count() == len(cron.JOBS)
