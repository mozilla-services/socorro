# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from datetime import date, datetime, time, timezone
import json

from click.testing import CliRunner

from bin.load_processed_crashes_into_es import load_crashes
from socorro.lib.libooid import create_new_ooid
from socorro import settings


# Setup helper, so we have some processed crashes to load into ES
def load_crashes_into_crashstorage_source(helper, date_str="2024-05-01", num_crashes=2):
    bucket = settings.STORAGE["options"]["bucket"]
    helper.create_bucket(bucket)

    expected_processed_crashes = []
    date_args = [int(date_part) for date_part in date_str.split("-")]
    date_datetime = date(*date_args)
    expected_processed_crash_base = {
        "date_processed": datetime.combine(
            date_datetime, time.min, timezone.utc
        ).isoformat(),
    }
    raw_crash_base = {"submitted_timestamp": date_str}

    for _ in range(num_crashes):
        # Encode the date in the crash ID, so we can determine the correct
        # Elasticsearch index by crash ID downstream.
        crash_id = create_new_ooid(timestamp=date_datetime)
        processed_crash = {**expected_processed_crash_base, "uuid": crash_id}
        expected_processed_crashes.append(processed_crash)

        # Upload raw crash for this crash ID, since only the raw crash
        # path contains the date for lookups.
        raw_crash = {**raw_crash_base, "uuid": crash_id}
        date_str_fmt = raw_crash["submitted_timestamp"].replace("-", "")
        helper.upload(
            bucket_name=bucket,
            key=f"v1/raw_crash/{date_str_fmt}/{crash_id}",
            data=json.dumps(raw_crash).encode("utf-8"),
        )

        # Upload processed crash for the crash ID
        helper.upload(
            bucket_name=bucket,
            key=f"v1/processed_crash/{crash_id}",
            data=json.dumps(processed_crash).encode("utf-8"),
        )

    return expected_processed_crashes


def test_it_runs():
    """Test whether the module loads and spits out help."""
    runner = CliRunner()
    result = runner.invoke(load_crashes, ["--help"])
    assert result.exit_code == 0


def test_it_loads_processed_crashes_by_date(storage_helper, es_helper):
    """Test whether the module loads processed crashes by date."""
    date_str = "2024-05-01"
    expected_crashes = load_crashes_into_crashstorage_source(storage_helper, date_str)
    runner = CliRunner()
    result = runner.invoke(load_crashes, ["--date", date_str])
    assert result.exit_code == 0
    es_helper.refresh()
    for expected_crash in expected_crashes:
        crash_id = expected_crash["uuid"]
        actual_crash = es_helper.get_crash_data(crash_id)["processed_crash"]
        assert actual_crash == expected_crash


def test_it_loads_processed_crashes_by_crashid(storage_helper, es_helper):
    """Test whether the module loads processed crashes by crash id."""
    expected_crashes = load_crashes_into_crashstorage_source(storage_helper)
    runner = CliRunner()
    expected_crash = expected_crashes[0]
    crash_id = expected_crash["uuid"]
    result = runner.invoke(load_crashes, ["--crash-id", crash_id])
    assert result.exit_code == 0
    es_helper.refresh()
    actual_crash = es_helper.get_crash_data(crash_id)["processed_crash"]
    assert actual_crash == expected_crash
