# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os

from nose.plugins.attrib import attr
from nose.tools import eq_

from socorro.external.postgresql.server_status_service import ServerStatus
from socorro.external.postgresql import server_status_service
from socorro.lib import datetimeutil
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
)

_revision_file_directory = os.path.dirname(server_status_service.__file__)

from unittestbase import PostgreSQLTestCase


#==============================================================================
@attr(integration='postgres')  # for nosetests
class IntegrationTestServerStatus(PostgreSQLTestCase):
    """Test socorro.external.postgresql.server_status_service.ServerStatus
    class. """

    #--------------------------------------------------------------------------
    def _insert_test_data(self, connection):
        # make sure we're clean first
        execute_no_results(
            connection,
            "TRUNCATE server_status, alembic_version CASCADE;"
        )

        # Insert data
        self.now = datetimeutil.utc_now()
        date1 = datetime.datetime(
            self.now.year, self.now.month, self.now.day, 12, 00, 00,
            tzinfo=self.now.tzinfo
        )
        date2 = date1 - datetime.timedelta(minutes=15)
        date3 = date2 - datetime.timedelta(minutes=15)
        date4 = date3 - datetime.timedelta(minutes=15)

        execute_no_results(
            connection,
            """
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

        # Prepare data for the schema revision
        # Clean up from init routine
        execute_no_results(
            connection,
            "TRUNCATE alembic_version CASCADE;")

        execute_no_results(
            connection,
            """
            INSERT INTO alembic_version
            (version_num)
            VALUES
            (
                'aaaaaaaaaaaa'
            )
        """)

    #--------------------------------------------------------------------------
    def setUp(self):
        """Set up this test class by populating the database with fake data.
        """
        super(IntegrationTestServerStatus, self).setUp(ServerStatus)
        # Create fake revision files
        self.basedir = _revision_file_directory
        self.socorro_revision_pathname = os.path.join(
            self.basedir, 'socorro_revision.txt'
        )
        with open(self.socorro_revision_pathname, 'w') as f:
            f.write('42')
        self.breakpad_revision_pathname = os.path.join(
            self.basedir, 'breakpad_revision.txt'
        )
        with open(self.breakpad_revision_pathname, 'w') as f:
            f.write('43')

        self.transaction(self._insert_test_data)

    #--------------------------------------------------------------------------
    def tearDown(self):
        """Clean up the database. """
        # Delete fake revision files
        os.remove(self.socorro_revision_pathname)
        os.remove(self.breakpad_revision_pathname)

        self.transaction(
            execute_no_results,
            "TRUNCATE server_status, alembic_version CASCADE;"
        )
        super(IntegrationTestServerStatus, self).tearDown()

    #--------------------------------------------------------------------------
    def test_get(self):
        status = ServerStatus(config=self.config)

        date1 = datetime.datetime(
            self.now.year, self.now.month, self.now.day, 12, 00, 00,
            tzinfo=self.now.tzinfo
        )
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
            "socorro_revision": "42",
            "breakpad_revision": "43",
            "schema_revision": "aaaaaaaaaaaa",
            "total": 4
        }

        eq_(res, res_expected)

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
            "socorro_revision": "42",
            "breakpad_revision": "43",
            "schema_revision": "aaaaaaaaaaaa",
            "total": 1
        }

        eq_(res, res_expected)
