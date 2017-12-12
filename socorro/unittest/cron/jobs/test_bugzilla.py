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

    def tearDown(self):
        self.conn.cursor().execute("TRUNCATE bug_associations CASCADE")
        self.conn.commit()
        super(IntegrationTestBugzilla, self).tearDown()

    def _setup_config_manager(self, days_into_past):
        return super(IntegrationTestBugzilla, self)._setup_config_manager(
            jobs_string='socorro.cron.jobs.bugzilla.BugzillaCronApp|1d',
            extra_value_source={
                'crontabber.class-BugzillaCronApp.days_into_past': days_into_past,
            }
        )

    def test_basic_run_job(self, requests_mocker):
        requests_mocker.get(BUGZILLA_BASE_URL, json=SAMPLE_BUGZILLA_RESULTS)
        config_manager = self._setup_config_manager(3)

        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        cursor = self.conn.cursor()
        cursor.execute('select bug_id from bug_associations order by bug_id')
        associations = cursor.fetchall()

        # Verify we have the expected number of associations.
        assert len(associations) == 8
        bug_ids = [x[0] for x in associations]

        # Verify bugs with no crash signatures are missing.
        assert 6 not in bug_ids

        cursor.execute(
            'select signature from bug_associations where bug_id = 8'
        )
        associations = cursor.fetchall()
        # New signatures have correctly been inserted.
        assert len(associations) == 2
        assert ('another::legitimate(sig)',) in associations
        assert ('legitimate(sig)',) in associations

    def test_run_job_with_reports_with_existing_bugs_different(self, requests_mocker):
        """Verify that an association to a signature that no longer is part
        of the crash signatures list gets removed.
        """
        requests_mocker.get(BUGZILLA_BASE_URL, json=SAMPLE_BUGZILLA_RESULTS)
        config_manager = self._setup_config_manager(3)
        cursor = self.conn.cursor()

        cursor.execute("""
            insert into bug_associations (bug_id, signature)
            values (8, '@different');
        """)
        self.conn.commit()

        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        cursor.execute(
            'select signature from bug_associations where bug_id = 8'
        )
        associations = cursor.fetchall()
        # The previous association, to signature '@different' that is not in
        # crash signatures, is now missing.
        assert ('@different',) not in associations

    def test_run_job_with_reports_with_existing_bugs_same(self, requests_mocker):
        requests_mocker.get(BUGZILLA_BASE_URL, json=SAMPLE_BUGZILLA_RESULTS)
        config_manager = self._setup_config_manager(3)
        cursor = self.conn.cursor()

        cursor.execute("""
            insert into bug_associations (bug_id, signature)
            values (8, 'legitimate(sig)');
        """)
        self.conn.commit()

        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        cursor.execute(
            'select signature from bug_associations where bug_id = 8'
        )
        associations = cursor.fetchall()
        # New signatures have correctly been inserted.
        assert len(associations) == 2
        assert ('another::legitimate(sig)',) in associations
        assert ('legitimate(sig)',) in associations

    def test_run_job_based_on_last_success(self, requests_mocker):
        """specifically setting 0 days back and no prior run
        will pick it up from now's date"""
        requests_mocker.get(BUGZILLA_BASE_URL, json=SAMPLE_BUGZILLA_RESULTS)
        config_manager = self._setup_config_manager(0)

        cursor = self.conn.cursor()
        # these are matching the SAMPLE_CSV above
        cursor.execute("""insert into bug_associations
        (bug_id,signature)
        values
        (8, 'legitimate(sig)');
        """)
        self.conn.commit()

        # second time
        config_manager = self._setup_config_manager(0)
        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            state = tab.job_state_database.copy()
            self._wind_clock(state, days=1)
            tab.job_state_database.update(state)

        # Create a CSV file for one day back.
        # This'll make sure there's a .csv file whose day
        # is that of the last run.
        self._setup_config_manager(1)

        config_manager = self._setup_config_manager(0)
        with config_manager.context() as config:
            tab = CronTabberApp(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

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
            # There has been an error.
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
