# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr

from socorro.external.postgresql.platforms import Platforms

from .unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestPlatforms(PostgreSQLTestCase):
    """Test socorro.external.postgresql.platforms.Platforms class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the os_names table with fake
        data. """
        super(IntegrationTestPlatforms, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        cursor.execute("""
            INSERT INTO os_names
            (os_name, os_short_name)
            VALUES
            (
                'Windows NT',
                'win'
            ),
            (
                'Mac OS X',
                'mac'
            ),
            (
                'Linux',
                'lin'
            );
        """)

        self.connection.commit()

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE os_names CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestPlatforms, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        platforms = Platforms(config=self.config)

        res = platforms.get()
        res_expected = {
            "hits": [
                {
                    "name": "Windows NT",
                    "code": "win"
                },
                {
                    "name": "Mac OS X",
                    "code": "mac"
                },
                {
                    "name": "Linux",
                    "code": "lin"
                }
            ],
            "total": 3
        }

        self.assertEqual(res, res_expected)
