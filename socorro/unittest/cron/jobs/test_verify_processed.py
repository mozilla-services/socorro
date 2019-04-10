# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import datetime
from unittest import mock

from moto import mock_s3_deprecated
import pytest

from socorro.cron.crontabber_app import CronTabberApp
from socorro.lib.ooid import create_new_ooid
from socorro.unittest.cron.crontabber_tests_base import get_config_manager


TODAY = datetime.datetime.now().strftime('%Y%m%d')


@pytest.fixture
def mock_futures():
    """Mock concurrent futures with non-multiprocessing map."""
    class Pool:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args, **kwargs):
            pass

        def map(self, fn, iterable, timeout=None):
            output = []
            for item in iterable:
                output.append(fn(item))
            return output

    with mock.patch('socorro.cron.jobs.verify_processed.concurrent.futures') as mocked_cf:
        mocked_cf.ProcessPoolExecutor.return_value = Pool()
        yield


class TestVerifyProcessedCronApp:
    def _setup_config_manager(self):
        prefix = 'crontabber.class-VerifyProcessedCronApp'
        return get_config_manager(
            jobs='socorro.cron.jobs.verify_processed.VerifyProcessedCronApp|1d',
            overrides={
                prefix + '.crashstorage_class': 'socorro.external.boto.crashstorage.BotoS3CrashStorage'  # noqa
            }
        )

    def fetch_crashids(self, conn):
        """Fetch crashids from db table."""
        cursor = conn.cursor()
        sql = """
        SELECT crash_id, created
        FROM crashstats_missingprocessedcrash
        ORDER BY crash_id
        """
        cursor.execute(sql)
        results = cursor.fetchall()
        return [
            {
                'crash_id': str(result[0]),
                'created': str(result[1])
            }
            for result in results
        ]

    @contextlib.contextmanager
    def get_app(self):
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            crontabberapp = CronTabberApp(config)
            job_classes = crontabberapp.get_job_data('verifyprocessed')

            info = crontabberapp.job_state_database.get('verifyprocessed')
            classconfig = crontabberapp.config.crontabber['class-VerifyProcessedCronApp']
            yield job_classes[0][1](classconfig, info)

    def test_get_entropy(self):
        with self.get_app() as app:
            entropy = list(sorted(app.get_entropy()))

            # We don't want to assert the contents of the whole list, so let's
            # just assert some basic facts and it's probably fine
            assert len(entropy) == 4096
            assert entropy[0] == '000'
            assert entropy[-1] == 'fff'

    @mock_s3_deprecated
    def test_no_crashes(self, mock_futures, boto_helper):
        """Verify no crashes in bucket result in no missing crashes."""
        boto_helper.get_or_create_bucket('crashstats')
        with self.get_app() as app:
            missing = app.find_missing(TODAY)
            assert missing == []

    @mock_s3_deprecated
    def test_no_missing_crashes(self, mock_futures, boto_helper):
        """Verify raw crashes with processed crashes result in no missing crashes."""
        boto_helper.get_or_create_bucket('crashstats')

        # Create a couple raw and processed crashes
        crashids = [
            create_new_ooid(),
            create_new_ooid(),
            create_new_ooid(),
        ]
        for crashid in crashids:
            boto_helper.set_contents_from_string(
                bucket_name='crashstats',
                key='/v2/raw_crash/%s/%s/%s' % (crashid[0:3], TODAY, crashid),
                value='test'
            )
            boto_helper.set_contents_from_string(
                bucket_name='crashstats',
                key='/v1/processed_crash/%s' % crashid,
                value='test'
            )

        with self.get_app() as app:
            missing = app.find_missing(TODAY)
            assert missing == []

    @mock_s3_deprecated
    def test_missing_crashes(self, mock_futures, boto_helper):
        """Verify it finds a missing crash."""
        boto_helper.get_or_create_bucket('crashstats')

        # Create a raw and processed crash
        crashid_1 = create_new_ooid()
        boto_helper.set_contents_from_string(
            bucket_name='crashstats',
            key='/v2/raw_crash/%s/%s/%s' % (crashid_1[0:3], TODAY, crashid_1),
            value='test'
        )
        boto_helper.set_contents_from_string(
            bucket_name='crashstats',
            key='/v1/processed_crash/%s' % crashid_1,
            value='test'
        )

        # Create a raw crash
        crashid_2 = create_new_ooid()
        boto_helper.set_contents_from_string(
            bucket_name='crashstats',
            key='/v2/raw_crash/%s/%s/%s' % (crashid_2[0:3], TODAY, crashid_2),
            value='test'
        )

        with self.get_app() as app:
            missing = app.find_missing(TODAY)
            assert missing == [crashid_2]

    def test_handle_missing_none_missing(self, caplogpp, db_conn):
        caplogpp.set_level('DEBUG')
        with self.get_app() as app:
            app.handle_missing(TODAY, [])
            recs = [rec.message for rec in caplogpp.records]
            assert ('All crashes for %s were processed.' % TODAY) in recs

    def test_handle_missing_some_missing(self, caplogpp, db_conn):
        caplogpp.set_level('DEBUG')
        crash_ids = [
            create_new_ooid(),
            create_new_ooid(),
        ]
        crash_ids.sort()
        with self.get_app() as app:
            app.handle_missing(TODAY, crash_ids)
            recs = [rec.message for rec in caplogpp.records]

            assert 'Missing: %s' % crash_ids[0] in recs
            assert 'Missing: %s' % crash_ids[1] in recs

            crash_ids_in_db = [item['crash_id'] for item in self.fetch_crashids(db_conn)]
            crash_ids_in_db.sort()

            assert crash_ids == crash_ids_in_db
