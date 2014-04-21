# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import shutil
import os
import tempfile

from nose.tools import ok_

from crontabber.app import CronTabber
from crontabber.tests.base import IntegrationTestCaseBase

_here = os.path.dirname(__file__)

ZIP_FILE = os.path.join(_here, 'sample.zip')
TAR_FILE = os.path.join(_here, 'sample.tar')
TGZ_FILE = os.path.join(_here, 'sample.tgz')
TARGZ_FILE = os.path.join(_here, 'sample.tar.gz')

assert os.path.isfile(ZIP_FILE)
assert os.path.isfile(TAR_FILE)
assert os.path.isfile(TGZ_FILE)
assert os.path.isfile(TARGZ_FILE)


#==============================================================================
class TestSymbolsUnpack(IntegrationTestCaseBase):

    def setUp(self):
        super(TestSymbolsUnpack, self).setUp()

        self.temp_source_directory = tempfile.mkdtemp('archives')
        self.temp_destination_directory = tempfile.mkdtemp('symbols')

    def tearDown(self):
        super(TestSymbolsUnpack, self).tearDown()
        shutil.rmtree(self.temp_source_directory)
        shutil.rmtree(self.temp_destination_directory)

    def _setup_config_manager(self):
        _super = super(TestSymbolsUnpack, self)._setup_config_manager
        return _super(
            'socorro.cron.jobs.symbolsunpack.SymbolsUnpackCronApp|1h',
            {
                'source_directory': self.temp_source_directory,
                'destination_directory': self.temp_destination_directory
            }
        )

    def test_symbols_unpack_empty(self):
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

        information = self._load_structure()
        assert information['symbols-unpack']
        assert not information['symbols-unpack']['last_error']
        assert information['symbols-unpack']['last_success']

    def test_symbols_unpack_zip_file(self):

        source_file = os.path.join(
            self.temp_source_directory,
            os.path.basename(ZIP_FILE)
        )
        shutil.copy(ZIP_FILE, source_file)

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

        information = self._load_structure()
        assert information['symbols-unpack']
        assert not information['symbols-unpack']['last_error']
        assert information['symbols-unpack']['last_success']

        ok_(os.listdir(self.temp_destination_directory), 'empty')
        # there should now be a directory named `sample-<todays date>
        destination_dir = self.temp_destination_directory
        ok_(os.path.isdir(destination_dir))
        # and it should contain files
        ok_(os.listdir(destination_dir))
        # and the original should now have been deleted
        ok_(not os.path.isfile(source_file))

    def test_symbols_unpack_other_files(self):

        source_file = os.path.join(
            self.temp_source_directory,
            os.path.basename(TAR_FILE)
        )
        shutil.copy(TAR_FILE, source_file)

        source_file = os.path.join(
            self.temp_source_directory,
            os.path.basename(TGZ_FILE)
        )
        shutil.copy(TGZ_FILE, source_file)

        source_file = os.path.join(
            self.temp_source_directory,
            os.path.basename(TARGZ_FILE)
        )
        shutil.copy(TARGZ_FILE, source_file)

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

        information = self._load_structure()
        assert information['symbols-unpack']
        assert not information['symbols-unpack']['last_error']
        assert information['symbols-unpack']['last_success']

        ok_(os.listdir(self.temp_destination_directory), 'empty')

    def test_symbols_unpack_non_archive_file(self):

        source_file = os.path.join(
            self.temp_source_directory,
            os.path.basename(__file__)
        )
        shutil.copy(__file__, source_file)

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            config.logger.warning.assert_called_with(
                "Don't know how to unpack %s" % (
                    source_file,
                )
            )

        information = self._load_structure()
        assert information['symbols-unpack']
        assert not information['symbols-unpack']['last_error']
        assert information['symbols-unpack']['last_success']
