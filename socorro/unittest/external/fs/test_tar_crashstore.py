from nose.tools import eq_, ok_, assert_raises
from mock import Mock, patch
from datetime import datetime

import json

from configman.dotdict import DotDict

from socorro.external.fs.crashstorage import (
    TarFileCrashStore,
)
from socorro.external.crashstorage_base import CrashIDNotFound
from socorro.unittest.testbase import TestCase

class TestTarCrashStorage(TestCase):

    def setUp(self):
        super(TestTarCrashStorage, self).setUp()

    def _get_config(self):
        config = DotDict()
        config.logger = Mock()
        config.tarball_name = '/tmp/a_tarball_name.tar'
        config.temp_directory = '/tmp'
        config.tarfile_module = Mock()
        config.gzip_module = Mock()
        config.os_module = Mock()
        config.redactor_class = Mock()

        return config

    def test_init(self):
        config = self._get_config()

        # the call to be tested
        tar_store = TarFileCrashStore(config)

        # this is what should have happened
        ok_(not hasattr(tar_store, 'tar_file'))
        ok_(isinstance(tar_store.tarfile_module, Mock))
        ok_(isinstance(tar_store.gzip_module, Mock))
        ok_(isinstance(tar_store.os_module, Mock))

    def test_save_processed(self):
        config = self._get_config()
        tar_store = TarFileCrashStore(config)

        processed_crash = {
            'crash_id': '091204bd-87c0-42ba-8f58-554492141212',
            'payload': 'nothing to see here',
            'some_date': datetime(1960, 5, 4, 15, 10)
        }
        processed_crash_as_string = json.dumps(
            processed_crash,
            default=tar_store.stringify_datetimes
        )

        # the call to be tested
        tar_store.save_processed(processed_crash)

        # this is what should have happened
        ok_(hasattr(tar_store, 'tar_file'))
        tar_store.tarfile_module.open.assert_called_once_with(
            config.tarball_name,
            'w'
        )
        tar_store.gzip_module.open.assert_called_once_with(
            '/tmp/091204bd-87c0-42ba-8f58-554492141212.jsonz',
            'w',
            9
        )
        mocked_file_handle = tar_store.gzip_module.open.return_value
        mocked_file_handle.write.assert_called_once_with(
            processed_crash_as_string
        )
        mocked_file_handle.close.assert_called_once_with()
        tar_store.tar_file.add.assert_called_once_with(
            '/tmp/091204bd-87c0-42ba-8f58-554492141212.jsonz',
            '09/12/091204bd-87c0-42ba-8f58-554492141212.jsonz'
        )
        tar_store.os_module.unlink.assert_called_once_with(
            '/tmp/091204bd-87c0-42ba-8f58-554492141212.jsonz'
        )


