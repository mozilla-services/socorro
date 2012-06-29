# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import gzip
import shutil
import os
import json
import unittest
import tempfile
from subprocess import PIPE
import mock
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from nose.plugins.attrib import attr
from socorro.cron import crontabber
from socorro.unittest.config.commonconfig import (
  databaseHost, databaseName, databaseUserName, databasePassword)
from configman import ConfigurationManager

DSN = {
  "database_host": databaseHost.default,
  "database_name": databaseName.default,
  "database_user": databaseUserName.default,
  "database_password": databasePassword.default
}


class _TestCaseBase(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.tempdir):
            shutil.rmtree(self.tempdir)

    def _setup_config_manager(self, jobs_string, extra_value_source=None):
        if not extra_value_source:
            extra_value_source = {}
        mock_logging = mock.Mock()
        required_config = crontabber.CronTabber.required_config
        required_config.add_option('logger', default=mock_logging)

        json_file = os.path.join(self.tempdir, 'test.json')
        assert not os.path.isfile(json_file)

        config_manager = ConfigurationManager(
            [required_config,
             #logging_required_config(app_name)
             ],
            app_name='crontabber',
            app_description=__doc__,
            values_source_list=[{
                'logger': mock_logging,
                'jobs': jobs_string,
                'database': json_file,
            }, DSN, extra_value_source]
        )
        return config_manager, json_file


#==============================================================================
@attr(integration='postgres')  # for nosetests
class TestFunctionalDailyURL(_TestCaseBase):

    def setUp(self):
        super(TestFunctionalDailyURL, self).setUp()
        # prep a fake table
        assert 'test' in databaseName.default, databaseName.default
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

        self.Popen_patcher = mock.patch('subprocess.Popen')
        self.Popen = self.Popen_patcher.start()

    def tearDown(self):
        super(TestFunctionalDailyURL, self).tearDown()
        self.conn.cursor().execute("""
        UPDATE crontabber_state SET state='{}';
        TRUNCATE TABLE reports CASCADE;
        TRUNCATE TABLE bugs CASCADE;
        TRUNCATE TABLE bug_associations CASCADE;
        TRUNCATE TABLE productdims CASCADE;
        """)
        self.conn.commit()
        self.Popen_patcher.stop()

    def _setup_config_manager(self, product='WaterWolf',
                              output_path=None,
                              public_output_path=None,
                              **kwargs
                              #version=None,
                              #private_user='ted',
                              #private_server='secure.mozilla.org',
                              #private_location='/var/logs/',
                              #public_user='bill',
                              #public_server='ftp.mozilla.org',
                              #public_location='/tmp/%Y%m%d/',
                              ):
        _super = super(TestFunctionalDailyURL, self)._setup_config_manager
        if output_path is None:
            output_path = self.tempdir
        if public_output_path is None:
            public_output_path = self.tempdir
        extra_value_source = {
            'class-DailyURLCronApp.output_path': output_path,
            'class-DailyURLCronApp.public_output_path': public_output_path,
            'class-DailyURLCronApp.product': product,
          }
        for key, value in kwargs.items():
            extra_value_source['class-DailyURLCronApp.%s' % key] = value

        config_manager, json_file = _super(
          'socorro.cron.jobs.daily_url.DailyURLCronApp|1d',
          extra_value_source=extra_value_source
        )
        return config_manager, json_file

    def test_basic_run_job_no_data(self):
        config_manager, json_file = self._setup_config_manager()

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['daily-url']
            assert not information['daily-url']['last_error']
            assert information['daily-url']['last_success']

            # this should have created two .csv.gz files
            now = datetime.datetime.utcnow() - datetime.timedelta(days=1)

            private = now.strftime('%Y%m%d-crashdata.csv.gz')
            public = now.strftime('%Y%m%d-pub-crashdata.csv.gz')
            self.assertTrue(private in os.listdir(self.tempdir))
            self.assertTrue(public in os.listdir(self.tempdir))

            private_path = os.path.join(self.tempdir, private)
            f = gzip.open(private_path)
            try:
                self.assertEqual(f.read(), '')
            finally:
                f.close()

            public_path = os.path.join(self.tempdir, public)
            f = gzip.open(public_path)
            try:
                self.assertEqual(f.read(), '')
            finally:
                f.close()

    def test_run_job_no_data_but_scped(self):
        config_manager, json_file = self._setup_config_manager(
          public_output_path='',
          private_user='peter',
          private_server='secure.mozilla.org',
          private_location='/var/data/',
          private_ssh_command='chmod 0640 /var/data/*',
        )

        def comm():
            # no errors
            return '', ''

        self.Popen().communicate.side_effect = comm

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['daily-url']
            assert not information['daily-url']['last_error']
            assert information['daily-url']['last_success']

        # even though the files created are empty they should nevertheless
        # be scp'ed
        # can expect the command exactly
        now = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        private = now.strftime('%Y%m%d-crashdata.csv.gz')
        private_path = os.path.join(self.tempdir, private)
        assert os.path.isfile(private_path)
        scp_command = 'scp "%s" "peter@secure.mozilla.org:/var/data/"' % private_path
        ssh_command = 'ssh "peter@secure.mozilla.org" "chmod 0640 /var/data/*"'
        self.Popen.assert_any_call(
          scp_command,
          stdin=PIPE, stderr=PIPE, stdout=PIPE,
          shell=True
        )

        self.Popen.assert_any_call(
          ssh_command,
          stdin=PIPE, stderr=PIPE, stdout=PIPE,
          shell=True
        )

    def _insert_waterwolf_mock_data(self):
        # these csv-like chunks of data are from the dataload tool
        productdims = """
        1,WaterWolf,1.0,2.2,major,1,001000z000000
        2,WaterWolf,2.0,2.2,development,2,002000z000000
        3,WaterWolf,3.0a2,2.2,development,3,003000z000000
        4,WaterWolf,4.0a1,2.2,milestone,4,004000z000000
        """

        reports = """
1,2012-06-15 10:34:45-07,2012-06-15 23:35:06.262196,0ac2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,1.0,20120615000001,FakeSignature1,http://porn.xxx,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-15 00:35:16.368154,2012-06-15 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,release,{waterwolf@example.org}
2,2012-06-15 10:34:45-07,2012-06-15 23:35:06.262196,0bc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,2.0,20120615000002,FakeSignature2,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-15 00:35:16.368154,2012-06-15 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,beta,{waterwolf@example.org}
3,2012-06-15 10:34:45-07,2012-06-15 23:35:06.262196,0cc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,3.0a2,20120615000003,FakeSignature3,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-15 00:35:16.368154,2012-06-15 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,aurora,{waterwolf@example.org}
4,2012-06-15 10:34:45-07,2012-06-15 23:35:06.262196,0dc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,4.0a1,20120615000004,FakeSignature4,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-15 00:35:16.368154,2012-06-15 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,nightly,{waterwolf@example.org}
5,2012-06-16 10:34:45-07,2012-06-16 23:35:06.262196,1ac2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,1.0,20120615000001,FakeSignature1,http://porn.xxx,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-16 00:35:16.368154,2012-06-16 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,release,{waterwolf@example.org}
6,2012-06-16 10:34:45-07,2012-06-16 23:35:06.262196,1bc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,2.0,20120615000002,FakeSignature2,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-16 00:35:16.368154,2012-06-16 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,beta,{waterwolf@example.org}
7,2012-06-16 10:34:45-07,2012-06-16 23:35:06.262196,1cc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,3.0a2,20120615000003,FakeSignature3,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-16 00:35:16.368154,2012-06-16 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,aurora,{waterwolf@example.org}
8,2012-06-16 10:34:45-07,2012-06-16 23:35:06.262196,1dc2e16a-a718-43c0-a1a5-6bf922111017,WaterWolf,4.0a1,20120615000004,FakeSignature4,,391578,,25,x86,GenuineIntel family 6 model 23 stepping 10 | 2,EXCEPTION_ACCESS_VIOLATION_READ,0x66a0665,Windows NT,5.1.2600 Service Pack 3,,"",2012-06-16 00:35:16.368154,2012-06-16 00:35:18.463317,t,f,"",,,,,"",t,9.0.124.0,,,nightly,{waterwolf@example.org}
        """
        reports = reports.replace(
            '2012-06-16',
            (datetime.datetime.utcnow()
             - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        )

        lines = []
        for line in productdims.strip().splitlines():
            lines.append(
              'insert into productdims values (' +
              ','.join(x.isdigit() and str(x) or "'%s'" % x
                       for x in line.strip().split(','))
              + ');'
            )
        for line in reports.strip().splitlines():
            lines.append(
              'insert into reports values (' +
              ','.join(not x and '0' or x.isdigit() and str(x) or "'%s'" % x
                       for x in line.strip().split(','))
              + ');'
            )

        mock_sql = '\n'.join(lines + [''])
        self.conn.cursor().execute(mock_sql)
        self.conn.commit()

    def test_run_job_with_mocked_data(self):
        config_manager, json_file = self._setup_config_manager()
        self._insert_waterwolf_mock_data()

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['daily-url']
            assert not information['daily-url']['last_error']
            assert information['daily-url']['last_success']

            # this should have created two .csv.gz files
            now = datetime.datetime.utcnow() - datetime.timedelta(days=1)

            private = now.strftime('%Y%m%d-crashdata.csv.gz')
            public = now.strftime('%Y%m%d-pub-crashdata.csv.gz')
            self.assertTrue(private in os.listdir(self.tempdir))
            self.assertTrue(public in os.listdir(self.tempdir))

            private_path = os.path.join(self.tempdir, private)
            f = gzip.open(private_path)
            try:
                content = f.read()
                self.assertTrue(content)
                lines = content.splitlines()
                header = lines[0]
                payload = lines[1:]
                self.assertEqual(header.split('\t')[0], 'signature')
                self.assertEqual(header.split('\t')[1], 'url')
                urls = [x.split('\t')[1] for x in payload]
                self.assertTrue('http://porn.xxx' in urls)
                signatures = [x.split('\t')[0] for x in payload]
                self.assertEqual(sorted(signatures),
                                 ['FakeSignature1',
                                  'FakeSignature2',
                                  'FakeSignature3',
                                  'FakeSignature4'])
            finally:
                f.close()

            public_path = os.path.join(self.tempdir, public)
            f = gzip.open(public_path)
            try:
                content = f.read()
                self.assertTrue(content)
                lines = content.splitlines()
                header = lines[0]
                payload = lines[1:]
                self.assertEqual(header.split('\t')[0], 'signature')
                self.assertEqual(header.split('\t')[1], 'URL (removed)')
                urls = [x.split('\t')[1] for x in payload]
                self.assertTrue('http://porn.xxx' not in urls)
                signatures = [x.split('\t')[0] for x in payload]
                self.assertEqual(sorted(signatures),
                                 ['FakeSignature1',
                                  'FakeSignature2',
                                  'FakeSignature3',
                                  'FakeSignature4'])
            finally:
                f.close()

    def test_run_job_with_mocked_data_with_scp_errors(self):
        config_manager, json_file = self._setup_config_manager(
          public_output_path='',
          private_user='peter',
          private_server='secure.mozilla.org',
          private_location='/var/data/',
        )
        self._insert_waterwolf_mock_data()

        def comm():
            # some errors
            return '', "CRAP!"

        self.Popen().communicate.side_effect = comm

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['daily-url']
            assert not information['daily-url']['last_error']
            assert information['daily-url']['last_success']
            self.assertTrue(config.logger.warn.called)

    def test_run_job_with_no_data_with_ssh_errors(self):
        config_manager, json_file = self._setup_config_manager(
          public_output_path='',
          private_user='peter',
          private_server='secure.mozilla.org',
          private_location='/var/data/',
          private_ssh_command='chmod 0640 /var/data/*',
        )
        self._insert_waterwolf_mock_data()

        # any mutable so we can keep track of the number of times
        # the side_effect function is called
        calls = []

        def comm():
            if calls:
                # some errors
                return '', "CRAP!"
            else:
                calls.append(1)
                return '', ''

        self.Popen().communicate.side_effect = comm

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['daily-url']
            assert not information['daily-url']['last_error']
            assert information['daily-url']['last_success']

            self.assertTrue(config.logger.warn.called)

    def test_run_job_with_mocked_data_with_wrong_products(self):
        config_manager, json_file = self._setup_config_manager(
            product='Thunderbird,SeaMonkey',
            version='1.0,2.0',
            public_output_path=False
        )
        self._insert_waterwolf_mock_data()

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = json.load(open(json_file))
            assert information['daily-url']
            assert not information['daily-url']['last_error']
            assert information['daily-url']['last_success']

            # this should have created two .csv.gz files
            now = datetime.datetime.utcnow() - datetime.timedelta(days=1)

            private = now.strftime('%Y%m%d-crashdata.csv.gz')
            public = now.strftime('%Y%m%d-pub-crashdata.csv.gz')
            self.assertTrue(private in os.listdir(self.tempdir))
            self.assertTrue(public not in os.listdir(self.tempdir))

            private_path = os.path.join(self.tempdir, private)
            f = gzip.open(private_path)
            try:
                self.assertEqual(f.read(), '')
            finally:
                f.close()
