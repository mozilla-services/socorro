# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os
from nose.plugins.attrib import attr
from nose.tools import eq_, ok_
from dateutil import tz
from crontabber.app import CronTabber
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)

from socorro.unittest.cron.jobs.base import IntegrationTestBase


SAMPLE_CSV = [
   'bug_id,"bug_status","resolution","short_desc","cf_crash_signature"',
   '1,"RESOLVED",,"this is a comment","This sig, while bogus, has a ] bracket"',
   '2,"CLOSED","WONTFIX","comments are not too important","single [@ BogusClass::bogus_sig (const char**) ] signature"',
   '3,"ASSIGNED",,"this is a comment. [@ nanojit::LIns::isTramp()]","[@ js3250.dll@0x6cb96] [@ valid.sig@0x333333]"',
   '4,"CLOSED","RESOLVED","two sigs enter, one sig leaves","[@ layers::Push@0x123456] [@ layers::Push@0x123456]"',
   '5,"ASSIGNED","INCOMPLETE",,"[@ MWSBAR.DLL@0x2589f] and a broken one [@ sadTrombone.DLL@0xb4s455"',
   '6,"ASSIGNED",,"empty crash sigs should not throw errors",""',
   '7,"CLOSED",,"gt 525355 gt","[@gfx::font(nsTArray<nsRefPtr<FontEntry> > const&)]"',
   '8,"CLOSED","RESOLVED","newlines in sigs","[@ legitimate(sig)] \n junk \n [@ another::legitimate(sig) ]"'
]


#==============================================================================
@attr(integration='postgres')
class IntegrationTestBugzilla(IntegrationTestBase):

    def tearDown(self):
        self.conn.cursor().execute("""
        TRUNCATE TABLE reports CASCADE;
        TRUNCATE TABLE bugs CASCADE;
        TRUNCATE TABLE bug_associations CASCADE;
        """)
        self.conn.commit()
        super(IntegrationTestBugzilla, self).tearDown()

    def _setup_config_manager(self, days_into_past):
        PST = tz.gettz('PST8PDT')
        datestring = ((datetime.datetime.now(PST) -
                       datetime.timedelta(days=days_into_past))
                       .astimezone(PST)
                       .strftime('%Y-%m-%d'))
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

    def test_basic_run_job_without_reports(self):
        config_manager = self._setup_config_manager(3)

        cursor = self.conn.cursor()
        cursor.execute('select count(*) from reports')
        count, = cursor.fetchone()
        assert count == 0, "reports table not cleaned"
        cursor.execute('select count(*) from bugs')
        count, = cursor.fetchone()
        assert count == 0, "'bugs' table not cleaned"
        cursor.execute('select count(*) from bug_associations')
        count, = cursor.fetchone()
        assert count == 0, "'bug_associations' table not cleaned"

        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        # now, because there we no matching signatures in the reports table
        # it means that all bugs are rejected
        cursor.execute('select count(*) from bugs')
        count, = cursor.fetchone()
        ok_(not count)
        cursor.execute('select count(*) from bug_associations')
        count, = cursor.fetchone()
        ok_(not count)

    def test_basic_run_job_with_some_reports(self):
        config_manager = self._setup_config_manager(3)

        cursor = self.conn.cursor()
        # these are matching the SAMPLE_CSV above
        cursor.execute("""insert into reports
        (uuid,signature)
        values
        ('123', 'legitimate(sig)');
        """)
        cursor.execute("""insert into reports
        (uuid,signature)
        values
        ('456', 'MWSBAR.DLL@0x2589f');
        """)
        self.conn.commit()

        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        cursor.execute('select id from bugs order by id')
        bugs = cursor.fetchall()
        eq_(len(bugs), 2)
        # the only bugs with matching those signatures are: 5 and 8
        bug_ids = [x[0] for x in bugs]
        eq_(bug_ids, [5, 8])

        cursor.execute('select bug_id from bug_associations order by bug_id')
        associations = cursor.fetchall()
        eq_(len(associations), 2)
        bug_ids = [x[0] for x in associations]
        eq_(bug_ids, [5, 8])

    def test_basic_run_job_with_reports_with_existing_bugs_different(self):
        config_manager = self._setup_config_manager(3)

        cursor = self.conn.cursor()
        cursor.execute('select count(*) from bugs')
        count, = cursor.fetchone()
        assert not count, count
        cursor.execute('select count(*) from bug_associations')
        count, = cursor.fetchone()
        assert not count, count
        cursor.execute('select count(*) from reports')
        count, = cursor.fetchone()
        assert not count, count

        # these are matching the SAMPLE_CSV above
        cursor.execute("""insert into reports
        (uuid,signature)
        values
        ('123', 'legitimate(sig)');
        """)
        cursor.execute("""insert into reports
        (uuid,signature)
        values
        ('456', 'MWSBAR.DLL@0x2589f');
        """)
        cursor.execute("""insert into bugs
        (id,status,resolution,short_desc)
        values
        (8, 'CLOSED', 'RESOLVED', 'Different');
        """)
        cursor.execute("""insert into bug_associations
        (bug_id,signature)
        values
        (8, '@different');
        """)
        self.conn.commit()

        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        cursor.execute('select id, short_desc from bugs where id = 8')
        bug = cursor.fetchone()
        eq_(bug[1], 'newlines in sigs')

        cursor.execute(
          'select signature from bug_associations where bug_id = 8')
        association = cursor.fetchone()
        eq_(association[0], 'legitimate(sig)')

    def test_basic_run_job_with_reports_with_existing_bugs_same(self):
        config_manager = self._setup_config_manager(3)

        cursor = self.conn.cursor()
        # these are matching the SAMPLE_CSV above
        cursor.execute("""insert into reports
        (uuid,signature)
        values
        ('123', 'legitimate(sig)');
        """)
        cursor.execute("""insert into reports
        (uuid,signature)
        values
        ('456', 'MWSBAR.DLL@0x2589f');
        """)
        # exactly the same as the fixture
        cursor.execute("""insert into bugs
        (id,status,resolution,short_desc)
        values
        (8, 'CLOSED', 'RESOLVED', 'newlines in sigs');
        """)
        cursor.execute("""insert into bug_associations
        (bug_id,signature)
        values
        (8, 'legitimate(sig)');
        """)
        self.conn.commit()

        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        cursor.execute('select id, short_desc from bugs where id = 8')
        bug = cursor.fetchone()
        eq_(bug[1], 'newlines in sigs')

        cursor.execute(
          'select signature from bug_associations where bug_id = 8')
        association = cursor.fetchone()
        eq_(association[0], 'legitimate(sig)')
        cursor.execute('select * from bug_associations')
