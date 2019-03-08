# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# NOTE(willkg): This file is based on crontabber's crontabber/tests/base.py
# file, then adjusted so it doesn't use nose.

import json
from collections import Sequence

from configman import ConfigurationManager
from mock import Mock
import six

from socorro.cron.crontabber_app import CronTabberApp


def get_config_manager(jobs=None, overrides=None):
    crontabber_config = CronTabberApp.get_required_config()

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


def load_structure(conn):
    cursor = conn.cursor()
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
    for record in cursor.fetchall():
        row = dict(zip(columns, record))
        last_error = row.pop('last_error')
        if isinstance(last_error, six.string_types):
            last_error = json.loads(last_error)
        row['last_error'] = last_error
        structure[row.pop('app_name')] = row
    return structure
