# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os

from django.conf import settings

from crashstats.crashstats.models import MissingProcessedCrash
from crashstats.crashstats.management.commands.verifyprocessed import Command
from socorro.lib.ooid import create_new_ooid


TODAY = datetime.datetime.now().strftime("%Y%m%d")
BUCKET_NAME = os.environ.get("resource.boto.bucket_name")


def get_small_entropy(self):
    """Returns small entropy so we're not spending ages cycling through things."""
    for item in ["000", "111", "222"]:
        yield item


class TestVerifyProcessed:
    def fetch_crashids(self):
        return MissingProcessedCrash.objects.order_by("crash_id").values_list(
            "crash_id", flat=True
        )

    def test_get_entropy(self):
        cmd = Command()
        entropy = list(sorted(cmd.get_entropy()))

        # We don't want to assert the contents of the whole list, so let's
        # just assert some basic facts and it's probably fine
        assert len(entropy) == 4096
        assert entropy[0] == "000"
        assert entropy[-1] == "fff"

    def test_no_crashes(self, boto_helper, monkeypatch):
        """Verify no crashes in bucket result in no missing crashes."""
        monkeypatch.setattr(Command, "get_entropy", get_small_entropy)

        bucket = settings.SOCORRO_CONFIG["resource"]["boto"]["bucket_name"]
        boto_helper.create_bucket(bucket)

        cmd = Command()
        missing = cmd.find_missing(num_workers=1, date=TODAY)
        assert missing == []

    def test_no_missing_crashes(self, boto_helper, monkeypatch):
        """Verify raw crashes with processed crashes result in no missing crashes."""
        monkeypatch.setattr(Command, "get_entropy", get_small_entropy)

        bucket = settings.SOCORRO_CONFIG["resource"]["boto"]["bucket_name"]
        boto_helper.create_bucket(bucket)

        # Create a few raw and processed crashes
        crashids = [
            "000" + create_new_ooid()[3:],
            "000" + create_new_ooid()[3:],
            "000" + create_new_ooid()[3:],
        ]
        for crashid in crashids:
            boto_helper.upload_fileobj(
                bucket_name=BUCKET_NAME,
                key="v2/raw_crash/%s/%s/%s" % (crashid[0:3], TODAY, crashid),
                data=b"test",
            )
            boto_helper.upload_fileobj(
                bucket_name=BUCKET_NAME,
                key="v1/processed_crash/%s" % crashid,
                data=b"test",
            )

        cmd = Command()
        missing = cmd.find_missing(num_workers=1, date=TODAY)
        assert missing == []

    def test_missing_crashes(self, boto_helper, monkeypatch):
        """Verify it finds a missing crash."""
        monkeypatch.setattr(Command, "get_entropy", get_small_entropy)

        bucket = settings.SOCORRO_CONFIG["resource"]["boto"]["bucket_name"]
        boto_helper.create_bucket(bucket)

        # Create a raw and processed crash
        crashid_1 = "000" + create_new_ooid()[3:]
        boto_helper.upload_fileobj(
            bucket_name=BUCKET_NAME,
            key="v2/raw_crash/%s/%s/%s" % (crashid_1[0:3], TODAY, crashid_1),
            data=b"test",
        )
        boto_helper.upload_fileobj(
            bucket_name=BUCKET_NAME,
            key="v1/processed_crash/%s" % crashid_1,
            data=b"test",
        )

        # Create a raw crash
        crashid_2 = "000" + create_new_ooid()[3:]
        boto_helper.upload_fileobj(
            bucket_name=BUCKET_NAME,
            key="v2/raw_crash/%s/%s/%s" % (crashid_2[0:3], TODAY, crashid_2),
            data=b"test",
        )

        cmd = Command()
        missing = cmd.find_missing(num_workers=1, date=TODAY)
        assert missing == [crashid_2]

    def test_handle_missing_none_missing(self, capsys):
        cmd = Command()
        cmd.handle_missing(TODAY, [])
        captured = capsys.readouterr()
        assert ("All crashes for %s were processed." % TODAY) in captured.out

    def test_handle_missing_some_missing(self, capsys, db):
        crash_ids = [create_new_ooid(), create_new_ooid()]
        crash_ids.sort()
        cmd = Command()
        cmd.handle_missing(TODAY, crash_ids)
        captured = capsys.readouterr()

        assert "Missing: %s" % crash_ids[0] in captured.out
        assert "Missing: %s" % crash_ids[1] in captured.out

        assert crash_ids == list(self.fetch_crashids())

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

    def test_past_missing_no_longer_missing(self, capsys, db, boto_helper):
        # Create a MissingProcessedCrash row and put the processed crash in the S3
        # bucket. After check_past_missing() runs, the MissingProcessedCrash should
        # have is_processed=True.
        crash_id = create_new_ooid()
        mpe = MissingProcessedCrash(crash_id=crash_id, is_processed=False)
        mpe.save()

        boto_helper.upload_fileobj(
            bucket_name=BUCKET_NAME,
            key="v1/processed_crash/%s" % crash_id,
            data=b"test",
        )

        cmd = Command()
        cmd.check_past_missing()

        mpe = MissingProcessedCrash.objects.get(crash_id=crash_id)
        assert mpe.is_processed is True
