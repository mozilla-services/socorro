# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime

import freezegun
import pytest

from django.utils import timezone

from crashstats.cron import FrequencyDefinitionError, TimeDefinitionError
from crashstats.cron.models import Job
from crashstats.cron.utils import (
    convert_frequency,
    convert_time,
    get_run_times,
    time_to_run,
)


@pytest.mark.parametrize("freq, expected", [("1d", 86400), ("2h", 7200), ("3m", 180)])
def test_convert_frequency_good(freq, expected):
    assert convert_frequency(freq) == expected


def test_convert_frequency_error():
    with pytest.raises(FrequencyDefinitionError):
        convert_frequency("1t")


@pytest.mark.parametrize(
    "value, expected", [("00:00", (0, 0)), ("12:00", (12, 0)), ("23:59", (23, 59))]
)
def test_convert_time(value, expected):
    assert convert_time(value) == expected


@pytest.mark.parametrize("value", ["", "000:000", "23:69"])
def test_convert_time_bad(value):
    with pytest.raises(TimeDefinitionError):
        convert_time(value)


def test_time_to_run(db):
    now = timezone.now()
    now = now.replace(hour=12, minute=30, second=0, microsecond=0)

    job_spec = {"cmd": "fakejob"}
    job = Job.objects.create(app_name=job_spec["cmd"], next_run=None)

    with freezegun.freeze_time(now, tz_offset=0):
        # With no next_run and no time
        job.next_run = None
        assert time_to_run(job_spec, job) is True

        # With no next_run and bad time
        job_spec["time"] = "%02d:%02d" % (now.hour + 1, now.minute + 1)
        assert time_to_run(job_spec, job) is False

        # With no next_run and good time
        job_spec["time"] = "%02d:%02d" % (now.hour - 1, now.minute - 1)
        assert time_to_run(job_spec, job) is True

        # With next_run
        job.next_run = now - datetime.timedelta(minutes=5)
        assert time_to_run(job_spec, job) is True


def test_get_run_times(db):
    now = timezone.now()

    job_spec = {"cmd": "fakejob", "backfill": False}

    with freezegun.freeze_time(now, tz_offset=0):
        # With backfill=False, yield [now]
        assert list(get_run_times(job_spec, last_success=now)) == [now]


def test_get_run_times_for_backfill_job(db):
    now = timezone.now()
    now = now.replace(hour=12, minute=0, second=0, microsecond=0)

    job_spec = {"cmd": "fakejob", "backfill": True, "frequency": "1h"}

    with freezegun.freeze_time(now, tz_offset=0):
        # With backfill=True, but never been run, yield [now]
        last_success = None
        assert list(get_run_times(job_spec, last_success=last_success)) == [now]

        # frequency, but no time, last_success one hour ago, yield [now]
        last_success = now - datetime.timedelta(hours=1)
        actual = list(get_run_times(job_spec, last_success=last_success))
        expected = [now]
        assert actual == expected

        # frequency, but no time, last_success three hours ago, yields
        # [2 hours ago, 1 hour ago, now]
        last_success = now - datetime.timedelta(hours=3)
        actual = list(get_run_times(job_spec, last_success=last_success))
        expected = [
            now - datetime.timedelta(hours=2),
            now - datetime.timedelta(hours=1),
            now,
        ]
        assert actual == expected

        # frequency and time
        last_success = now - datetime.timedelta(hours=24)
        job_spec["frequency"] = "1d"
        job_spec["time"] = "10:30"
        actual = list(get_run_times(job_spec, last_success=last_success))
        expected = [
            datetime.datetime(
                year=now.year,
                month=now.month,
                day=now.day,
                hour=10,
                minute=30,
                second=0,
                microsecond=0,
                tzinfo=now.tzinfo,
            )
        ]
        assert actual == expected
