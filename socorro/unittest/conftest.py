# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os

from markus.testing import MetricsMock
import psycopg2
import pytest
import requests_mock


@pytest.fixture
def req_mock():
    with requests_mock.mock() as mock:
        yield mock


@pytest.fixture
def metricsmock():
    """Returns MetricsMock that a context to record metrics records

    Usage::

        def test_something(metricsmock):
            with metricsmock as mm:
                # do stuff
                assert mm.has_record(
                    'incr',
                    stat='some.stat',
                    value=1
                )

    https://markus.readthedocs.io/en/latest/testing.html

    """
    return MetricsMock()


@pytest.fixture
def db_conn():
    dsn = os.environ['DATABASE_URL']
    conn = psycopg2.connect(dsn)

    tables = [
        'crashstats_bugassociation',
        'crashstats_productversion',
        'crashstats_signature',
        'cron_job',
        'cron_log',
    ]

    # Clean specific tables after usage
    cursor = conn.cursor()
    for table_name in tables:
        cursor.execute('TRUNCATE %s CASCADE' % table_name)
    conn.commit()

    yield conn

    # Clean specific tables after usage
    cursor = conn.cursor()
    for table_name in tables:
        cursor.execute('TRUNCATE %s CASCADE' % table_name)
    conn.commit()
