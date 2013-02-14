# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
from nose.plugins.attrib import attr

from socorro.external.postgresql.crontabber_state import CrontabberState
from socorro.lib import datetimeutil

from unittestbase import PostgreSQLTestCase

_SAMPLE_JSON = """
{
  "slow-one": {
    "next_run": "2013-02-09 01:16:00.893834",
    "first_run": "2012-11-05 23:27:07.316347",
    "last_error": {
      "traceback": "error error error",
      "type": "<class 'sluggish.jobs.InternalError'>",
      "value": "Have already run this for 2012-12-24 23:27"
    },
    "last_run": "2013-02-09 00:16:00.893834",
    "last_success": "2012-12-24 22:27:07.316893",
    "error_count": 6,
    "depends_on": []
  },
  "slow-two": {
    "next_run": "2012-11-12 19:39:59.521605",
    "first_run": "2012-11-05 23:27:17.341879",
    "last_error": {},
    "last_run": "2012-11-12 18:39:59.521605",
    "last_success": "2012-11-12 18:27:17.341895",
    "error_count": 0,
    "depends_on": ["slow-one"]
  }
}
""".strip()
json.loads(_SAMPLE_JSON)  # assert that that would work


@attr(integration='postgres')  # for nosetests
class IntegrationTestCrontabberStatus(PostgreSQLTestCase):
    """Test socorro.external.postgresql.crontabbers_state.CrontabberState
    class """

    def setUp(self):
        """Set up this test class by populating the database with fake data.
        """
        super(IntegrationTestCrontabberStatus, self).setUp()

        cursor = self.connection.cursor()
        cursor.execute("""
            UPDATE crontabber_state
            SET state = %s
        """, (_SAMPLE_JSON,))
        self.connection.commit()

    def tearDown(self):
        """Clean up the database. """
        cursor = self.connection.cursor()
        cursor.execute("UPDATE crontabber_state SET state = '{}';")
        self.connection.commit()
        super(IntegrationTestCrontabberStatus, self).tearDown()

    def test_get(self):
        state = CrontabberState(config=self.config)
        res = state.get()
        self.assertEqual(res['state'], _SAMPLE_JSON)
        self.assertTrue(isinstance(res['last_updated'], basestring))
        # it should be a parsable datetime
        datetimeutil.datetimeFromISOdateString(res['last_updated'])
