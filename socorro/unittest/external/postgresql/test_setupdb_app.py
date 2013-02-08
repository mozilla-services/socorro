# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
from cStringIO import StringIO
import unittest
import mock
from psycopg2 import ProgrammingError
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE

from nose.plugins.attrib import attr
from socorro.external.postgresql import setupdb_app
from socorro.unittest.config.commonconfig import (
    databaseName,
    databaseHost,
    databaseUserName,
    databasePassword
)
from configman import ConfigurationManager

DSN = {
    "database_hostname": databaseHost.default,
    "database_name": databaseName.default,
    "database_username": databaseUserName.default,
    "database_password": databasePassword.default
}

class TestSetupDB(unittest.TestCase):

    psycopg2_module_path = 'socorro.external.postgresql.setupdb_app.psycopg2'

    def test_execute_postgres(self):
        config_manager = self._setup_config_manager()
        klass = setupdb_app.PostgreSQLManager

        with config_manager.context() as config:
            with mock.patch(self.psycopg2_module_path) as psycopg2:
                with klass('dbname=postgres', config.logger) as db:
                    db.execute('CREATE DATABASE blah')

                (psycopg2.connect().cursor()
                 .execute.assert_called_with('CREATE DATABASE blah'))

    def test_execute_postgres_with_acceptable_errors(self):
        config_manager = self._setup_config_manager()
        klass = setupdb_app.PostgreSQLManager

        with config_manager.context() as config:
            with mock.patch(self.psycopg2_module_path) as psycopg2:
                pge = ProgrammingError()
                pge.pgerror = "ERROR:  bad things happened"
                psycopg2.connect().cursor().execute.side_effect = pge

                # no allowable errors
                with klass('postgres', config.logger) as db:
                    self.assertRaises(ProgrammingError, db.execute,
                                      'CREATE DATABASE blah')
                # harmless error
                with klass('postgres', config.logger) as db:
                    db.execute('CREATE DATABASE blah', ['bad things'])

                config.logger.warning.assert_called_with('bad things happened')

                (psycopg2.connect().cursor()
                 .execute.assert_called_with('CREATE DATABASE blah'))

                # harmless but not expected
                with klass('postgres', config.logger) as db:
                    self.assertRaises(ProgrammingError, db.execute,
                                      'CREATE DATABASE blah', ['other things'])

                # unrecognized ProgrammingError
                pge = ProgrammingError()
                pge.pgerror = "ERROR:  good things"
                psycopg2.connect().cursor().execute.side_effect = pge
                with klass('postgres', config.logger) as db:
                    self.assertRaises(ProgrammingError, db.execute,
                                      'CREATE DATABASE blah', ['bad things'])

                # something really f'ed up
                err = ValueError('flying pigs!')
                psycopg2.connect().cursor().execute.side_effect = err
                with klass('postgres', config.logger) as db:
                    self.assertRaises(ValueError, db.execute,
                                      'CREATE DATABASE blah', ['bad things'])

                # that self.conn.close() was called with no arguments:
                psycopg2.connect().close.assert_called_with()

    @mock.patch('socorro.external.postgresql.setupdb_app.create_engine')
    @mock.patch('socorro.external.postgresql.setupdb_app.sessionmaker')
    def test_setupdb_app_main(self, create_engine_mock, sessionmaker_mock):
        config_manager = self._setup_config_manager({
          'database_name': 'foo',
          'database_hostname': 'heaven',
        })

        def mocked_fetchall():
            return _return_rows

        # we use a mutable to keep track of what the latest that was sent
        # to cursor.execute() so we can update it within the scope
        _return_rows = []

        def mocked_execute(sql):
            if sql == 'SELECT version()':
                _return_rows.insert(0, ('PostgreSQL 9.2.1 blah blah blah',))
            elif sql == 'SHOW TIMEZONE':
                _return_rows.insert(0, ('UTC',))

        conn_mocked = mock.MagicMock()
        print "*conn_mocked*", repr(conn_mocked)
        create_engine_mock().connect.side_effect = conn_mocked

        with config_manager.context() as config:
            with mock.patch(self.psycopg2_module_path) as psycopg2:
                app = setupdb_app.SocorroDB(config)
                # TODO test that citext.sql gets loaded with 9.0.x
                # TODO test that non 9.[01].x errors out
                psycopg2.connect().cursor().execute.side_effect = mocked_execute
                psycopg2.connect().cursor().fetchall.side_effect = mocked_fetchall
                result = app.main()
                self.assertEqual(result, 0)

                # we're interested to see that the 'CREATE DATABASE' command is called

                print conn_mocked.mock_calls
                #print create_engine_mock.mock_calls
                print
                #psycopg2.connect.assert_called_with('dbname=foo host=heaven')
                #(psycopg2.connect().cursor().execute
                # .assert_any_call('SELECT weekly_report_partitions()'))
                #(psycopg2.connect().cursor().execute
                # .assert_any_call('CREATE DATABASE foo'))

    def test_setupdb_app_main_pg_90(self):
        config_manager = self._setup_config_manager({
          'database_name': 'foo',
          'database_hostname': 'heaven',
        })

        def mocked_fetchall():
            return _return_rows

        # we use a mutable to keep track of what the latest that was sent
        # to cursor.execute() so we can update it within the scope
        _return_rows = []

        def mocked_execute(sql):
            if sql == 'SELECT version()':
                _return_rows.insert(0, ('PostgreSQL 9.0.1 blah blah blah',))
            elif sql == 'SHOW TIMEZONE':
                _return_rows.insert(0, ('UTC',))

        with config_manager.context() as config:
            with mock.patch(self.psycopg2_module_path) as psycopg2:
                app = setupdb_app.SocorroDB(config)
                # TODO test that citext.sql gets loaded with 9.0.x
                psycopg2.connect().cursor().execute.side_effect = mocked_execute
                psycopg2.connect().cursor().fetchall.side_effect = mocked_fetchall
                stderr = StringIO()
                old_stderr = sys.stderr
                sys.stderr = stderr
                try:
                    result = app.main()
                    self.assertEqual(result, 2)
                    error_output = stderr.getvalue()
                    self.assertTrue('ERROR' in error_output)
                    self.assertTrue('9.0.1' in error_output)
                finally:
                    sys.stderr = old_stderr

    def test_setupdb_app_main_not_utc_timezone(self):
        config_manager = self._setup_config_manager({
          'database_name': 'foo',
          'database_hostname': 'heaven',
        })

        def mocked_fetchall():
            return _return_rows

        # we use a mutable to keep track of what the latest that was sent
        # to cursor.execute() so we can update it within the scope
        _return_rows = []

        def mocked_execute(sql):
            if sql == 'SELECT version()':
                _return_rows.insert(0, ('PostgreSQL 9.2.1 blah blah blah',))
            elif sql == 'SHOW TIMEZONE':
                _return_rows.insert(0, ('CET',))

        with config_manager.context() as config:
            with mock.patch(self.psycopg2_module_path) as psycopg2:
                app = setupdb_app.SocorroDB(config)
                # TODO test that citext.sql gets loaded with 9.0.x
                # TODO test that non 9.[01].x errors out
                psycopg2.connect().cursor().execute.side_effect = mocked_execute
                psycopg2.connect().cursor().fetchall.side_effect = mocked_fetchall
                stderr = StringIO()
                old_stderr = sys.stderr
                sys.stderr = stderr
                try:
                    result = app.main()
                    self.assertEqual(result, 3)
                    error_output = stderr.getvalue()
                    self.assertTrue('ERROR' in error_output)
                    self.assertTrue('CET' in error_output)
                finally:
                    sys.stderr = old_stderr

    def _setup_config_manager(self, extra_value_source=None):
        if not extra_value_source:
            extra_value_source = {}
        mock_logging = mock.Mock()
        required_config = setupdb_app.SocorroDB.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
            [required_config,
             ],
            app_name='setupdb',
            app_description=__doc__,
            values_source_list=[{
                'logger': mock_logging,
                'database_name': 'blah',
            }, DSN, extra_value_source]
        )
        return config_manager



@attr(integration='postgres')  # for nosetests
class IntegrationTestSetupDB(unittest.TestCase):

    def setUp(self):
        super(IntegrationTestSetupDB, self).setUp()
        # prep a fake table
        assert 'test' in DSN['database_name']
        dsn = ('host=%(database_hostname)s '
               'dbname=%(database_name)s '
               'user=%(database_username)s '
               'password=%(database_password)s' % dict(DSN, database_name='template1'))
        self.conn = psycopg2.connect(dsn)
        cursor = self.conn.cursor()
        # double-check there is a crontabber_state row
        self.conn.set_isolation_level(0)
        try:
            cursor.execute('DROP DATABASE %s' % DSN['database_name'])
        except ProgrammingError, msg:
            print repr(str(msg))
        self.conn.set_isolation_level(1)
        assert self.conn.get_transaction_status() == TRANSACTION_STATUS_IDLE
        self.conn.close()

    def tearDown(self):
        super(IntegrationTestSetupDB, self).tearDown()
        #self.conn.cursor().execute('DROP DATABASE %s', DSN['database_name'])
        #self.conn.commit()

    def _setup_config_manager(self, extra_value_source=None):
        if not extra_value_source:
            extra_value_source = {}
        mock_logging = mock.Mock()
        required_config = setupdb_app.SocorroDB.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
            [required_config,
             ],
            app_name='setupdb',
            app_description=__doc__,
            values_source_list=[{
                'logger': mock_logging,
            }, DSN, extra_value_source]
        )
        return config_manager

    def test_run_setupdb_app(self):
        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            db = setupdb_app.SocorroDB(config)
            db.main()
            print config
