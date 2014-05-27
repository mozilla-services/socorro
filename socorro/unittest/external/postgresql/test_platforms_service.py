# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr
from nose.tools import eq_

from socorro.external.postgresql.platforms_service import Platforms
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
)

from .unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestPlatforms(PostgreSQLTestCase):
    """Test socorro.external.postgresql.platforms_service.Platforms class.
    """

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the os_names table with fake
        data. """
        super(IntegrationTestPlatforms, self).setUp(Platforms)

        self.transaction(
            execute_no_results,
            """
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
        """
        )

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        self.transaction(
            execute_no_results,
            "TRUNCATE os_names CASCADE"
        )
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

        eq_(res, res_expected)
