import os
import shutil
import tempfile
import unittest
import mock

from configman import ConfigurationManager
from socorro.cron import crontabber
from socorro.unittest.config.commonconfig import (
  databaseHost, databaseName, databaseUserName, databasePassword)


DSN = {
  "database_host": databaseHost.default,
  "database_name": databaseName.default,
  "database_user": databaseUserName.default,
  "database_password": databasePassword.default
}


class TestCaseBase(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.tempdir):
            shutil.rmtree(self.tempdir)

    def _setup_config_manager(self, jobs_string, extra_value_source=None):
        if not extra_value_source:
            extra_value_source = {}
        mock_logging = mock.Mock()
        required_config = crontabber.CronTabber.required_config
        required_config.add_option('logger', default=mock_logging)

        json_file = os.path.join(self.tempdir, 'test.json')
        assert not os.path.isfile(json_file)

        config_manager = ConfigurationManager(
            [required_config,
             #logging_required_config(app_name)
             ],
            app_name='crontabber',
            app_description=__doc__,
            values_source_list=[{
                'logger': mock_logging,
                'jobs': jobs_string,
                'database': json_file,
            }, DSN, extra_value_source]
        )
        return config_manager, json_file
