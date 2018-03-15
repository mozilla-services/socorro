# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
from os.path import join

from moto import mock_s3_deprecated
import pytest

from socorro.external.boto.connection_context import S3ConnectionContext
from socorro.external.boto.crashstorage import (
    BotoS3CrashStorage,
    TelemetryBotoS3CrashStorage,
)
from socorro.external.crashstorage_base import (
    CrashIDNotFound,
    MemoryDumpsMapping,
)
from socorro.lib.util import DotDict
from socorro.unittest.external.boto import get_config


a_raw_crash = {
    "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
}
a_raw_crash_as_string = json.dumps(a_raw_crash)


class ABadDeal(Exception):
    pass


class ConditionallyABadDeal(Exception):
    pass


S3ConnectionContext.operational_exceptions = (ABadDeal, )
S3ConnectionContext.conditional_exceptions = (ConditionallyABadDeal, )


def setup_mocked_s3_storage(
    tmpdir=None,
    storage_class=BotoS3CrashStorage,
    bucket_name='crash_storage',
    **extra
):
    values_source = {
        'resource_class': S3ConnectionContext,
        'bucket_name': bucket_name,
        'prefix': 'dev',
    }
    values_source.update(extra)

    config = get_config(
        cls=storage_class,
        values_source=values_source
    )
    if tmpdir is not None:
        config.temporary_file_system_storage_path = str(tmpdir)

    return storage_class(config)


class TestBotoS3CrashStorage:
    def _fake_processed_crash(self):
        d = DotDict()
        # these keys survive redaction
        d.a = DotDict()
        d.a.b = DotDict()
        d.a.b.c = 11
        d.sensitive = DotDict()
        d.sensitive.x = 2
        d.not_url = 'not a url'

        return d

    def _fake_redacted_processed_crash(self):
        d = self._fake_unredacted_processed_crash()
        del d.url
        del d.email
        del d.user_id
        del d.exploitability
        del d.json_dump.sensitive
        del d.upload_file_minidump_flash1.json_dump.sensitive
        del d.upload_file_minidump_flash2.json_dump.sensitive
        del d.upload_file_minidump_browser.json_dump.sensitive

        return d

    def _fake_unredacted_processed_crash(self):
        d = self._fake_processed_crash()

        # these keys do not survive redaction
        d['url'] = 'http://very.embarassing.com'
        d['email'] = 'lars@fake.com'
        d['user_id'] = '3333'
        d['exploitability'] = 'yep'
        d.json_dump = DotDict()
        d.json_dump.sensitive = 22
        d.upload_file_minidump_flash1 = DotDict()
        d.upload_file_minidump_flash1.json_dump = DotDict()
        d.upload_file_minidump_flash1.json_dump.sensitive = 33
        d.upload_file_minidump_flash2 = DotDict()
        d.upload_file_minidump_flash2.json_dump = DotDict()
        d.upload_file_minidump_flash2.json_dump.sensitive = 33
        d.upload_file_minidump_browser = DotDict()
        d.upload_file_minidump_browser.json_dump = DotDict()
        d.upload_file_minidump_browser.json_dump.sensitive = DotDict()
        d.upload_file_minidump_browser.json_dump.sensitive.exploitable = 55
        d.upload_file_minidump_browser.json_dump.sensitive.secret = 66

        return d

    def _fake_unredacted_processed_crash_as_string(self):
        d = self._fake_unredacted_processed_crash()
        s = json.dumps(d)
        return s

    @mock_s3_deprecated
    def test_save_raw_crash_no_dumps(self, boto_helper):
        boto_s3_store = setup_mocked_s3_storage()

        # Run save_raw_crash
        boto_s3_store.save_raw_crash(
            {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            # This is an empty set of dumps--no dumps!
            MemoryDumpsMapping(),
            "0bba929f-8721-460c-dead-a43c20071027"
        )

        # Verify the raw_crash made it to the right place and has the right
        # contents
        raw_crash = boto_helper.get_contents_as_string(
            bucket_name='crash_storage',
            key='dev/v1/raw_crash/0bba929f-8721-460c-dead-a43c20071027'
        )

        assert (
            json.loads(raw_crash) ==
            {
                "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
            }
        )

        # Verify dump_names made it to the right place and has the right
        # contents
        dump_names = boto_helper.get_contents_as_string(
            bucket_name='crash_storage',
            key='dev/v1/dump_names/0bba929f-8721-460c-dead-a43c20071027'
        )
        assert json.loads(dump_names) == []

    @mock_s3_deprecated
    def test_save_raw_crash_no_dumps_existing_bucket(self, boto_helper):
        boto_s3_store = setup_mocked_s3_storage()

        # Create the bucket
        boto_helper.get_or_create_bucket('crash_storage')

        # Run save_raw_crash
        boto_s3_store.save_raw_crash(
            {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            # This is an empty set of dumps--no dumps!
            MemoryDumpsMapping(),
            "0bba929f-8721-460c-dead-a43c20071027"
        )

        # Verify the raw_crash made it to the right place and has the right
        # contents
        raw_crash = boto_helper.get_contents_as_string(
            bucket_name='crash_storage',
            key='dev/v1/raw_crash/0bba929f-8721-460c-dead-a43c20071027'
        )

        assert (
            json.loads(raw_crash) ==
            {
                "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
            }
        )

        # Verify dump_names made it to the right place and has the right
        # contents
        dump_names = boto_helper.get_contents_as_string(
            bucket_name='crash_storage',
            key='dev/v1/dump_names/0bba929f-8721-460c-dead-a43c20071027'
        )
        assert json.loads(dump_names) == []

    @mock_s3_deprecated
    def test_save_raw_crash_with_dumps(self, boto_helper):
        boto_s3_store = setup_mocked_s3_storage()

        # Run save_raw_crash
        boto_s3_store.save_raw_crash(
            {"submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"},
            MemoryDumpsMapping(
                {'dump': 'fake dump', 'flash_dump': 'fake flash dump'}
            ),
            "0bba929f-8721-460c-dead-a43c20071027"
        )

        # Verify the raw_crash made it to the right place and has the right
        # contents
        raw_crash = boto_helper.get_contents_as_string(
            bucket_name='crash_storage',
            key='dev/v1/raw_crash/0bba929f-8721-460c-dead-a43c20071027'
        )

        assert (
            json.loads(raw_crash) ==
            {
                "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
            }
        )

        # Verify dump_names made it to the right place and has the right
        # contents
        dump_names = boto_helper.get_contents_as_string(
            bucket_name='crash_storage',
            key='dev/v1/dump_names/0bba929f-8721-460c-dead-a43c20071027'
        )
        assert sorted(json.loads(dump_names)) == ['dump', 'flash_dump']

        # Verify dumps
        dump = boto_helper.get_contents_as_string(
            bucket_name='crash_storage',
            key='dev/v1/dump/0bba929f-8721-460c-dead-a43c20071027'
        )
        assert dump == 'fake dump'

        flash_dump = boto_helper.get_contents_as_string(
            bucket_name='crash_storage',
            key='dev/v1/flash_dump/0bba929f-8721-460c-dead-a43c20071027'
        )
        assert flash_dump == 'fake flash dump'

    @mock_s3_deprecated
    def test_save_processed(self, boto_helper):
        boto_s3_store = setup_mocked_s3_storage()

        # the tested call
        boto_s3_store.save_processed({
            "uuid": "0bba929f-8721-460c-dead-a43c20071027",
            "completeddatetime": "2012-04-08 10:56:50.902884",
            "signature": 'now_this_is_a_signature'
        })

        # Verify the processed crash was put in the right place and has the
        # right contents
        processed_crash = boto_helper.get_contents_as_string(
            bucket_name='crash_storage',
            key='dev/v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027'
        )
        assert (
            json.loads(processed_crash) ==
            {
                "uuid": "0bba929f-8721-460c-dead-a43c20071027",
                "completeddatetime": "2012-04-08 10:56:50.902884",
                "signature": 'now_this_is_a_signature'
            }
        )

    @mock_s3_deprecated
    def test_save_raw_and_processed(self, boto_helper):
        boto_s3_store = setup_mocked_s3_storage()

        # the tested call
        boto_s3_store.save_raw_and_processed(
            {
                "submitted_timestamp": "2013-01-09T22:21:18.646733+00:00"
            },
            None,
            {
                "uuid": "0bba929f-8721-460c-dead-a43c20071027",
                "completeddatetime": "2012-04-08 10:56:50.902884",
                "signature": 'now_this_is_a_signature'
            },
            "0bba929f-8721-460c-dead-a43c20071027"
        )

        # Verify processed crash is saved
        processed_crash = boto_helper.get_contents_as_string(
            bucket_name='crash_storage',
            key='dev/v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027'
        )
        assert (
            json.loads(processed_crash) ==
            {
                "signature": 'now_this_is_a_signature',
                "uuid": "0bba929f-8721-460c-dead-a43c20071027",
                "completeddatetime": "2012-04-08 10:56:50.902884",
            }
        )
        # Verify nothing else got saved
        assert (
            boto_helper.list(bucket_name='crash_storage') ==
            [u'dev/v1/processed_crash/0bba929f-8721-460c-dead-a43c20071027']
        )

    @mock_s3_deprecated
    def test_get_raw_crash(self, boto_helper):
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/raw_crash/936ce666-ff3b-4c7a-9674-367fe2120408',
            value=a_raw_crash_as_string
        )

        # the tested call
        boto_s3_store = setup_mocked_s3_storage()
        result = boto_s3_store.get_raw_crash("936ce666-ff3b-4c7a-9674-367fe2120408")

        assert result == a_raw_crash

    @mock_s3_deprecated
    def test_get_raw_crash_not_found(self):
        boto_s3_store = setup_mocked_s3_storage()

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get_raw_crash('0bba929f-dead-dead-dead-a43c20071027')

    @mock_s3_deprecated
    def test_get_raw_dump(self, boto_helper):
        """test fetching the raw dump without naming it"""
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408',
            value='this is a raw dump'
        )

        # the tested call
        boto_s3_store = setup_mocked_s3_storage()
        result = boto_s3_store.get_raw_dump('936ce666-ff3b-4c7a-9674-367fe2120408')
        assert result == 'this is a raw dump'

    @mock_s3_deprecated
    def test_get_raw_dump_not_found(self):
        boto_s3_store = setup_mocked_s3_storage()

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get_raw_dump('0bba929f-dead-dead-dead-a43c20071027')

    @mock_s3_deprecated
    def test_get_raw_dump_upload_file_minidump(self, boto_helper):
        """test fetching the raw dump, naming it 'upload_file_minidump'"""
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408',
            value='this is a raw dump'
        )

        # the tested call
        boto_s3_store = setup_mocked_s3_storage()
        result = boto_s3_store.get_raw_dump(
            '936ce666-ff3b-4c7a-9674-367fe2120408',
            name='upload_file_minidump'
        )

        assert result == 'this is a raw dump'

    @mock_s3_deprecated
    def test_get_raw_dump_empty_string(self, boto_helper):
        """test fetching the raw dump, naming it with empty string"""
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408',
            value='this is a raw dump'
        )

        # the tested call
        boto_s3_store = setup_mocked_s3_storage()
        result = boto_s3_store.get_raw_dump('936ce666-ff3b-4c7a-9674-367fe2120408', name='')
        assert result == 'this is a raw dump'

    @mock_s3_deprecated
    def test_get_raw_dumps(self, boto_helper):
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/dump_names/936ce666-ff3b-4c7a-9674-367fe2120408',
            value='["dump", "flash_dump", "city_dump"]'
        )
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408',
            value='this is "dump", the first one'
        )
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/flash_dump/936ce666-ff3b-4c7a-9674-367fe2120408',
            value='this is "flash_dump", the second one'
        )
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/city_dump/936ce666-ff3b-4c7a-9674-367fe2120408',
            value='this is "city_dump", the last one'
        )

        # the tested call
        boto_s3_store = setup_mocked_s3_storage()
        result = boto_s3_store.get_raw_dumps('936ce666-ff3b-4c7a-9674-367fe2120408')
        assert (
            result == {
                'dump': 'this is "dump", the first one',
                'flash_dump': 'this is "flash_dump", the second one',
                'city_dump': 'this is "city_dump", the last one',
            }
        )

    @mock_s3_deprecated
    def test_get_raw_dumps_not_found(self):
        boto_s3_store = setup_mocked_s3_storage()

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get_raw_dumps('0bba929f-dead-dead-dead-a43c20071027')

    @mock_s3_deprecated
    def test_get_raw_dumps_as_files(self, boto_helper, tmpdir):
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/dump_names/936ce666-ff3b-4c7a-9674-367fe2120408',
            value='["dump", "flash_dump", "city_dump"]'
        )
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/dump/936ce666-ff3b-4c7a-9674-367fe2120408',
            value='this is "dump", the first one'
        )
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/flash_dump/936ce666-ff3b-4c7a-9674-367fe2120408',
            value='this is "flash_dump", the second one'
        )
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/city_dump/936ce666-ff3b-4c7a-9674-367fe2120408',
            value='this is "city_dump", the last one'
        )

        # the tested call
        boto_s3_store = setup_mocked_s3_storage(tmpdir=tmpdir)
        result = boto_s3_store.get_raw_dumps_as_files(
            '936ce666-ff3b-4c7a-9674-367fe2120408'
        )

        # we don't care much about the mocked internals as the bulk of that
        # function is tested elsewhere.
        # we just need to be concerned about the file writing worked
        expected = {
            'flash_dump': join(
                str(tmpdir),
                '936ce666-ff3b-4c7a-9674-367fe2120408.flash_dump.TEMPORARY.dump'
            ),
            'city_dump': join(
                str(tmpdir),
                '936ce666-ff3b-4c7a-9674-367fe2120408.city_dump.TEMPORARY.dump'
            ),
            'upload_file_minidump': join(
                str(tmpdir),
                '936ce666-ff3b-4c7a-9674-367fe2120408.upload_file_minidump.TEMPORARY.dump'
            )
        }
        assert result == expected

    @mock_s3_deprecated
    def test_get_unredacted_processed(self, boto_helper):
        boto_helper.set_contents_from_string(
            bucket_name='crash_storage',
            key='dev/v1/processed_crash/936ce666-ff3b-4c7a-9674-367fe2120408',
            value=self._fake_unredacted_processed_crash_as_string()
        )

        # the tested call
        boto_s3_store = setup_mocked_s3_storage()
        result = boto_s3_store.get_unredacted_processed(
            '936ce666-ff3b-4c7a-9674-367fe2120408'
        )

        assert result == self._fake_unredacted_processed_crash()

    @mock_s3_deprecated
    def test_get_undredacted_processed_not_found(self):
        boto_s3_store = setup_mocked_s3_storage()

        with pytest.raises(CrashIDNotFound):
            boto_s3_store.get_unredacted_processed('0bba929f-dead-dead-dead-a43c20071027')


class TestTelemetryBotoS3CrashStorage:
    def get_s3_store(self):
        config = get_config(
            cls=TelemetryBotoS3CrashStorage,
            values_source={
                'resource_class': S3ConnectionContext,
                'bucket_name': 'telemetry-crashes',
            }
        )

        return TelemetryBotoS3CrashStorage(config)

    @mock_s3_deprecated
    def test_save_raw_and_processed(self, boto_helper):
        boto_s3_store = self.get_s3_store()

        # Run save_raw_and_processed
        boto_s3_store.save_raw_and_processed(
            {
                'submitted_timestamp': '2013-01-09T22:21:18.646733+00:00'
            },
            None,
            {
                'uuid': '0bba929f-8721-460c-dead-a43c20071027',
                'completeddatetime': '2012-04-08 10:56:50.902884',
                'signature': 'now_this_is_a_signature',
                'os_name': 'Linux',
            },
            '0bba929f-8721-460c-dead-a43c20071027'
        )

        # Get the crash data we just saved from the bucket and verify it's
        # contents
        crash_data = boto_helper.get_contents_as_string(
            bucket_name='telemetry-crashes',
            key='/v1/crash_report/20071027/0bba929f-8721-460c-dead-a43c20071027'
        )
        assert (
            json.loads(crash_data) ==
            {
                'platform': 'Linux',
                'signature': 'now_this_is_a_signature',
                'uuid': '0bba929f-8721-460c-dead-a43c20071027'
            }
        )

    @mock_s3_deprecated
    def test_get_unredacted_processed(self, boto_helper):
        crash_data = {
            'platform': 'Linux',
            'signature': 'now_this_is_a_signature',
            'uuid': '0bba929f-8721-460c-dead-a43c20071027'
        }

        # Save the data to S3 so we have something to get
        boto_helper.set_contents_from_string(
            bucket_name='telemetry-crashes',
            key='/v1/crash_report/20071027/0bba929f-8721-460c-dead-a43c20071027',
            value=json.dumps(crash_data)
        )

        # Get the crash and assert it's the same data
        boto_s3_store = self.get_s3_store()

        data = boto_s3_store.get_unredacted_processed(
            crash_id='0bba929f-8721-460c-dead-a43c20071027'
        )
        assert data == crash_data
