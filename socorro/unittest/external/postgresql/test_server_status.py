# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import socorro
from nose.tools import eq_

from socorro.external.postgresql import server_status

from unittestbase import PostgreSQLTestCase


class IntegrationTestServerStatus(PostgreSQLTestCase):
    """Test socorro.external.postgresql.server_status.ServerStatus class. """

    def setUp(self):
        """Set up this test class by populating the database with fake data.
        """
        super(IntegrationTestServerStatus, self).setUp()

        # Create fake revision files
        self.basedir = os.path.dirname(socorro.__file__)
        open(os.path.join(
            self.basedir, 'socorro_revision.txt'
        ), 'w').write('42')
        open(os.path.join(
            self.basedir, 'breakpad_revision.txt'
        ), 'w').write('43')

        cursor = self.connection.cursor()

        # Prepare data for the schema revision
        # Clean up from init routine
        cursor.execute("TRUNCATE alembic_version CASCADE;")

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
        # Delete fake revision files
        os.remove(os.path.join(self.basedir, 'socorro_revision.txt'))
        os.remove(os.path.join(self.basedir, 'breakpad_revision.txt'))

        cursor = self.connection.cursor()
        cursor.execute("TRUNCATE server_status, alembic_version CASCADE;")
        self.connection.commit()
        super(IntegrationTestServerStatus, self).tearDown()

    def test_get(self):
        status = server_status.ServerStatus(config=self.config)

        res = status.get()
        res_expected = {
            "socorro_revision": "42",
            "breakpad_revision": "43",
            "schema_revision": "aaaaaaaaaaaa",
        }

        eq_(res, res_expected)
