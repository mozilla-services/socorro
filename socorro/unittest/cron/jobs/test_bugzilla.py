# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os
import pytest
from dateutil import tz
from crontabber.app import CronTabber

from socorro.cron.jobs.bugzilla import find_signatures
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)
from socorro.unittest.cron.jobs.base import IntegrationTestBase


SAMPLE_CSV = [
    'bug_id,"cf_crash_signature"',
    '1,"This sig, while bogus, has a ] bracket"',
    '2,"single [@ BogusClass::bogus_sig (const char**) ] signature"',
    '3,"[@ js3250.dll@0x6cb96] [@ valid.sig@0x333333]"',
    '4,"[@ layers::Push@0x123456] [@ layers::Push@0x123456]"',
    '5,"[@ MWSBAR.DLL@0x2589f] and a broken one [@ sadTrombone.DLL@0xb4s455"',
    '6,""',
    '7,"[@gfx::font(nsTArray<nsRefPtr<FontEntry> > const&)]"',
    '8,"[@ legitimate(sig)] \n junk \n [@ another::legitimate(sig) ]"'
]


class IntegrationTestBugzilla(IntegrationTestBase):

    def tearDown(self):
        self.conn.cursor().execute("TRUNCATE bug_associations CASCADE")
        self.conn.commit()
        super(IntegrationTestBugzilla, self).tearDown()

    def _setup_config_manager(self, days_into_past):
        PST = tz.gettz('PST8PDT')
        datestring = (
            (
                datetime.datetime.now(PST) -
                datetime.timedelta(days=days_into_past)
            ).astimezone(PST).strftime('%Y-%m-%d')
        )
        filename = os.path.join(self.tempdir, 'sample-%s.csv' % datestring)
        with open(filename, 'w') as f:
            f.write('\n'.join(SAMPLE_CSV))

        query = 'file://' + filename.replace(datestring, '%s')

        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.bugzilla.BugzillaCronApp|1d',
            overrides={
                'crontabber.class-BugzillaCronApp.query': query,
                'crontabber.class-BugzillaCronApp.days_into_past': days_into_past,
            }
        )

    def test_basic_run_job(self):
        config_manager = self._setup_config_manager(3)

        with config_manager.context() as config:
            tab = CronTabber(config)
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

    def test_run_job_with_reports_with_existing_bugs_different(self):
        """Verify that an association to a signature that no longer is part
        of the crash signatures list gets removed.
        """
        config_manager = self._setup_config_manager(3)
        cursor = self.conn.cursor()

        cursor.execute("""
            insert into bug_associations (bug_id, signature)
            values (8, '@different');
        """)
        self.conn.commit()

        with config_manager.context() as config:
            tab = CronTabber(config)
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

    def test_run_job_with_reports_with_existing_bugs_same(self):
        config_manager = self._setup_config_manager(3)
        cursor = self.conn.cursor()

        cursor.execute("""
            insert into bug_associations (bug_id, signature)
            values (8, 'legitimate(sig)');
        """)
        self.conn.commit()

        with config_manager.context() as config:
            tab = CronTabber(config)
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

    def test_run_job_based_on_last_success(self):
        """specifically setting 0 days back and no prior run
        will pick it up from now's date"""
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
            tab = CronTabber(config)
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
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']


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
