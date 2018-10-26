# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.postgresql.crontabber_state import CrontabberState
from socorro.unittest.external.postgresql.unittestbase import PostgreSQLTestCase


class IntegrationTestCrontabberStatus(PostgreSQLTestCase):
    """Test socorro.external.postgresql.crontabbers_state.CrontabberState
    class """

    def setUp(self):
        super(IntegrationTestCrontabberStatus, self).setUp()
        cursor = self.connection.cursor()

        # NOTE(willkg): Sometimes the test db gets into a "state", so
        # drop the table if it exists.
        cursor.execute("""
        DROP TABLE IF EXISTS cron_job, cron_log
        """)

        # NOTE(willkg): The socorro tests don't run with the Django-managed
        # database models created in the db, so we have to do it by hand until
        # we've moved everything out of sqlalchemy/alembic land to Django land.
        #
        # FIXME(willkg): Please stop this madness soon.
        #
        # From "./manage.py sqlmigrate cron 0002";

        cursor.execute("""
        CREATE TABLE "cron_job" (
        "id" serial NOT NULL PRIMARY KEY,
        "app_name" varchar(100) NOT NULL UNIQUE,
        "next_run" timestamp with time zone NULL,
        "first_run" timestamp with time zone NULL,
        "last_run" timestamp with time zone NULL,
        "last_success" timestamp with time zone NULL,
        "error_count" integer NOT NULL,
        "depends_on" text NULL,
        "last_error" text NULL,
        "ongoing" timestamp with time zone NULL);
        """)
        cursor.execute("""
        CREATE TABLE "cron_log" (
        "id" serial NOT NULL PRIMARY KEY,
        "app_name" varchar(100) NOT NULL,
        "log_time" timestamp with time zone NOT NULL,
        "duration" double precision NOT NULL,
        "success" timestamp with time zone NULL,
        "exc_type" text NULL,
        "exc_value" text NULL,
        "exc_traceback" text NULL);
        """)
        self.connection.commit()

    def tearDown(self):
        self.connection.cursor().execute("""
        DROP TABLE IF EXISTS cron_job, cron_log;
        """)
        super(IntegrationTestCrontabberStatus, self).tearDown()

    def truncate(self):
        cursor = self.connection.cursor()
        cursor.execute("""
        TRUNCATE cron_job, cron_log CASCADE;
        """)
        self.connection.commit()

    def test_get(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO cron_job (
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
                '',
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
                'slow-one',
                '{}'
            );
        """)
        self.connection.commit()

        state = CrontabberState(config=self.config)
        res = state.get()

        slow_one = res['state']['slow-one']
        assert slow_one['next_run'].isoformat() == '2013-02-09T01:16:00.893834+00:00'
        assert slow_one['first_run'].isoformat() == '2012-11-05T23:27:07.316347+00:00'
        assert slow_one['last_run'].isoformat() == '2013-02-09T00:16:00.893834+00:00'
        assert slow_one['last_success'].isoformat() == '2012-12-24T22:27:07.316893+00:00'
        assert slow_one['error_count'] == 6
        assert slow_one['depends_on'] == ''
        expected = {
            'traceback': 'error error error',
            'type': "<class 'sluggish.jobs.InternalError'>",
            'value': 'Have already run this for 2012-12-24 23:27'
        }
        assert slow_one['last_error'] == expected

        slow_two = res['state']['slow-two']
        assert slow_two['next_run'].isoformat() == '2012-11-12T19:39:59.521605+00:00'
        assert slow_two['first_run'].isoformat() == '2012-11-05T23:27:17.341879+00:00'
        assert slow_two['last_run'].isoformat() == '2012-11-12T18:39:59.521605+00:00'
        assert slow_two['last_success'].isoformat() == '2012-11-12T18:27:17.341895+00:00'
        assert slow_two['error_count'] == 0
        assert slow_two['depends_on'] == 'slow-one'
        assert slow_two['last_error'] == {}

    def test_get_with_some_null(self):
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO cron_job (
                app_name,
                next_run,
                first_run,
                last_run,
                last_success,
                error_count,
                depends_on,
                last_error
            ) VALUES (
                'slow-two',
                '2012-11-12 19:39:59.521605',
                '2012-11-05 23:27:17.341879',
                '2012-11-12 18:39:59.521605',
                null,
                0,
                '{"slow-one"}',
                '{}'
            );
        """)
        self.connection.commit()

        state = CrontabberState(config=self.config)
        res = state.get()

        assert res['state']['slow-two']['last_success'] is None
