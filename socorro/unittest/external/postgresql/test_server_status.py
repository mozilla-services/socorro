# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.plugins.attrib import attr

from socorro.external.postgresql.server_status import ServerStatus
from socorro.lib import datetimeutil

from unittestbase import PostgreSQLTestCase


@attr(integration='postgres')  # for nosetests
class IntegrationTestServerStatus(PostgreSQLTestCase):
    """Test socorro.external.postgresql.server_status.ServerStatus class. """

    def setUp(self):
        """Set up this test class by populating the database with fake data.
        """
        super(IntegrationTestServerStatus, self).setUp()

        # Extend config with revisions
        self.config.socorro_revision = 42
        self.config.breakpad_revision = 43

        cursor = self.connection.cursor()

        # Insert data
        now = datetimeutil.utc_now()
        date1 = datetime.datetime(now.year, now.month, now.day, 12, 00, 00,
                                  tzinfo=now.tzinfo)
        date2 = date1 - datetime.timedelta(minutes=15)
        date3 = date2 - datetime.timedelta(minutes=15)
        date4 = date3 - datetime.timedelta(minutes=15)

        cursor.execute("""
            INSERT INTO server_status
            (id, date_recently_completed, date_oldest_job_queued,
             avg_process_sec, avg_wait_sec, waiting_job_count,
             processors_count, date_created)
            VALUES
            (
                1,
                '%(date1)s',
                '%(date1)s',
                2,
                5,
                3,
                2,
                '%(date1)s'
            ),
            (
                2,
                '%(date2)s',
                '%(date2)s',
                3,
                3.12,
                2,
                2,
                '%(date2)s'
            ),
            (
                3,
                '%(date3)s',
                '%(date3)s',
                1,
                2,
                4,
                1,
                '%(date3)s'
            ),
            (
                4,
                NULL,
                NULL,
                1,
                2,
                4,
                1,
                '%(date4)s'
            );
        """ % {"date1": date1, "date2": date2, "date3": date3, "date4": date4})

        self.connection.commit()

    def tearDown(self):
        """Clean up the database. """
        cursor = self.connection.cursor()
        cursor.execute("TRUNCATE server_status CASCADE;")
        self.connection.commit()
        super(IntegrationTestServerStatus, self).tearDown()

    def test_get(self):
        status = ServerStatus(config=self.config)
        now = datetimeutil.utc_now()

        date1 = datetime.datetime(now.year, now.month, now.day, 12, 00, 00,
                                  tzinfo=now.tzinfo)
        date2 = date1 - datetime.timedelta(minutes=15)
        date3 = date2 - datetime.timedelta(minutes=15)
        date4 = date3 - datetime.timedelta(minutes=15)

        date1 = datetimeutil.date_to_string(date1)
        date2 = datetimeutil.date_to_string(date2)
        date3 = datetimeutil.date_to_string(date3)
        date4 = datetimeutil.date_to_string(date4)

        #......................................................................
        # Test 1: default behavior
        res = status.get()
        res_expected = {
            "hits": [
                {
                    "id": 1,
                    "date_recently_completed": date1,
                    "date_oldest_job_queued": date1,
                    "avg_process_sec": 2,
                    "avg_wait_sec": 5,
                    "waiting_job_count": 3,
                    "processors_count": 2,
                    "date_created": date1
                },
                {
                    "id": 2,
                    "date_recently_completed": date2,
                    "date_oldest_job_queued": date2,
                    "avg_process_sec": 3,
                    "avg_wait_sec": 3.12,
                    "waiting_job_count": 2,
                    "processors_count": 2,
                    "date_created": date2
                },
                {
                    "id": 3,
                    "date_recently_completed": date3,
                    "date_oldest_job_queued": date3,
                    "avg_process_sec": 1,
                    "avg_wait_sec": 2,
                    "waiting_job_count": 4,
                    "processors_count": 1,
                    "date_created": date3
                },
                {
                    "id": 4,
                    "date_recently_completed": None,
                    "date_oldest_job_queued": None,
                    "avg_process_sec": 1,
                    "avg_wait_sec": 2,
                    "waiting_job_count": 4,
                    "processors_count": 1,
                    "date_created": date4
                }
            ],
            "socorro_revision": 42,
            "breakpad_revision": 43,
            "total": 4
        }

        self.assertEqual(res, res_expected)

        #......................................................................
        # Test 2: with duration
        params = {
            "duration": 1
        }
        res = status.get(**params)
        res_expected = {
            "hits": [
                {
                    "id": 1,
                    "date_recently_completed": date1,
                    "date_oldest_job_queued": date1,
                    "avg_process_sec": 2,
                    "avg_wait_sec": 5,
                    "waiting_job_count": 3,
                    "processors_count": 2,
                    "date_created": date1
                }
            ],
            "socorro_revision": 42,
            "breakpad_revision": 43,
            "total": 1
        }

        self.assertEqual(res, res_expected)
