# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import unittest
from nose.plugins.skip import SkipTest
from nose.tools import eq_, assert_raises
from configman import ConfigurationManager, Namespace
from mock import Mock
from nose.plugins.attrib import attr

from socorro.external import MissingArgumentError, ResourceNotFound, \
                             ResourceUnavailable
from socorro.external.hb import crash_data, crashstorage, hbase_client


_run_integration_tests = os.environ.get('RUN_HBASE_INTEGRATION_TESTS', False)
if _run_integration_tests in ('false', 'False', 'no', '0'):
    _run_integration_tests = False


@attr(integration='hbase')  # for nosetests
class TestIntegrationHBaseCrashData(unittest.TestCase):

    def setUp(self):
        if not _run_integration_tests:
            raise SkipTest("Skipping HBase integration tests")
        self.config_manager = self._common_config_setup()

        with self.config_manager.context() as config:
            store = crashstorage.HBaseCrashStorage(config.hbase)

            # A complete crash report (raw, dump and processed)
            fake_raw_dump_1 = 'peter is a swede'
            fake_raw_dump_2 = 'lars is a norseman'
            fake_raw_dump_3 = 'adrian is a frenchman'
            fake_dumps = {'upload_file_minidump': fake_raw_dump_1,
                          'lars': fake_raw_dump_2,
                          'adrian': fake_raw_dump_3}
            fake_raw = {
                'name': 'Peter',
                'legacy_processing': 0,
                'submitted_timestamp': '2013-05-04'
            }
            fake_processed = {
                'name': 'Peter',
                'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314',
                'completeddatetime': '2012-01-01T00:00:00',
                'email': 'peter@fake.org',
            }

            store.save_raw_crash(
                fake_raw,
                fake_dumps,
                '114559a5-d8e6-428c-8b88-1c1f22120314'
            )
            store.save_processed(fake_processed)

            # A non-processed crash report
            fake_raw = {
                'name': 'Adrian',
                'legacy_processing': 0,
                'submitted_timestamp': '2013-05-04'
            }

            store.save_raw_crash(
                fake_raw,
                fake_dumps,
                '58727744-12f5-454a-bcf5-f688a2120821'
            )

    def tearDown(self):
        with self.config_manager.context() as config:
            connection = hbase_client.HBaseConnectionForCrashReports(
                config.hbase.hbase_host,
                config.hbase.hbase_port,
                config.hbase.hbase_timeout
            )
            for row in connection.merge_scan_with_prefix(
              'crash_reports', '', ['ids:ooid']):
                index_row_key = row['_rowkey']
                connection.client.deleteAllRow(
                  'crash_reports', index_row_key)
            # because of HBase's async nature, deleting can take time
            list(connection.iterator_for_all_legacy_to_be_processed())

    def _common_config_setup(self):
        mock_logging = Mock()
        required_config = Namespace()
        required_config.namespace('hbase')
        required_config.hbase.hbase_class = \
            crashstorage.HBaseCrashStorage
        required_config.hbase.add_option('logger', default=mock_logging)
        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'hbase': {
            'logger': mock_logging
          }}]
        )
        return config_manager

    def test_get(self):
        with self.config_manager.context() as config:

            priorityjobs_mock = Mock()
            service = crash_data.CrashData(
                config=config,
                all_services={'Priorityjobs': priorityjobs_mock}
            )
            params = {
                'datatype': 'raw',
                'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314'
            }

            # Test 1: get a raw dump
            res_expected = ('peter is a swede',
                            'application/octet-stream')
            res = service.get(**params)

            eq_(res, res_expected)

            # Test 2: get a raw crash
            params['datatype'] = 'meta'
            res_expected = {
                'name': 'Peter',
                'legacy_processing': 0,
                'submitted_timestamp': '2013-05-04'
            }
            res = service.get(**params)

            eq_(res, res_expected)

            # Test 3: get a processed crash
            params['datatype'] = 'processed'
            res_expected = {
                'name': 'Peter',
                'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314',
                'completeddatetime': '2012-01-01T00:00:00'
            }
            res = service.get(**params)

            eq_(res, res_expected)

            # Test 3a: get a unredacted processed crash
            params['datatype'] = 'unredacted'
            res_expected = {
                'name': 'Peter',
                'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314',
                'completeddatetime': '2012-01-01T00:00:00',
                'email': 'peter@fake.org',
            }
            res = service.get(**params)

            eq_(res, res_expected)

            # Test 4: missing parameters
            assert_raises(
                MissingArgumentError,
                service.get
            )
            assert_raises(
                MissingArgumentError,
                service.get,
                **{'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314'}
            )

            # Test 5: crash cannot be found
            assert_raises(
                ResourceNotFound,
                service.get,
                **{
                    'uuid': 'c44245f4-c93b-49b8-86a2-c15dc2130504',
                    'datatype': 'processed'
                }
            )
            # Test 5a: crash cannot be found
            assert_raises(
                ResourceNotFound,
                service.get,
                **{
                    'uuid': 'c44245f4-c93b-49b8-86a2-c15dc2130504',
                    'datatype': 'unredacted'
                }
            )

            # Test 6: not yet available crash
            assert_raises(
                ResourceUnavailable,
                service.get,
                **{
                    'uuid': '58727744-12f5-454a-bcf5-f688a2120821',
                    'datatype': 'processed'
                }
            )
            priorityjobs_mock.cls.return_value.create.assert_called_once_with(
                uuid='58727744-12f5-454a-bcf5-f688a2120821'
            )
            priorityjobs_mock.cls.return_value.create.reset_mock()

            # Test 6a: not yet available crash
            assert_raises(
                ResourceUnavailable,
                service.get,
                **{
                    'uuid': '58727744-12f5-454a-bcf5-f688a2120821',
                    'datatype': 'unredacted'
                }
            )
            priorityjobs_mock.cls.return_value.create.assert_called_once_with(
                uuid='58727744-12f5-454a-bcf5-f688a2120821'
            )

            # Test 7: raw crash cannot be found
            assert_raises(
                ResourceNotFound,
                service.get,
                **{
                    'uuid': 'c44245f4-c93b-49b8-86a2-c15dc2130505',
                    'datatype': 'raw'
                }
            )
