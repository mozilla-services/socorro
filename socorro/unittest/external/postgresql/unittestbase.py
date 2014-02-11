# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

import socorro.database.database as db

import mock
from configman import ConfigurationManager, Namespace
from configman.converters import list_converter


class PostgreSQLTestCase(unittest.TestCase):
    """Base class for PostgreSQL related unit tests. """

    app_name = 'PostgreSQLTestCase'
    app_version = '1.0'
    app_description = __doc__
    metadata = ''

    required_config = Namespace()
    required_config.namespace('database')
    required_config.add_option(
        name='database_name',
        default='socorro_integration_test',
        doc='Name of database to manage',
    )

    required_config.add_option(
        name='database_hostname',
        default='localhost',
        doc='Hostname to connect to database',
    )

    required_config.add_option(
        name='database_username',
        default='breakpad_rw',
        doc='Username to connect to database',
    )

    required_config.add_option(
        name='database_password',
        default='aPassword',
        doc='Password to connect to database',
    )

    required_config.add_option(
        name='database_superusername',
        default='test',
        doc='Username to connect to database',
    )

    required_config.add_option(
        name='database_superuserpassword',
        default='aPassword',
        doc='Password to connect to database',
    )

    required_config.add_option(
        name='database_port',
        default='',
        doc='Port to connect to database',
    )

    required_config.add_option(
        name='dropdb',
        default=False,
        doc='Whether or not to drop database_name',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
    )

    required_config.add_option(
        'platforms',
        default=[{
            "id": "windows",
            "name": "Windows NT"
        }, {
            "id": "mac",
            "name": "Mac OS X"
        }, {
            "id": "linux",
            "name": "Linux"
        }],
        doc='Array associating OS ids to full names.',
    )

    required_config.add_option(
        'non_release_channels',
        default=['beta', 'aurora', 'nightly'],
        doc='List of channels, excluding the `release` one.',
        from_string_converter=list_converter
    )

    required_config.add_option(
        'restricted_channels',
        default=['beta'],
        doc='List of channels to restrict based on build ids.',
        from_string_converter=list_converter
    )

    required_config.add_option(
        name='unlogged',
        default=False,
        doc='Create all tables with UNLOGGED for running tests',
    )

    def get_standard_config(self, extra_value_source=None):
        if not extra_value_source:
            extra_value_source = {}
        self.mock_logging = mock.Mock()

        assert 'unlogged' in self.required_config
        required_config = self.required_config
        required_config.add_option('logger', self.mock_logging)

        config_manager = ConfigurationManager(
            [required_config],
            app_name='PostgreSQLTestCase',
            app_description=__doc__,
            argv_source=[]
        )

        with config_manager.context() as config:
            return config

    def setUp(self):
        """Create a configuration context and a database connection. """
        self.config = self.get_standard_config()
        print "SELF.CONFIG"
        print self.config.keys()
        self.database = db.Database(self.config, logger=self.config.logger)
        self.connection = self.database.connection()

    def tearDown(self):
        """Close the database connection. """
        self.connection.close()
