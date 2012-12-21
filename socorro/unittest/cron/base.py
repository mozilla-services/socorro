# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import shutil
import tempfile
import unittest
import mock
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE

from configman import ConfigurationManager
from socorro.cron import crontabber
from socorro.unittest.config.commonconfig import (
    databaseHost,
    databaseName,
    databaseUserName,
    databasePassword
)


DSN = {
    "database.database_host": databaseHost.default,
    "database.database_name": databaseName.default,
    "database.database_user": databaseUserName.default,
    "database.database_password": databasePassword.default
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
        #required_config.namespace('logging')
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
                'crontabber.jobs': jobs_string,
                'crontabber.database_file': json_file,
            }, DSN, extra_value_source]
        )
        return config_manager, json_file


class IntegrationTestCaseBase(TestCaseBase):
    """Useful class for running integration tests related to crontabber apps
    since this class takes care of setting up a psycopg connection and it
    makes sure the `crontabber_state` class is emptied.
    """

    def setUp(self):
        super(IntegrationTestCaseBase, self).setUp()
        assert 'test' in DSN['database.database_name']
        self.dsn = (
            'host=%(database.database_host)s '
            'dbname=%(database.database_name)s '
            'user=%(database.database_user)s '
            'password=%(database.database_password)s' % DSN
        )
        self.conn = psycopg2.connect(self.dsn)

        cursor = self.conn.cursor()
        cursor.execute('select count(*) from crontabber_state')
        if cursor.fetchone()[0] < 1:
            cursor.execute("""
            INSERT INTO crontabber_state (state, last_updated)
            VALUES ('{}', NOW());
            """)
        else:
            cursor.execute("""
            UPDATE crontabber_state SET state='{}';
            """)
        self.conn.commit()
        assert self.conn.get_transaction_status() == TRANSACTION_STATUS_IDLE

    def tearDown(self):
        super(IntegrationTestCaseBase, self).tearDown()
        self.conn.cursor().execute("""
            UPDATE crontabber_state SET state='{}';
        """)
        self.conn.commit()
