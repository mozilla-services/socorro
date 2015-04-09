# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import socorro.database.database as db
from configman import ConfigurationManager, Namespace
from configman.converters import list_converter
from socorro.unittest.testbase import TestCase


class PostgreSQLTestCase(TestCase):
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
        default='test',
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

    @classmethod
    def get_standard_config(cls):

        config_manager = ConfigurationManager(
            [cls.required_config,
             ],
            app_name='PostgreSQLTestCase',
            app_description=__doc__,
            argv_source=[]
        )

        with config_manager.context() as config:
            return config

    @classmethod
    def setUpClass(cls):
        """Create a configuration context and a database connection.

        This will create (and later destroy) one connection per test
        case (aka. test class).
        """
        cls.config = cls.get_standard_config()
        cls.database = db.Database(cls.config)
        cls.connection = cls.database.connection()

    @classmethod
    def tearDownClass(cls):
        """Close the database connection. """
        cls.connection.close()
