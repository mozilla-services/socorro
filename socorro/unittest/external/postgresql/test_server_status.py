# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib

from nose.tools import eq_

from socorro.external.postgresql import server_status

from unittestbase import PostgreSQLTestCase


@contextlib.contextmanager
def mock_get_file():
    def mock_get_file(fn):
        vals = {
            'socorro_revision.txt': '42',
            'breakpad_revision.txt': '43'
        }
        return vals[fn]

    old_get_file = server_status.get_file
    server_status.get_file = mock_get_file
    yield
    server_status.get_file = old_get_file


class IntegrationTestServerStatus(PostgreSQLTestCase):
    """Test socorro.external.postgresql.server_status.ServerStatus class. """

    def setUp(self):
        """Set up this test class by populating the database with fake data.
        """
        super(IntegrationTestServerStatus, self).setUp()

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
        cursor = self.connection.cursor()
        cursor.execute("TRUNCATE alembic_version CASCADE;")
        self.connection.commit()
        super(IntegrationTestServerStatus, self).tearDown()

    def test_get(self):
        # NOTE(willkg): This mocks out the pkg_resources code that gets the
        # files, so this test doesn't test that aspect of server_status.
        with mock_get_file():
            status = server_status.ServerStatus(config=self.config)
            res = status.get()

        res_expected = {
            "socorro_revision": "42",
            "breakpad_revision": "43",
            "schema_revision": "aaaaaaaaaaaa",
        }

        eq_(res, res_expected)
