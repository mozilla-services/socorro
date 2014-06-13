# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.unittest.testbase import TestCase
from socorro.unittest.middleware.setup_configman import (
    get_config_manager_with_internal_pg
)

from configman import Namespace


#==============================================================================
class PostgreSQLTestCase(TestCase):
    """Base class for PostgreSQL related unit tests. """

    app_name = 'PostgreSQLTestCase'
    app_version = '1.0'
    app_description = __doc__
    metadata = ''

    required_config = Namespace()
    # this class will bring in all the appropriate connection stuff required
    # by postgres - including a transaction manager

    #--------------------------------------------------------------------------
    def get_standard_config(self, service_classes=None):
        required_config = Namespace()
        required_config.add_option(
            name='dropdb',
            default=False,
            doc='Whether or not to drop database_name',
            exclude_from_print_conf=True,
            exclude_from_dump_conf=True
        )

        local_overrides_of_defaults = {
            'resource.postgresql.database_name': 'socorro_integration_test',
        }
        config_manager = get_config_manager_with_internal_pg(
            more_definitions=[required_config],
            service_classes=service_classes,
            overrides=[local_overrides_of_defaults]
        )
        return config_manager.get_config()

    #--------------------------------------------------------------------------
    def setUp(self, service_class=None):
        """Create a configuration context and a database connection. """
        self.config = self.get_standard_config(service_class)

        self.database = self.config.database.database_class(
            self.config.database
        )
        self.transaction = self.config.database.transaction_executor_class(
            self.config.database,
            self.database,
        )
        self.connection = self.database.connection()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Close the database connection. """
        self.connection.close()
