# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# NOTE(willkg): This file is based on crontabber's crontabber/tests/base.py
# file, then adjusted so it doesn't use nose.

import datetime
import json
import unittest
from collections import defaultdict, Sequence

from configman import ConfigurationManager
from mock import Mock
import six

from socorro.cron.crontabber_app import CronTabberApp, JobStateDatabase


def get_config_manager(jobs=None, overrides=None):
    crontabber_config = CronTabberApp.get_required_config()
    crontabber_config.add_option('logger', default=Mock())
    crontabber_config.add_option('metrics', default=Mock())

    local_overrides = {}
    if jobs:
        local_overrides['crontabber.jobs'] = jobs

    if isinstance(overrides, Sequence):
        overrides.append(local_overrides)
    elif overrides is not None:
        overrides = [overrides, local_overrides]
    else:
        overrides = [local_overrides]

    # Be sure to include defaults
    overrides.insert(0, CronTabberApp.config_defaults)

    return ConfigurationManager(
        [crontabber_config],
        values_source_list=overrides,
        app_name='test-crontabber',
        app_description='',
        argv_source=[]
    )


class IntegrationTestBase(unittest.TestCase):
    """Useful class for running integration tests related to crontabber apps
    since this class takes care of setting up a psycopg connection and it
    makes sure the ``cron_job`` and ``cron_log`` tables are empty.

    """
    def _wind_clock(self, state, days=0, hours=0, seconds=0):
        # note that 'hours' and 'seconds' can be negative numbers
        if days:
            hours += days * 24
        if hours:
            seconds += hours * 60 * 60

        # modify ALL last_run and next_run to pretend time has changed

        def _wind(data):
            for key, value in data.items():
                if isinstance(value, dict):
                    _wind(value)
                else:
                    if isinstance(value, datetime.datetime):
                        data[key] = value - datetime.timedelta(seconds=seconds)

        _wind(state)
        return state

    @classmethod
    def get_standard_config(cls):
        return get_config_manager().get_config()

    @classmethod
    def setUpClass(cls):
        super(IntegrationTestBase, cls).setUpClass()
        cls.config = cls.get_standard_config()

        db_connection_factory = cls.config.crontabber.database_class(cls.config.crontabber)
        cls.conn = db_connection_factory.connection()

        # instanciate one of these to make sure the tables are created
        JobStateDatabase(cls.config.crontabber)

    def _truncate(self):
        self.conn.cursor().execute("""
        TRUNCATE cron_job, cron_log CASCADE;
        """)
        self.conn.commit()

    def setUp(self):
        super(IntegrationTestBase, self).setUp()

        cursor = self.conn.cursor()

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
        self.conn.commit()

    def tearDown(self):
        super(IntegrationTestBase, self).tearDown()
        self.conn.cursor().execute("""
        DROP TABLE IF EXISTS cron_job, cron_log
        """)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        super(IntegrationTestBase, cls).tearDownClass()

    def assertAlmostEqual(self, val1, val2):
        if isinstance(val1, datetime.datetime) and isinstance(val2, datetime.datetime):
            # if there difference is just in the microseconds, they're
            # sufficiently equal
            return not abs(val1 - val2).seconds
        assert val1 == val2

    def _load_structure(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                app_name,
                next_run,
                first_run,
                last_run,
                last_success,
                error_count,
                depends_on,
                last_error,
                ongoing
            FROM cron_job
        """)
        columns = (
            'app_name', 'next_run', 'first_run', 'last_run', 'last_success',
            'error_count', 'depends_on', 'last_error', 'ongoing'
        )
        structure = {}
        try:
            for record in cursor.fetchall():
                row = dict(zip(columns, record))
                last_error = row.pop('last_error')
                if isinstance(last_error, six.string_types):
                    last_error = json.loads(last_error)
                row['last_error'] = last_error
                structure[row.pop('app_name')] = row
        finally:
            self.conn.commit()
        return structure

    def _update_structure(self, app_name, information, **updates):
        cursor = self.conn.cursor()
        information.update(updates)
        execute_vars = dict(
            information,
            app_name=app_name,
            last_error=json.dumps(information['last_error']),
        )
        cursor.execute("""
            UPDATE
                cron_job
            SET
                next_run = %(next_run)s,
                first_run = %(first_run)s,
                last_run = %(last_run)s,
                last_success = %(last_success)s,
                error_count = %(error_count)s,
                depends_on = %(depends_on)s,
                last_error = %(last_error)s,
                ongoing = %(ongoing)s
            WHERE
                app_name = %(app_name)s
        """, execute_vars)
        self.conn.commit()

    def _load_logs(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                app_name,
                log_time,
                duration,
                success,
                exc_type,
                exc_value,
                exc_traceback
            FROM cron_log
            ORDER BY log_time;
        """)
        columns = (
            'app_name', 'log_time', 'duration', 'success',
            'exc_type', 'exc_value', 'exc_traceback'
        )
        logs = defaultdict(list)
        try:
            for record in cursor.fetchall():
                row = dict(zip(columns, record))
                logs[row.pop('app_name')].append(row)
        finally:
            self.conn.commit()
        return logs
