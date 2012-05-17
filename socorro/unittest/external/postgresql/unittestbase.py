# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

import socorro.database.database as db
from socorro.lib import ConfigurationManager
from socorro.unittest.config import commonconfig


class PostgreSQLTestCase(unittest.TestCase):
    """Base class for PostgreSQL related unit tests. """

    def setUp(self):
        """Create a configuration context and a database connection. """
        self.config = ConfigurationManager.newConfiguration(
            configurationModule=commonconfig,
            applicationName="PostgreSQL Tests"
        )

        try:
            self.database = db.Database(self.config)
        except (AttributeError, KeyError):
            raise

        self.connection = self.database.connection()

    def tearDown(self):
        """Close the database connection. """
        self.connection.close()
