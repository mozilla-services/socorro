from datetime import datetime
import json
import gzip
from os.path import join
import tarfile
import tempfile


from configman.dotdict import DotDict
from mock import Mock

from socorro.external.fs.crashstorage import (
    TarFileWritingCrashStore,
    TarFileSequentialReadingCrashStore,
)
from socorro.external.crashstorage_base import Redactor
from socorro.lib.datetimeutil import JsonDTISOEncoder
from socorro.unittest.testbase import TestCase

TEMP_DIR = tempfile.gettempdir()


class TestTarFileWritingCrashStorage(TestCase):

    def setUp(self):
        super(TestTarFileWritingCrashStorage, self).setUp()

    def _get_config(self):
        config = DotDict()
        config.logger = Mock()
        config.tarball_name = join(TEMP_DIR, 'a_tarball_name.tar')
        config.tarfile_module = Mock()
        config.gzip_module = Mock()
        config.redactor_class = Mock()

        return config

    def test_init(self):
        config = self._get_config()

        # the call to be tested
        tar_store = TarFileWritingCrashStore(config)

        # this is what should have happened
        assert not hasattr(tar_store, 'tar_file')
        assert isinstance(tar_store.tarfile_module, Mock)
        assert isinstance(tar_store.gzip_module, Mock)
        tar_store.tarfile_module.open.assert_called_once_with(
            config.tarball_name,
            'w'
        )

    def test_save_processed(self):
        config = self._get_config()
        config.tarfile_module = tarfile
        config.gzip_module = gzip

        tar_store = TarFileWritingCrashStore(config)

        processed_crash = {
            'crash_id': '091204bd-87c0-42ba-8f58-554492141212',
            'payload': 'nothing to see here',
            'some_date': datetime(1960, 5, 4, 15, 10)
        }
        processed_crash_as_str = json.dumps(
            processed_crash,
            cls=JsonDTISOEncoder
        )

        # the call to be tested
        tar_store.save_processed(processed_crash)

        # this try to get it back
        tar_store.close()

        result_tar_fp = tarfile.TarFile(join(TEMP_DIR, 'a_tarball_name.tar'))
        result_gzip_fp = gzip.GzipFile(
            fileobj=result_tar_fp.extractfile(
                '091204bd-87c0-42ba-8f58-554492141212.jsonz'
            )
        )
        reconstituted_processed_crash_as_str = result_gzip_fp.read().strip()

        assert processed_crash_as_str == reconstituted_processed_crash_as_str


class TestTarFileSequentialReadingCrashStorage(TestCase):

    def _get_config(self):
        config = DotDict()
        config.logger = Mock()
        config.tarball_name = join(TEMP_DIR, 'a_tarball_name.tar')
        config.tarfile_module = tarfile
        config.gzip_module = gzip
        config.redactor_class = Redactor
        config.forbidden_keys = ''

        return config

    def test_get_processed(self):
        config = self._get_config()
        config.tarfile_module = tarfile
        config.gzip_module = gzip

        writing_tar_store = TarFileWritingCrashStore(config)

        processed_crash_1 = {
            'crash_id': '091204bd-87c0-42ba-8f58-554492141212',
            'payload': 'nothing to see here',
            'some_date': "1960-05-04T15:10:00"
        }
        processed_crash_2 = {
            'crash_id': '666884bd-87c0-42ba-8f58-554492141212',
            'payload': 'nothing to see here, ether',
            'some_date': "1974-05-04T15:10:00"
        }

        writing_tar_store.save_processed(processed_crash_1)
        writing_tar_store.save_processed(processed_crash_2)
        writing_tar_store.close()

        reading_tar_store = TarFileSequentialReadingCrashStore(config)

        reconstituted_processed_crash_1 = reading_tar_store.get_processed(
            'it does not matter what is said here'
        )
        assert processed_crash_1 == reconstituted_processed_crash_1

        reconstituted_processed_crash_2 = reading_tar_store.get_processed(
            'it does not matter what is said here'
        )
        assert processed_crash_2 == reconstituted_processed_crash_2
