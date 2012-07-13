# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import os
import json
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from nose.plugins.attrib import attr
from socorro.cron import crontabber
from ..base import TestCaseBase, DSN


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
@attr(integration='postgres')  # for nosetests
class TestFunctionalBugzilla(TestCaseBase):

    def setUp(self):
        super(TestFunctionalBugzilla, self).setUp()
        # prep a fake table
        assert 'test' in DSN['database_name'], DSN['database_name']
        dsn = ('host=%(database_host)s dbname=%(database_name)s '
               'user=%(database_user)s password=%(database_password)s' % DSN)
        self.conn = psycopg2.connect(dsn)
        cursor = self.conn.cursor()
        cursor.execute('select count(*) from crontabber_state')
        if cursor.fetchone()[0] < 1:
            cursor.execute("""
            INSERT INTO crontabber_state (state, last_updated)
            VALUES ('{}', NOW());
            """)
        else:
            cursor.execute("""
            UPDATE crontabber_state SET state='{}';
            """)
        self.conn.commit()
        assert self.conn.get_transaction_status() == TRANSACTION_STATUS_IDLE

    def tearDown(self):
        super(TestFunctionalBugzilla, self).tearDown()
        self.conn.cursor().execute("""
        UPDATE crontabber_state SET state='{}';
        TRUNCATE TABLE reports CASCADE;
        TRUNCATE TABLE bugs CASCADE;
        TRUNCATE TABLE bug_associations CASCADE;
        """)
        self.conn.commit()

    def _setup_config_manager(self, days_into_past):
        datestring = ((datetime.datetime.utcnow() -
                       datetime.timedelta(days=days_into_past))
                       .strftime('%Y-%m-%d'))
        filename = os.path.join(self.tempdir, 'sample-%s.csv' % datestring)
        with open(filename, 'w') as f:
            f.write('\n'.join(SAMPLE_CSV))

        query = 'file://' + filename.replace(datestring, '%s')

        _super = super(TestFunctionalBugzilla, self)._setup_config_manager
        config_manager, json_file = _super(
          'socorro.cron.jobs.bugzilla.BugzillaCronApp|1d',
          extra_value_source={
            'class-BugzillaCronApp.query': query,
            'class-BugzillaCronApp.days_into_past': days_into_past,
          }
        )
        return config_manager, json_file

    def test_basic_run_job_without_reports(self):
        config_manager, json_file = self._setup_config_manager(3)

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
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        # now, because there we no matching signatures in the reports table
        # it means that all bugs are rejected
        cursor.execute('select count(*) from bugs')
        count, = cursor.fetchone()
        self.assertTrue(not count)
        cursor.execute('select count(*) from bug_associations')
        count, = cursor.fetchone()
        self.assertTrue(not count)

    def test_basic_run_job_with_some_reports(self):
        config_manager, json_file = self._setup_config_manager(3)

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
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        cursor.execute('select id from bugs order by id')
        bugs = cursor.fetchall()
        self.assertEqual(len(bugs), 2)
        # the only bugs with matching those signatures are: 5 and 8
        bug_ids = [x[0] for x in bugs]
        self.assertEqual(bug_ids, [5, 8])

        cursor.execute('select bug_id from bug_associations order by bug_id')
        associations = cursor.fetchall()
        self.assertEqual(len(associations), 2)
        bug_ids = [x[0] for x in associations]
        self.assertEqual(bug_ids, [5, 8])

    def test_basic_run_job_with_reports_with_existing_bugs_different(self):
        config_manager, json_file = self._setup_config_manager(3)

        cursor = self.conn.cursor()
        cursor.execute('select count(*) from bugs')
        count, = cursor.fetchone()
        assert not count
        cursor.execute('select count(*) from bug_associations')
        count, = cursor.fetchone()
        assert not count

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
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        cursor.execute('select id, short_desc from bugs where id = 8')
        bug = cursor.fetchone()
        self.assertEqual(bug[1], 'newlines in sigs')

        cursor.execute(
          'select signature from bug_associations where bug_id = 8')
        association = cursor.fetchone()
        self.assertEqual(association[0], 'legitimate(sig)')

    def test_basic_run_job_with_reports_with_existing_bugs_same(self):
        config_manager, json_file = self._setup_config_manager(3)

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
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['bugzilla-associations']
            assert not information['bugzilla-associations']['last_error']
            assert information['bugzilla-associations']['last_success']

        cursor.execute('select id, short_desc from bugs where id = 8')
        bug = cursor.fetchone()
        self.assertEqual(bug[1], 'newlines in sigs')

        cursor.execute(
          'select signature from bug_associations where bug_id = 8')
        association = cursor.fetchone()
        self.assertEqual(association[0], 'legitimate(sig)')
        cursor.execute('select * from bug_associations')
