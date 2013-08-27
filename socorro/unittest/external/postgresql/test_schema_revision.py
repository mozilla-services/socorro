# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.plugins.attrib import attr

from socorro.external.postgresql.schema_revision import SchemaRevision
from socorro.lib import datetimeutil, util

from unittestbase import PostgreSQLTestCase


@attr(integration='postgres')  # for nosetests
class IntegrationTestSchemaRevision(PostgreSQLTestCase):
    """Test socorro.external.postgresql.server_status.SchemaRevision class. """

    def setUp(self):
        """Set up this test class by populating the database with fake data.
        """
        super(IntegrationTestSchemaRevision, self).setUp()

        cursor = self.connection.cursor()

        # Clean up from init routine
        cursor.execute("TRUNCATE alembic_version CASCADE;")

        # Insert data
        cursor.execute("""
            INSERT INTO alembic_version
            (version_num)
            VALUES
            (
                'aaaaaaaaaaaa'
            )
        """)

        self.connection.commit()

    def tearDown(self):
        """Clean up the database. """
        cursor = self.connection.cursor()
        cursor.execute("TRUNCATE alembic_version CASCADE;")
        self.connection.commit()
        super(IntegrationTestSchemaRevision, self).tearDown()

    def test_get(self):
        status = SchemaRevision(config=self.config)

        #......................................................................
        # Test 1: return a schema revision ID
        res = status.get()
        res_expected = {
            "schema_revision": 'aaaaaaaaaaaa'
        }

        self.assertEqual(res, res_expected)
