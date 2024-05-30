# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import os

from crashstats.crashstats.models import MissingProcessedCrash
from crashstats.crashstats.management.commands.verifyprocessed import Command
from socorro.lib.libdatetime import utc_now
from socorro.lib.libooid import create_new_ooid, date_from_ooid


TODAY = utc_now().strftime("%Y%m%d")
BUCKET_NAME = os.environ.get("resource.boto.bucket_name")


def get_threechars_subset(self):
    """Returns subset of threechars combinations

    This reduces the time it takes to run the tests.

    """
    yield from ["000", "111", "222"]


class TestVerifyProcessed:
    def fetch_crashids(self):
        return MissingProcessedCrash.objects.order_by("crash_id").values_list(
            "crash_id", flat=True
        )

    def create_raw_crash_in_storage(self, storage_helper, bucket_name, crash_id):
        storage_helper.upload(
            bucket_name=bucket_name,
            key=f"v1/raw_crash/{TODAY}/{crash_id}",
            data=b"test",
        )

    def create_processed_crash_in_storage(self, storage_helper, bucket_name, crash_id):
        storage_helper.upload(
            bucket_name=bucket_name,
            key=f"v1/processed_crash/{crash_id}",
            data=b"test",
        )

    def create_processed_crash_in_es(self, es_helper, crash_id):
        crash_date = date_from_ooid(crash_id)
        processed_crash = {
            "uuid": crash_id,
            "signature": "OOM | Small",
            "date_processed": crash_date,
        }
        es_helper.index_crash(processed_crash=processed_crash)

    def test_get_threechars(self):
        cmd = Command()
        threechars = list(sorted(cmd.get_threechars()))

        # We don't want to assert the contents of the whole list, so let's
        # just assert some basic facts and it's probably fine
        assert len(threechars) == 4096
        assert threechars[0] == "000"
        assert threechars[-1] == "fff"

    def test_no_crashes(self, storage_helper, monkeypatch):
        """Verify no crashes in bucket result in no missing crashes."""
        monkeypatch.setattr(Command, "get_threechars", get_threechars_subset)

        bucket = storage_helper.get_crashstorage_bucket()
        storage_helper.create_bucket(bucket)

        cmd = Command()
        missing = cmd.find_missing(num_workers=1, date=TODAY)
        assert missing == []

    def test_no_missing_crashes(self, storage_helper, es_helper, monkeypatch):
        """Verify raw crashes with processed crashes result in no missing crashes."""
        monkeypatch.setattr(Command, "get_threechars", get_threechars_subset)

        bucket = storage_helper.get_crashstorage_bucket()
        storage_helper.create_bucket(bucket)

        # Create a few raw and processed crashes
        crashids = [
            "000" + create_new_ooid()[3:],
            "000" + create_new_ooid()[3:],
            "000" + create_new_ooid()[3:],
        ]
        for crash_id in crashids:
            self.create_raw_crash_in_storage(
                storage_helper, bucket_name=bucket, crash_id=crash_id
            )
            self.create_processed_crash_in_storage(
                storage_helper, bucket_name=bucket, crash_id=crash_id
            )
            self.create_processed_crash_in_es(es_helper, crash_id=crash_id)

        es_helper.refresh()

        cmd = Command()
        missing = cmd.find_missing(num_workers=1, date=TODAY)
        assert missing == []

    def test_missing_crashes(self, storage_helper, es_helper, monkeypatch):
        """Verify it finds a missing crash."""
        monkeypatch.setattr(Command, "get_threechars", get_threechars_subset)

        bucket = storage_helper.get_crashstorage_bucket()
        storage_helper.create_bucket(bucket)

        # Create a raw and processed crash
        crash_id_1 = "000" + create_new_ooid()[3:]
        self.create_raw_crash_in_storage(
            storage_helper, bucket_name=bucket, crash_id=crash_id_1
        )
        self.create_processed_crash_in_storage(
            storage_helper, bucket_name=bucket, crash_id=crash_id_1
        )
        self.create_processed_crash_in_es(es_helper, crash_id=crash_id_1)

        # Create a raw crash
        crash_id_2 = "000" + create_new_ooid()[3:]
        self.create_raw_crash_in_storage(
            storage_helper, bucket_name=bucket, crash_id=crash_id_2
        )

        cmd = Command()
        missing = cmd.find_missing(num_workers=1, date=TODAY)
        assert missing == [crash_id_2]

    def test_missing_crashes_es(self, storage_helper, es_helper, monkeypatch):
        """Verify it finds a processed crash missing in ES."""
        monkeypatch.setattr(Command, "get_threechars", get_threechars_subset)

        bucket = storage_helper.get_crashstorage_bucket()
        storage_helper.create_bucket(bucket)

        # Create a raw and processed crash
        crash_id_1 = "000" + create_new_ooid()[3:]
        self.create_raw_crash_in_storage(
            storage_helper, bucket_name=bucket, crash_id=crash_id_1
        )
        self.create_processed_crash_in_storage(
            storage_helper, bucket_name=bucket, crash_id=crash_id_1
        )
        self.create_processed_crash_in_es(es_helper, crash_id=crash_id_1)

        # Create a raw crash
        crash_id_2 = "000" + create_new_ooid()[3:]
        self.create_raw_crash_in_storage(
            storage_helper, bucket_name=bucket, crash_id=crash_id_2
        )
        self.create_processed_crash_in_storage(
            storage_helper, bucket_name=bucket, crash_id=crash_id_2
        )

        cmd = Command()
        missing = cmd.find_missing(num_workers=1, date=TODAY)
        assert missing == [crash_id_2]

    def test_handle_missing_none_missing(self, capsys):
        cmd = Command()
        cmd.handle_missing(TODAY, [])
        captured = capsys.readouterr()
        assert ("All crashes for %s were processed." % TODAY) in captured.out

    def test_handle_missing_some_missing(self, capsys, db, queue_helper):
        crash_ids = [create_new_ooid(), create_new_ooid()]
        crash_ids.sort()
        cmd = Command()
        cmd.handle_missing(TODAY, crash_ids)
        captured = capsys.readouterr()

        assert "Missing: %s" % crash_ids[0] in captured.out
        assert "Missing: %s" % crash_ids[1] in captured.out

        assert crash_ids == list(self.fetch_crashids())

        assert queue_helper.get_published_crashids("reprocessing") == crash_ids
