# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest
import requests_mock

from socorro.cron.crontabber_app import CronTabberApp
from socorro.cron.jobs.bugzilla import find_signatures
from socorro.cron.jobs.bugzilla import BUGZILLA_BASE_URL
from socorro.unittest.cron.jobs.base import IntegrationTestBase


SAMPLE_BUGZILLA_RESULTS = {
    'bugs': [
        {
            'id': '1',
            'cf_crash_signature': 'This sig, while bogus, has a ] bracket',
        },
        {
            'id': '2',
            'cf_crash_signature': 'single [@ BogusClass::bogus_sig (const char**) ] signature',
        },
        {
            'id': '3',
            'cf_crash_signature': '[@ js3250.dll@0x6cb96] [@ valid.sig@0x333333]',
        },
        {
            'id': '4',
            'cf_crash_signature': '[@ layers::Push@0x123456] [@ layers::Push@0x123456]',
        },
        {
            'id': '5',
            'cf_crash_signature': (
                '[@ MWSBAR.DLL@0x2589f] and a broken one [@ sadTrombone.DLL@0xb4s455'
            ),
        },
        {
            'id': '6',
            'cf_crash_signature': '',
        },
        {
            'id': '7',
            'cf_crash_signature': '[@gfx::font(nsTArray<nsRefPtr<FontEntry> > const&)]',
        },
        {
            'id': '8',
            'cf_crash_signature': '[@ legitimate(sig)] \n junk \n [@ another::legitimate(sig) ]',
        },
        {
            'id': '42',
        },
    ]
}


@requests_mock.Mocker()
class IntegrationTestBugzilla(IntegrationTestBase):
    def setUp(self):
        super(IntegrationTestBugzilla, self).setUp()

        cursor = self.conn.cursor()
        # NOTE(willkg): Sometimes the test db gets into a "state", so
        # drop the table if it exists.
        cursor.execute("""
        DROP TABLE IF EXISTS crashstats_bugassociation
        """)

        # NOTE(willkg): The socorro tests don't run with the Django-managed
        # database models created in the db, so we have to do it by hand until
        # we've moved everything out of sqlalchemy/alembic land to Django land.
        #
        # FIXME(willkg): Please stop this madness soon.
        #
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
        # Truncate crontabber tables before running tests
        self._truncate()

    def tearDown(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        DROP TABLE crashstats_bugassociation
        """)
        self.conn.commit()
        super(IntegrationTestBugzilla, self).tearDown()

    def _setup_config_manager(self, days_into_past):
        return super(IntegrationTestBugzilla, self)._setup_config_manager(
            jobs_string='socorro.cron.jobs.bugzilla.BugzillaCronApp|1d',
            extra_value_source={
                'crontabber.class-BugzillaCronApp.days_into_past': days_into_past,
            }
        )

    def fetch_data(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT bug_id, signature
        FROM crashstats_bugassociation
        ORDER BY bug_id, signature
        """)
        return [
            {
                'bug_id': str(result[0]),
                'signature': str(result[1])
            } for result in cursor.fetchall()
        ]

    def insert_data(self, bug_id, signature):
        cursor = self.conn.cursor()
        cursor.execute("""
        INSERT INTO crashstats_bugassociation (bug_id, signature)
        VALUES (%s, %s);
        """, (bug_id, signature))
        self.conn.commit()

    def test_basic_run_job(self, requests_mocker):
        requests_mocker.get(BUGZILLA_BASE_URL, json=SAMPLE_BUGZILLA_RESULTS)
        config_manager = self._setup_config_manager(3)

        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            print(information)
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        associations = self.fetch_data()

        # Verify we have the expected number of associations
        assert len(associations) == 8
        bug_ids = set([x['bug_id'] for x in associations])

        # Verify bugs with no crash signatures are missing
        assert 6 not in bug_ids

        bug_8_signatures = [
            item['signature'] for item in associations if item['bug_id'] == '8'
        ]

        # New signatures have correctly been inserted
        assert len(bug_8_signatures) == 2
        assert 'another::legitimate(sig)' in bug_8_signatures
        assert 'legitimate(sig)' in bug_8_signatures

    def test_run_job_with_reports_with_existing_bugs_different(self, requests_mocker):
        """Verify that an association to a signature that no longer is part
        of the crash signatures list gets removed.
        """
        requests_mocker.get(BUGZILLA_BASE_URL, json=SAMPLE_BUGZILLA_RESULTS)
        self.insert_data(bug_id='8', signature='@different')

        config_manager = self._setup_config_manager(3)
        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        # The previous association, to signature '@different' that is not in
        # crash signatures, is now missing
        associations = self.fetch_data()
        assert '@different' not in [item['signature'] for item in associations]

    def test_run_job_with_reports_with_existing_bugs_same(self, requests_mocker):
        requests_mocker.get(BUGZILLA_BASE_URL, json=SAMPLE_BUGZILLA_RESULTS)
        self.insert_data(bug_id='8', signature='legitimate(sig)')

        config_manager = self._setup_config_manager(3)
        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        associations = self.fetch_data()
        associations = [item['signature'] for item in associations if item['bug_id'] == '8']

        # New signatures have correctly been inserted
        assert len(associations) == 2
        assert associations == [
            'another::legitimate(sig)',
            'legitimate(sig)'
        ]

    def test_with_bugzilla_failure(self, requests_mocker):
        requests_mocker.get(
            BUGZILLA_BASE_URL,
            text='error loading content',
            status_code=500
        )
        config_manager = self._setup_config_manager(3)

        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            # Verify there has been an error
            last_error = information['bugzilla-associations']['last_error']
            assert last_error
            assert 'HTTPError' in last_error['type']
            assert not information['bugzilla-associations']['last_success']


@pytest.mark.parametrize('content, expected', [
    # Simple signature
    ('[@ moz::signature]', set(['moz::signature'])),
    # Using unicode.
    (u'[@ moz::signature]', set(['moz::signature'])),
    # 2 signatures and some junk
    (
        '@@3*&^!~[@ moz::signature][@   ns::old     ]',
        set(['moz::signature', 'ns::old'])
    ),
    # A signature containing square brackets.
    (
        '[@ moz::signature] [@ sig_with[brackets]]',
        set(['moz::signature', 'sig_with[brackets]'])
    ),
    # A malformed signature.
    ('[@ note there is no trailing bracket', set()),
])
def test_find_signatures(content, expected):
    assert find_signatures(content) == expected
