# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import os

from markus.testing import MetricsMock
import psycopg2
import pytest


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


class DjangoTablesMixin(object):
    """Set up Django-managed tables used by tests

    This creates all the required tables, yields, and then cleans them all
    up.

    This is for use with unittest.TestCase style tests. If you want this
    without unittest.TestCase tests, then use the ``django_tables``
    pytest fixture.

    NOTE(willkg): The socorro tests don't run with the Django-managed
    database models created in the db, so we have to do it by hand until
    we've moved everything out of sqlalchemy/alembic land to Django land.

    FIXME(willkg): Please stop this madness soon.

    """
    _DJANGO_TABLES = [
        'crashstats_bugassociation',
        'crashstats_signature',
        'cron_job',
        'cron_log',
    ]

    @classmethod
    def _get_conn(cls):
        dsn = os.environ['DATABASE_URL']
        return psycopg2.connect(dsn)

    @classmethod
    def _drop_django_tables(cls):
        conn = cls._get_conn()
        cursor = conn.cursor()
        for table_name in cls._DJANGO_TABLES:
            cursor.execute('DROP TABLE IF EXISTS %s' % table_name)
        conn.commit()

    @classmethod
    def truncate_django_tables(cls):
        conn = cls._get_conn()
        cursor = conn.cursor()
        for table_name in cls._DJANGO_TABLES:
            cursor.execute('TRUNCATE %s CASCADE;' % table_name)
        conn.commit()

    @classmethod
    def _create_django_tables(cls):
        conn = cls._get_conn()
        cursor = conn.cursor()

        # Create tables in order

        # From "./manage.py sqlmigrate crashstats 0006":
        cursor.execute("""
        CREATE TABLE "crashstats_bugassociation" (
        "id" serial NOT NULL PRIMARY KEY,
        "bug_id" integer NOT NULL,
        "signature" text NOT NULL);
        """)
        cursor.execute("""
        ALTER TABLE "crashstats_bugassociation"
        ADD CONSTRAINT "crashstats_bugassociation_bug_id_signature_0123b7ff_uniq"
        UNIQUE ("bug_id", "signature");
        """)

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

        # From "./manage.py sqlmigrate crashstats 0004":
        cursor.execute("""
        CREATE TABLE "crashstats_signature" (
        "id" serial NOT NULL PRIMARY KEY,
        "signature" text NOT NULL UNIQUE,
        "first_build" bigint NOT NULL,
        "first_date" timestamp with time zone NOT NULL);
        """)
        cursor.execute("""
        CREATE INDEX "crashstats_signature_signature_15c3e97d_like"
        ON "crashstats_signature" ("signature" text_pattern_ops);
        """)
        conn.commit()

    @classmethod
    def setUpClass(cls):
        super(DjangoTablesMixin, cls).setUpClass()

        # Drop all the tables first so we have a clean slate
        cls._drop_django_tables()
        # Create tables
        cls._create_django_tables()

    def setUp(self):
        # Truncate tables for every test so there's nothing in them
        super(DjangoTablesMixin, self).setUp()
        self.truncate_django_tables()

    @classmethod
    def tearDownClass(cls):
        super(DjangoTablesMixin, cls).tearDownClass()
        cls._drop_django_tables()


@pytest.fixture
def django_tables():
    DjangoTablesMixin.setUpClass()
    yield
    DjangoTablesMixin.tearDownClass()
