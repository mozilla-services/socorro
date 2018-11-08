# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman.dotdict import DotDict
import pytest

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.connection_context import ConnectionContext
from socorro.lib import DatabaseError
from socorro.unittest.testbase import TestCase
from socorro.unittest.external.postgresql.unittestbase import PostgreSQLTestCase


class TestPostgreSQLBase(TestCase):
    """Test PostgreSQLBase class. """

    def get_dummy_context(self):
        """Create a dummy config object to use when testing."""
        context = DotDict({
            'database_class': ConnectionContext,
            'database_hostname': 'somewhere',
            'database_port': '8888',
            'database_name': 'somename',
            'database_username': 'someuser',
            'database_password': 'somepasswd',
        })
        context.platforms = (
            {
                "id": "windows",
                "name": "Windows NT"
            },
            {
                "id": "linux",
                "name": "Linux"
            }
        )
        context.non_release_channels = ['beta', 'aurora', 'nightly']
        context.restricted_channels = ['beta']
        return context

    def get_instance(self, config=None):
        """Return an instance of PostgreSQLBase with the config parameter as
        a context or the default one if config is None.
        """
        args = {
            "config": config or self.get_dummy_context()
        }
        return PostgreSQLBase(**args)


class IntegrationTestBase(PostgreSQLTestCase):

    def setUp(self):
        super(IntegrationTestBase, self).setUp()

        # Populate the release_channels table with fake data
        cursor = self.connection.cursor()
        # Truncate first in case there's data in there--there shouldn't be
        cursor.execute("""
            TRUNCATE release_channels CASCADE;
        """)
        self.connection.commit()
        cursor.execute("""
            INSERT INTO release_channels
            (release_channel, sort)
            VALUES
            ('Nightly', 1),
            ('Aurora', 2),
            ('Beta', 3),
            ('Release', 4),
            ('ESR', 5)
        """)

        self.connection.commit()

    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE release_channels CASCADE;
        """)
        self.connection.commit()
        super(IntegrationTestBase, self).tearDown()

    def test_utc(self):
        base = PostgreSQLBase(config=self.config)

        # Verify that we've got 'timezone=utc' set
        sql = 'SHOW TIMEZONE'
        results = base.query(sql)
        assert 'UTC' in results[0], (
            'Please set PostgreSQL to use the UTC timezone. Documentation on how to do this is '
            'included in the installation instructions.'
        )

    def test_query(self):
        base = PostgreSQLBase(config=self.config)

        # A working query
        sql = 'SELECT * FROM release_channels ORDER BY sort'
        results = base.query(sql)
        assert len(results) == 5
        assert results[0] == ('Nightly', 1)
        assert results[1] == ('Aurora', 2)

        # A working query with parameters
        sql = 'SELECT * FROM release_channels WHERE release_channel=%(release_channel)s'
        params = {'release_channel': 'Nightly'}
        results = base.query(sql, params)
        assert len(results) == 1
        assert results[0] == ('Nightly', 1)

        # A failing query
        sql = 'SELECT FROM release_channels LIMIT notanumber'
        with pytest.raises(DatabaseError):
            base.query(sql)

    def test_count(self):
        base = PostgreSQLBase(config=self.config)

        # A working count
        sql = 'SELECT count(*) FROM release_channels'
        count = base.count(sql)
        assert count == 5

        # A working count with parameters
        sql = 'SELECT count(*) FROM release_channels WHERE release_channel=%(release_channel)s'
        params = {'release_channel': 'Nightly'}
        count = base.count(sql, params)
        assert count == 1

        # A failing count
        sql = 'SELECT count(`invalid_field_name`) FROM release_channels'
        with pytest.raises(DatabaseError):
            base.count(sql)
