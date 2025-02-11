# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from crashstats.crashstats.models import MissingProcessedCrash
from crashstats.crashstats.management.commands.updatemissing import Command
from socorro.lib.libdatetime import utc_now
from socorro.lib.libooid import create_new_ooid, date_from_ooid


TODAY = utc_now().strftime("%Y%m%d")


class TestUpdateMissing:
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

    def test_past_missing_still_missing(self, capsys, db):
        # Create a MissingProcessedCrash row, but don't put the processed crash in the
        # bucket. After check_past_missing() runs, the MissingProcessedCrash should
        # still have is_processed=False.
        crash_id = create_new_ooid()
        mpe = MissingProcessedCrash(crash_id=crash_id, is_processed=False)
        mpe.save()

        cmd = Command()
        cmd.check_past_missing()

        mpe = MissingProcessedCrash.objects.get(crash_id=crash_id)
        assert mpe.is_processed is False

    def test_past_missing_no_longer_missing(
        self, capsys, db, es_helper, storage_helper
    ):
        # Create a MissingProcessedCrash row and put the processed crash in the
        # bucket. After check_past_missing() runs, the MissingProcessedCrash should
        # have is_processed=True.
        crash_id = create_new_ooid()
        mpe = MissingProcessedCrash(crash_id=crash_id, is_processed=False)
        mpe.save()

        bucket = storage_helper.get_crashstorage_bucket()
        self.create_raw_crash_in_storage(
            storage_helper, bucket_name=bucket, crash_id=crash_id
        )
        self.create_processed_crash_in_storage(
            storage_helper, bucket_name=bucket, crash_id=crash_id
        )
        self.create_processed_crash_in_es(es_helper, crash_id)

        cmd = Command()
        cmd.check_past_missing()

        mpe = MissingProcessedCrash.objects.get(crash_id=crash_id)
        assert mpe.is_processed is True
