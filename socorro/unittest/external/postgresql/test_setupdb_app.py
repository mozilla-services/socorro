# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
from cStringIO import StringIO
import unittest
import mock
from psycopg2 import ProgrammingError
from socorro.external.postgresql import setupdb_app
from socorro.unittest.config.commonconfig import databaseName
from configman import ConfigurationManager

DSN = {
  "database_name": databaseName.default,
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

    def test_setupdb_app_main(self):
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

        with config_manager.context() as config:
            with mock.patch(self.psycopg2_module_path) as psycopg2:
                app = setupdb_app.SocorroDB(config)
                # TODO test that citext.sql gets loaded with 9.0.x
                # TODO test that non 9.[01].x errors out
                psycopg2.connect().cursor().execute.side_effect = mocked_execute
                psycopg2.connect().cursor().fetchall.side_effect = mocked_fetchall
                result = app.main()
                self.assertEqual(result, 0)

                psycopg2.connect.assert_called_with('dbname=foo host=heaven')
                (psycopg2.connect().cursor().execute
                 .assert_any_call('SELECT weekly_report_partitions()'))
                (psycopg2.connect().cursor().execute
                 .assert_any_call('CREATE DATABASE foo'))

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
