# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
import os
import shutil
import tempfile
import unittest
from collections import Sequence, Mapping, defaultdict

import mock
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from nose.plugins.attrib import attr

from configman import ConfigurationManager
from socorro.cron import crontabber
from socorro.unittest.config.commonconfig import (
    databaseHost,
    databaseName,
    databaseUserName,
    databasePassword
)


DSN = {
    "database.database_hostname": databaseHost.default,
    "database.database_name": databaseName.default,
    "database.database_username": databaseUserName.default,
    "database.database_password": databasePassword.default
}


class TestCaseBase(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.tempdir):
            shutil.rmtree(self.tempdir)

    def _setup_config_manager(self, jobs_string, extra_value_source=None):
        """setup and return a ConfigurationManager and a the crontabber
        json file.
            jobs_string - a formatted string list services to be offered
            config - a string representing a config file OR a mapping of
                     key/value pairs to be used to override config defaults or
                     a list of any of the previous
            extra_value_source - supplemental values required by a service

        """
        mock_logging = mock.Mock()
        required_config = crontabber.CronTabber.required_config
        #required_config.namespace('logging')
        required_config.add_option('logger', default=mock_logging)

        json_file = os.path.join(self.tempdir, 'test.json')

        value_source = [
            {
                'logger': mock_logging,
                'crontabber.jobs': jobs_string,
                'crontabber.database_file': json_file,
                'admin.strict': True,
            },
            DSN,
            extra_value_source,
        ]

        if extra_value_source is None:
            pass
        elif isinstance(extra_value_source, basestring):
            value_source.append(extra_value_source)
        elif isinstance(extra_value_source, Sequence):
            value_source.extend(extra_value_source)
        elif isinstance(extra_value_source, Mapping):
            value_source.append(extra_value_source)

        config_manager = ConfigurationManager(
            [required_config,
             #logging_required_config(app_name)
             ],
            values_source_list=value_source,
            app_name='crontabber',
            app_description=__doc__,
            argv_source=[]
        )
        return config_manager

    def _wind_clock(self, state, days=0, hours=0, seconds=0):
        # note that 'hours' and 'seconds' can be negative numbers
        if days:
            hours += days * 24
        if hours:
            seconds += hours * 60 * 60

        ## modify ALL last_run and next_run to pretend time has changed
        #db = crontabber.JSONJobDatabase()
        #db.load(json_file)

        def _wind(data):
            for key, value in data.items():
                if isinstance(value, dict):
                    _wind(value)
                else:
                    if isinstance(value, datetime.datetime):
                        data[key] = value - datetime.timedelta(seconds=seconds)

        _wind(state)
        return state


@attr(integration='postgres')
class IntegrationTestCaseBase(TestCaseBase):
    """Useful class for running integration tests related to crontabber apps
    since this class takes care of setting up a psycopg connection and it
    makes sure the `crontabber_state` class is emptied.
    """

    def setUp(self):
        super(IntegrationTestCaseBase, self).setUp()
        assert 'test' in DSN['database.database_name']
        self.dsn = (
            'host=%(database.database_hostname)s '
            'dbname=%(database.database_name)s '
            'user=%(database.database_username)s '
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
        # make absolutely sure we're starting with these clean
        self.conn.cursor().execute("""
            TRUNCATE crontabber, crontabber_log CASCADE;
        """)
        self.conn.commit()
        assert self.conn.get_transaction_status() == TRANSACTION_STATUS_IDLE

    def tearDown(self):
        super(IntegrationTestCaseBase, self).tearDown()
        self.conn.cursor().execute("""
            UPDATE crontabber_state SET state='{}';
            TRUNCATE crontabber, crontabber_log CASCADE;
        """)
        self.conn.commit()
        self.conn.close()

    def assertAlmostEqual(self, val1, val2):
        if (
            isinstance(val1, datetime.datetime) and
            isinstance(val2, datetime.datetime)
        ):
            # if there difference is just in the microseconds, they're
            # sufficiently equal
            return not abs(val1 - val2).seconds
        self.assertEqual(val1, val2)

    def _load_structure(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                app_name,
                next_run,
                first_run,
                last_run,
                last_success,
                error_count,
                depends_on,
                last_error
            FROM crontabber;
        """)
        columns = (
            'app_name', 'next_run', 'first_run', 'last_run', 'last_success',
            'error_count', 'depends_on', 'last_error'
        )
        structure = {}
        for record in cursor.fetchall():
            row = dict(zip(columns, record))
            row['last_error'] = json.loads(row.pop('last_error'))
            structure[row.pop('app_name')] = row
        return structure

    def _load_logs(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                app_name,
                log_time,
                duration,
                success,
                exc_type,
                exc_value,
                exc_traceback
            FROM crontabber_log
            ORDER BY log_time;
        """)
        columns = (
            'app_name', 'log_time', 'duration', 'success',
            'exc_type', 'exc_value', 'exc_traceback'
        )
        logs = defaultdict(list)
        for record in cursor.fetchall():
            row = dict(zip(columns, record))
            logs[row.pop('app_name')].append(row)
        return logs
