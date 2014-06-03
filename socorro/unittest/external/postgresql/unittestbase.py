# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import socorro.lib.util
from configman import ConfigurationManager, Namespace, environment
from configman.converters import list_converter, class_converter
from socorro.unittest.testbase import TestCase


class PostgreSQLTestCase(TestCase):
    """Base class for PostgreSQL related unit tests. """

    app_name = 'PostgreSQLTestCase'
    app_version = '1.0'
    app_description = __doc__
    metadata = ''

    required_config = Namespace()
    required_config.namespace('database')
    # this class will bring in all the appropriate connection stuff required
    # by postgres - including a transaction manager
    required_config.database.add_option(
        'crashstorage_class',
        default=
        'socorro.external.postgresql.crashstorage.PostgreSQLCrashStorage',
        doc='the class responsible for connecting to Postgres',
        reference_value_from='resource.postgresql',
        from_string_converter=class_converter
    )

    required_config.database.add_option(
        name='database_superusername',
        default='test',
        doc='Username to connect to database',
    )

    required_config.database.add_option(
        name='database_superuserpassword',
        default='aPassword',
        doc='Password to connect to database',
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
        'logger',
        default=socorro.lib.util.SilentFakeLogger(),
        doc='a logger',
    )

    def get_standard_config(self):
        # MOCKED CONFIG DONE HERE
        local_overrides_of_defaults = {
            'database.database_name': 'socorro_integration_test',
        }

        config_manager = ConfigurationManager(
            [self.required_config,
             ],
            values_source_list=[local_overrides_of_defaults, environment],
            app_name='PostgreSQLTestCase',
            app_description=__doc__,
            argv_source=[]
        )
        return config_manager.get_config()

    def setUp(self):
        """Create a configuration context and a database connection. """
        self.config = self.get_standard_config()

        self.database = self.config.database.database_class(
            self.config.database
        )

        self.connection = self.database.connection()

    def tearDown(self):
        """Close the database connection. """
        self.connection.close()
