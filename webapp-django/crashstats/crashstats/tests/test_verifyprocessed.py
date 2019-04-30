# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os

from moto import mock_s3_deprecated

from crashstats.crashstats.models import MissingProcessedCrash
from crashstats.crashstats.management.commands.verifyprocessed import Command
from socorro.lib.ooid import create_new_ooid


TODAY = datetime.datetime.now().strftime('%Y%m%d')
BUCKET_NAME = os.environ.get('resource.boto.bucket_name')


class TestVerifyProcessed:
    def fetch_crashids(self):
        return MissingProcessedCrash.objects.order_by('crash_id').values_list('crash_id', flat=True)

    def test_get_entropy(self):
        cmd = Command()
        entropy = list(sorted(cmd.get_entropy()))

        # We don't want to assert the contents of the whole list, so let's
        # just assert some basic facts and it's probably fine
        assert len(entropy) == 4096
        assert entropy[0] == '000'
        assert entropy[-1] == 'fff'

    @mock_s3_deprecated
    def test_no_crashes(self, boto_helper):
        """Verify no crashes in bucket result in no missing crashes."""
        boto_helper.get_or_create_bucket(BUCKET_NAME)
        cmd = Command()
        missing = cmd.find_missing(num_workers=1, date=TODAY)
        assert missing == []

    @mock_s3_deprecated
    def test_no_missing_crashes(self, boto_helper):
        """Verify raw crashes with processed crashes result in no missing crashes."""
        boto_helper.get_or_create_bucket(BUCKET_NAME)

        # Create a couple raw and processed crashes
        crashids = [
            create_new_ooid(),
            create_new_ooid(),
            create_new_ooid(),
        ]
        for crashid in crashids:
            boto_helper.set_contents_from_string(
                bucket_name=BUCKET_NAME,
                key='/v2/raw_crash/%s/%s/%s' % (crashid[0:3], TODAY, crashid),
                value='test'
            )
            boto_helper.set_contents_from_string(
                bucket_name=BUCKET_NAME,
                key='/v1/processed_crash/%s' % crashid,
                value='test'
            )

        cmd = Command()
        missing = cmd.find_missing(num_workers=1, date=TODAY)
        assert missing == []

    @mock_s3_deprecated
    def test_missing_crashes(self, boto_helper):
        """Verify it finds a missing crash."""
        boto_helper.get_or_create_bucket(BUCKET_NAME)

        # Create a raw and processed crash
        crashid_1 = create_new_ooid()
        boto_helper.set_contents_from_string(
            bucket_name=BUCKET_NAME,
            key='/v2/raw_crash/%s/%s/%s' % (crashid_1[0:3], TODAY, crashid_1),
            value='test'
        )
        boto_helper.set_contents_from_string(
            bucket_name=BUCKET_NAME,
            key='/v1/processed_crash/%s' % crashid_1,
            value='test'
        )

        # Create a raw crash
        crashid_2 = create_new_ooid()
        boto_helper.set_contents_from_string(
            bucket_name=BUCKET_NAME,
            key='/v2/raw_crash/%s/%s/%s' % (crashid_2[0:3], TODAY, crashid_2),
            value='test'
        )

        cmd = Command()
        missing = cmd.find_missing(num_workers=1, date=TODAY)
        assert missing == [crashid_2]

    def test_handle_missing_none_missing(self, capsys):
        cmd = Command()
        cmd.handle_missing(TODAY, [])
        captured = capsys.readouterr()
        assert ('All crashes for %s were processed.' % TODAY) in captured.out

    def test_handle_missing_some_missing(self, capsys, db):
        crash_ids = [
            create_new_ooid(),
            create_new_ooid(),
        ]
        crash_ids.sort()
        cmd = Command()
        cmd.handle_missing(TODAY, crash_ids)
        captured = capsys.readouterr()

        assert 'Missing: %s' % crash_ids[0] in captured.out
        assert 'Missing: %s' % crash_ids[1] in captured.out

        assert crash_ids == list(self.fetch_crashids())
