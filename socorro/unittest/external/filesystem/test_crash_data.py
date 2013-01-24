# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import shutil
import tempfile
import unittest
from configman import ConfigurationManager, Namespace
from mock import Mock, patch
from nose.plugins.attrib import attr

from socorro.external import MissingOrBadArgumentError, ResourceNotFound, \
                             ResourceUnavailable
from socorro.external.filesystem import crash_data, crashstorage


@attr(integration='filesystem')  # for nosetests
class IntegrationTestCrashData(unittest.TestCase):

    def setUp(self):
        """Insert fake data into filesystem. """
        self.std_tmp_dir = tempfile.mkdtemp()
        self.def_tmp_dir = tempfile.mkdtemp()
        self.pro_tmp_dir = tempfile.mkdtemp()

        self.config_manager = self._common_config_setup()

        with self.config_manager.context() as config:
            store = crashstorage.FileSystemCrashStorage(config.filesystem)
            fake_dump = 'this is a fake dump'
            fake_raw = {'name': 'Peter', 'legacy_processing': 0,
                        "submitted_timestamp": '2012-05-04 15:10:33'}
            fake_processed = {
                'name': 'Peter',
                'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314'
            }

            store.save_raw_crash(
                fake_raw,
                fake_dump,
                '114559a5-d8e6-428c-8b88-1c1f22120314'
            )
            store.save_processed(fake_processed)

            fake_dump = 'this is another fake dump'
            fake_raw = {'name': 'Adrian', 'legacy_processing': 0,
                        "submitted_timestamp": '2012-05-04 15:10:33'}

            store.save_raw_crash(
                fake_raw,
                fake_dump,
                '58727744-12f5-454a-bcf5-f688af393821'
            )

    def tearDown(self):
        """Remove all temp files and folders. """
        shutil.rmtree(self.std_tmp_dir)
        shutil.rmtree(self.def_tmp_dir)
        shutil.rmtree(self.pro_tmp_dir)

    def _common_config_setup(self):
        mock_logging = Mock()
        required_config = Namespace()
        required_config.namespace('filesystem')
        required_config.filesystem = \
            crashstorage.FileSystemCrashStorage.get_required_config()
        required_config.filesystem.add_option('logger', default=mock_logging)
        config_manager = ConfigurationManager(
          [required_config],
          app_name='testapp',
          app_version='1.0',
          app_description='app description',
          values_source_list=[{'filesystem': {
            'logger': mock_logging,
            'std_fs_root': self.std_tmp_dir,
            'def_fs_root': self.def_tmp_dir,
            'pro_fs_root': self.pro_tmp_dir,
          }}]
        )
        return config_manager

    @patch('socorro.external.postgresql.priorityjobs.Priorityjobs')
    def test_get(self, priorityjobs_mock):
        with self.config_manager.context() as config:
            service = crash_data.CrashData(config=config)
            params = {
                'datatype': 'raw',
                'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314'
            }

            # Test 1: get a raw dump
            res_expected = ('this is a fake dump', 'application/octet-stream')
            res = service.get(**params)

            self.assertEqual(res, res_expected)

            # Test 2: get a raw crash
            params['datatype'] = 'meta'
            res_expected = {'name': 'Peter', 'legacy_processing': 0,
                            "submitted_timestamp": '2012-05-04 15:10:33'}
            res = service.get(**params)

            self.assertEqual(res, res_expected)

            # Test 3: get a processed crash
            params['datatype'] = 'processed'
            res_expected = {
                'name': 'Peter',
                'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314'
            }
            res = service.get(**params)

            self.assertEqual(res, res_expected)

            # Test 4: missing parameters
            self.assertRaises(
                MissingOrBadArgumentError,
                service.get
            )
            self.assertRaises(
                MissingOrBadArgumentError,
                service.get,
                **{'uuid': '114559a5-d8e6-428c-8b88-1c1f22120314'}
            )

            # Test 5: crash cannot be found
            self.assertRaises(
                ResourceNotFound,
                service.get,
                **{
                    'uuid': 'c44245f4-c93b-49b8-86a2-c15dc3a695cb',
                    'datatype': 'processed'
                }
            )

            # Test 6: not yet available crash
            self.assertRaises(
                ResourceUnavailable,
                service.get,
                **{
                    'uuid': '58727744-12f5-454a-bcf5-f688af393821',
                    'datatype': 'processed'
                }
            )
            priorityjobs_mock.return_value.create.assert_called_once_with(
                uuid='58727744-12f5-454a-bcf5-f688af393821'
            )

            # Test 7: raw crash cannot be found
            self.assertRaises(
                ResourceNotFound,
                service.get,
                **{
                    'uuid': 'c44245f4-c93b-49b8-86a2-c15dc3a695cb',
                    'datatype': 'raw'
                }
            )
