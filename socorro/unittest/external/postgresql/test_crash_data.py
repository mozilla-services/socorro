# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from nose.plugins.attrib import attr

from socorro.external import (
    MissingArgumentError,
    BadArgumentError,
    ResourceNotFound
)
from socorro.external.postgresql.crash_data import CrashData
from socorro.lib import datetimeutil

from unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestCrash(PostgreSQLTestCase):
    """Test socorro.external.postgresql.crash.Crash class. """

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the reports table with fake
        data. """
        super(IntegrationTestCrash, self).setUp()

        cursor = self.connection.cursor()

        # Insert data
        self.now = datetimeutil.utc_now()
        self.uuid = '4337c180-6c7b-4fe0-95e8-740732130926'
        self.raw_crash = {"Name": "Peter", "YOB": 1979}

        cursor.execute("""
            INSERT INTO raw_crashes
            (uuid, date_processed, raw_crash)
            VALUES (
            UUID(%s), '2013-09-27 13:14:15', %s);
        """, (self.uuid, json.dumps(self.raw_crash)))

        self.connection.commit()

    #--------------------------------------------------------------------------
    def test_get_failing(self):
        api = CrashData(config=self.config)
        self.assertRaises(BadArgumentError, api.get, uuid='1')
        self.assertRaises(MissingArgumentError, api.get)
        self.assertRaises(ResourceNotFound, api.get,
                          uuid='ab37c180-6c7b-4fe0-95e8-751843041037')

    def test_get_successful(self):
        api = CrashData(config=self.config)
        res = api.get(uuid=self.uuid)
        self.assertEqual(res, self.raw_crash)

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database, delete tables and functions. """
        cursor = self.connection.cursor()
        cursor.execute("""
            TRUNCATE raw_crashes
            CASCADE
        """)
        self.connection.commit()
        super(IntegrationTestCrash, self).tearDown()
