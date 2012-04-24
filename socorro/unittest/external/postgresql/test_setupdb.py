import unittest
import mock
from psycopg2 import ProgrammingError
from socorro.external.postgresql import setupdb_app
from socorro.unittest.config.commonconfig import (
  databaseHost, databaseName, databaseUserName, databasePassword)
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
                with klass('postgres', config.logger) as db:
                    db.execute('CREATE DATABASE blah')

                psycopg2.connect.assert_called_with(database='postgres')
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

    def _setup_config_manager(self, extra_value_source=None):
        if not extra_value_source:
            extra_value_source = {}
        mock_logging = mock.Mock()
        required_config = setupdb_app.SocorroDB.required_config
        required_config.add_option('logger', default=mock_logging)

        config_manager = ConfigurationManager(
            [required_config,
             #logging_required_config(app_name)
             ],
            app_name='setupdb',
            app_description=__doc__,
            values_source_list=[{
                'logger': mock_logging,
                'database_name': 'blah',
            }, DSN, extra_value_source]
        )
        return config_manager
