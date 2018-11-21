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

from socorro.cron.crontabber_app import CronTabberApp


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

    def setUp(self):
        super(IntegrationTestBase, self).setUp()
        self.config = self.get_standard_config()

        connection_context = self.config.crontabber.database_class(self.config.crontabber)
        self.conn = connection_context.connection()
        self.truncate_django_tables()

    def tearDown(self):
        self.conn.close()
        super(IntegrationTestBase, self).tearDown()

    def truncate_django_tables(self):
        django_tables = [
            'crashstats_bugassociation',
            'crashstats_productversion',
            'crashstats_signature',
            'cron_job',
            'cron_log',
        ]
        cursor = self.conn.cursor()
        for table_name in django_tables:
            cursor.execute('TRUNCATE %s CASCADE' % table_name)
        self.conn.commit()

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
