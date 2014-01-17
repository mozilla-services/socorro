# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr

from socorro.external.postgresql.crontabber_state import CrontabberState

from unittestbase import PostgreSQLTestCase


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
            INSERT INTO crontabber (
                app_name,
                next_run,
                first_run,
                last_run,
                last_success,
                error_count,
                depends_on,
                last_error
            ) VALUES (
                'slow-one',
                '2013-02-09 01:16:00.893834',
                '2012-11-05 23:27:07.316347',
                '2013-02-09 00:16:00.893834',
                '2012-12-24 22:27:07.316893',
                6,
                '{}',
                '{"traceback": "error error error",
                  "type": "<class ''sluggish.jobs.InternalError''>",
                  "value": "Have already run this for 2012-12-24 23:27"
                  }'
            ), (
                'slow-two',
                '2012-11-12 19:39:59.521605',
                '2012-11-05 23:27:17.341879',
                '2012-11-12 18:39:59.521605',
                '2012-11-12 18:27:17.341895',
                0,
                '{"slow-one"}',
                '{}'
            );
        """)
        self.connection.commit()

    def tearDown(self):
        """Clean up the database. """
        cursor = self.connection.cursor()
        cursor.execute("TRUNCATE crontabber")
        self.connection.commit()
        super(IntegrationTestCrontabberStatus, self).tearDown()

    def test_get(self):
        state = CrontabberState(config=self.config)
        res = state.get()

        slow_one = res['state']['slow-one']
        self.assertEqual(slow_one['next_run'], '2013-02-09T01:16:00+00:00')
        self.assertEqual(slow_one['first_run'], '2012-11-05T23:27:07+00:00')
        self.assertEqual(slow_one['last_run'], '2013-02-09T00:16:00+00:00')
        self.assertEqual(slow_one['last_success'], '2012-12-24T22:27:07+00:00')
        self.assertEqual(slow_one['error_count'], 6)
        self.assertEqual(slow_one['depends_on'], [])
        self.assertEqual(slow_one['last_error'], {
            'traceback': 'error error error',
            'type': "<class 'sluggish.jobs.InternalError'>",
            'value': 'Have already run this for 2012-12-24 23:27'
        })

        slow_two = res['state']['slow-two']
        self.assertEqual(slow_two['next_run'], '2012-11-12T19:39:59+00:00')
        self.assertEqual(slow_two['first_run'], '2012-11-05T23:27:17+00:00')
        self.assertEqual(slow_two['last_run'], '2012-11-12T18:39:59+00:00')
        self.assertEqual(slow_two['last_success'], '2012-11-12T18:27:17+00:00')
        self.assertEqual(slow_two['error_count'], 0)
        self.assertEqual(slow_two['depends_on'], ['slow-one'])
        self.assertEqual(slow_two['last_error'], {})
