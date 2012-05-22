import re
import sys
import datetime
import shutil
import os
import json
import unittest
import tempfile
from cStringIO import StringIO
import mock
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from nose.plugins.attrib import attr
from socorro.cron import crontabber
from socorro.unittest.config.commonconfig import (
  databaseHost, databaseName, databaseUserName, databasePassword)
from socorro.lib.datetimeutil import utc_now
from configman import ConfigurationManager, Namespace

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

    def _wind_clock(self, json_file, days=0, hours=0, seconds=0):
        # note that 'hours' and 'seconds' can be negative numbers
        if days:
            hours += days * 24
        if hours:
            seconds += hours * 60 * 60

        # modify ALL last_run and next_run to pretend time has changed
        db = crontabber.JSONJobDatabase()
        db.load(json_file)

        def _wind(data):
            for key, value in data.items():
                if isinstance(value, dict):
                    _wind(value)
                else:
                    if isinstance(value, datetime.datetime):
                        data[key] = value - datetime.timedelta(seconds=seconds)

        _wind(db)
        db.save(json_file)


#==============================================================================
class TestJSONJobsDatabase(_TestCaseBase):
    """This has nothing to do with Socorro actually. It's just tests for the
    underlying JSON database.
    """

    def test_loading_existing_file(self):
        db = crontabber.JSONJobDatabase()
        file1 = os.path.join(self.tempdir, 'file1.json')

        stuff = {
          'foo': 1,
          'more': {
            'bar': u'Bar'
          }
        }
        json.dump(stuff, open(file1, 'w'))
        db.load(file1)
        self.assertEqual(db['foo'], 1)
        self.assertEqual(db['more']['bar'], u"Bar")

    def test_saving_new_file(self):
        db = crontabber.JSONJobDatabase()
        file1 = os.path.join(self.tempdir, 'file1.json')

        db.load(file1)
        self.assertEqual(db, {})

        db['foo'] = 1
        db['more'] = {'bar': u'Bar'}
        db.save(file1)
        structure = json.load(open(file1))
        self.assertEqual(structure,
                         {u'foo': 1, u'more': {u'bar': u'Bar'}})

        # check that save doesn't actually change anything
        self.assertEqual(db['foo'], 1)
        self.assertEqual(db['more']['bar'], u"Bar")

    def test_saving_dates(self):
        db = crontabber.JSONJobDatabase()
        file1 = os.path.join(self.tempdir, 'file1.json')

        db.load(file1)
        self.assertEqual(db, {})

        now = datetime.datetime.now()
        today = datetime.date.today()
        db['here'] = now
        db['there'] = {'now': today}
        db.save(file1)

        structure = json.load(open(file1))
        # try to avoid the exact strftime
        self.assertTrue(now.strftime('%H:%M') in structure['here'])
        self.assertTrue(now.strftime('%Y') in structure['here'])
        self.assertTrue(now.strftime('%Y') in structure['there']['now'])
        self.assertTrue(now.strftime('%m') in structure['there']['now'])
        self.assertTrue(now.strftime('%d') in structure['there']['now'])

        # create a new db a load this stuff in
        db2 = crontabber.JSONJobDatabase()
        db2.load(file1)
        self.assertTrue(isinstance(db2['here'], datetime.datetime))
        self.assertTrue(isinstance(db2['there']['now'], datetime.date))

    def test_loading_broken_json(self):
        file1 = os.path.join(self.tempdir, 'file1.json')
        with open(file1, 'w') as f:
            f.write('{Junk\n')
        db = crontabber.JSONJobDatabase()
        self.assertRaises(crontabber.BrokenJSONError, db.load, file1)


#==============================================================================
class TestCrontabber(_TestCaseBase):

    def setUp(self):
        super(TestCrontabber, self).setUp()
        self.psycopg2_patcher = mock.patch('psycopg2.connect')
        self.mocked_connection = mock.Mock()
        self.psycopg2 = self.psycopg2_patcher.start()

    def tearDown(self):
        super(TestCrontabber, self).tearDown()
        self.psycopg2_patcher.stop()

    def test_basic_run_job(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.BasicJob|7d'
        )

        def fmt(d):
            return d.split('.')[0]

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            self.assertRaises(
                crontabber.JobNotFoundError,
                tab.run_one,
                'unheard-of-app-name'
            )
            tab.run_one('basic-job')
            config.logger.info.assert_called_with('Ran BasicJob')

            infos = [x[0][0] for x in config.logger.info.call_args_list]

            # check that this was written to the JSON file
            # and that the next_run is going to be 1 day from now
            assert os.path.isfile(json_file)
            structure = json.load(open(json_file))
            information = structure['basic-job']
            self.assertEqual(information['error_count'], 0)
            self.assertEqual(information['last_error'], {})
            today = utc_now()
            one_week = today + datetime.timedelta(days=7)
            self.assertTrue(today.strftime('%Y-%m-%d')
                            in information['last_run'])
            self.assertTrue(today.strftime('%H:%M:%S')
                            in information['last_run'])
            self.assertTrue(one_week.strftime('%Y-%m-%d')
                            in information['next_run'])
            self.assertEqual(fmt(information['last_run']),
                             fmt(information['last_success']))

            # run it again and nothing should happen
            count_infos = len([x for x in infos if 'Ran BasicJob' in x])
            assert count_infos > 0
            tab.run_one('basic-job')
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            count_infos_after = len([x for x in infos if 'Ran BasicJob' in x])
            self.assertEqual(count_infos, count_infos_after)

            # force it the second time
            tab.run_one('basic-job', force=True)
            self.assertTrue('Ran BasicJob' in infos)
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            count_infos_after_second = len([x for x in infos
                                            if 'Ran BasicJob' in x])
            self.assertEqual(count_infos_after_second, count_infos + 1)

    def test_run_job_by_class_path(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.BasicJob|30m'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_one('socorro.unittest.cron.test_crontabber.BasicJob')
            config.logger.info.assert_called_with('Ran BasicJob')

    def test_basic_run_all(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.FooJob|3d\n'
          'socorro.unittest.cron.test_crontabber.BarJob|4d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertTrue('Ran FooJob' in infos)
            self.assertTrue('Ran BarJob' in infos)
            self.assertTrue(infos.index('Ran FooJob') <
                            infos.index('Ran BarJob'))
            count = len(infos)

            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            count_after = len(infos)
            self.assertEqual(count, count_after)

            # wind the clock forward by three days
            self._wind_clock(json_file, days=3)

            # this forces in crontabber instance to reload the JSON file
            tab._database = None

            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertEqual(infos[-1], 'Ran FooJob')
            count_after_after = len(infos)
            self.assertEqual(count_after + 1, count_after_after)

    def test_run_into_error_first_time(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.TroubleJob|7d\n'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            assert os.path.isfile(json_file)
            structure = json.load(open(json_file))
            information = structure['trouble']

            self.assertEqual(information['error_count'], 1)
            self.assertTrue(information['last_error'])
            self.assertTrue(not information.get('last_success'), {})
            today = utc_now()
            one_week = today + datetime.timedelta(days=7)
            self.assertTrue(today.strftime('%Y-%m-%d')
                            in information['last_run'])
            self.assertTrue(today.strftime('%H:%M:%S')
                            in information['last_run'])
            self.assertTrue(one_week.strftime('%Y-%m-%d')
                            in information['next_run'])

            # list the output
            old_stdout = sys.stdout
            new_stdout = StringIO()
            sys.stdout = new_stdout

            try:
                tab.list_jobs()
            finally:
                sys.stdout = old_stdout
            output = new_stdout.getvalue()
            last_success_line = [x for x in output.splitlines()
                                 if 'Last success' in x][0]
            self.assertTrue('no previous successful run' in last_success_line)

    def test_run_all_with_failing_dependency(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.TroubleJob|1d\n'
          'socorro.unittest.cron.test_crontabber.SadJob|1d\n'
          'socorro.unittest.cron.test_crontabber.BasicJob|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertEqual(infos, ['Ran TroubleJob', 'Ran BasicJob'])
            # note how SadJob couldn't be run!
            # let's see what information we have
            assert os.path.isfile(json_file)
            structure = json.load(open(json_file))
            self.assertTrue('basic-job' in structure)
            self.assertTrue('trouble' in structure)
            self.assertTrue('sad' not in structure)
            self.assertEqual(structure['trouble']['error_count'], 1)
            err = structure['trouble']['last_error']
            self.assertTrue('NameError' in err['traceback'])
            self.assertTrue('NameError' in err['type'])
            self.assertTrue('Trouble!!' in err['value'])

            # you can't run the sad job either
            count_before = len(infos)
            tab.run_one('sad')
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            count_after = len(infos)
            self.assertEqual(count_before, count_after)

            # unless you force it
            tab.run_one('sad', force=True)
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            count_after_after = len(infos)
            self.assertEqual(count_after + 1, count_after_after)

    def test_run_all_basic_with_failing_dependency_without_errors(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.BarJob|1d'
        )

        # the BarJob one depends on FooJob but suppose that FooJob
        # hasn't never run
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertEqual(infos, [])

    def test_run_all_with_failing_dependency_without_errors_but_old(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.FooJob|1d\n'
          'socorro.unittest.cron.test_crontabber.BarJob|1d'
        )
        # the BarJob one depends on FooJob but suppose that FooJob
        # has run for but a very long time ago
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            # obvious
            self.assertEqual(infos, ['Ran FooJob', 'Ran BarJob'])

            self._wind_clock(json_file, days=1, seconds=1)
            # this forces in crontabber instance to reload the JSON file
            tab._database = None

            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            # obvious
            self.assertEqual(infos,
              ['Ran FooJob', 'Ran BarJob', 'Ran FooJob', 'Ran BarJob'])

            # repeat
            self._wind_clock(json_file, days=2)
            tab._database = None

            # now, let's say FooJob hasn't errored but instead we try to run
            # the dependent and it shouldn't allow it
            tab.run_one('bar')
            infos_before = infos[:]
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertEqual(infos, infos_before)

    def test_basic_run_job_with_hour(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.BasicJob|7d|03:00\n'
          'socorro.unittest.cron.test_crontabber.FooJob|1:45'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]

            assert os.path.isfile(json_file)
            structure = json.load(open(json_file))
            next_run = structure['basic-job']['next_run']
            self.assertTrue('03:00:00' in next_run)
            next_run = structure['foo']['next_run']
            self.assertTrue('01:45:00' in next_run)

    def test_list_jobs(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.SadJob|5h\n'
          'socorro.unittest.cron.test_crontabber.TroubleJob|1d\n'
          'socorro.unittest.cron.test_crontabber.BasicJob|7d|03:00\n'
          'socorro.unittest.cron.test_crontabber.FooJob|2d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            old_stdout = sys.stdout
            new_stdout = StringIO()
            sys.stdout = new_stdout
            try:
                tab.list_jobs()
            finally:
                sys.stdout = old_stdout
            output = new_stdout.getvalue()
            self.assertEqual(output.count('Class:'), 4)
            self.assertEqual(4,
              len(re.findall('App name:\s+(trouble|basic-job|foo|sad)',
                             output, re.I)))
            self.assertEqual(4,
              len(re.findall('No previous run info', output, re.I)))

            tab.run_all()
            assert 'sad' not in tab.database
            assert 'basic-job' in tab.database
            assert 'foo' in tab.database
            assert 'trouble' in tab.database
            old_stdout = sys.stdout
            new_stdout = StringIO()
            sys.stdout = new_stdout
            try:
                tab.list_jobs()
            finally:
                sys.stdout = old_stdout
            output = new_stdout.getvalue()
            # sad job won't be run since its depdendent keeps failing
            self.assertEqual(1,
              len(re.findall('No previous run info', output, re.I)))

            # split them up so that we can investigate each block of output
            outputs = {}
            for block in re.split('={5,80}', output)[1:]:
                key = re.findall('App name:\s+([\w-]+)', block)[0]
                outputs[key] = block

            self.assertTrue(re.findall('No previous run info',
                                       outputs['sad'], re.I))
            self.assertTrue(re.findall('Error',
                                       outputs['trouble'], re.I))
            self.assertTrue(re.findall('1 time',
                                       outputs['trouble'], re.I))
            self.assertTrue(re.findall('raise NameError',
                                       outputs['trouble'], re.I))
            self.assertTrue(re.findall('7d @ 03:00',
                                       outputs['basic-job'], re.I))

    def test_configtest_ok(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.FooJob|3d\n'
          'socorro.unittest.cron.test_crontabber.BarJob|4d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            old_stderr = sys.stderr
            new_stderr = StringIO()
            sys.stderr = new_stderr
            old_stdout = sys.stdout
            new_stdout = StringIO()
            sys.stdout = new_stdout
            try:
                self.assertTrue(tab.configtest())
            finally:
                sys.stderr = old_stderr
                sys.stdout = old_stdout
            self.assertTrue(not new_stderr.getvalue())
            self.assertTrue(not new_stdout.getvalue())

    def test_configtest_not_found(self):
        self.assertRaises(
            crontabber.JobNotFoundError,
            self._setup_config_manager,
            'socorro.unittest.cron.test_crontabber.YYYYYY|3d'
        )

    def test_configtest_definition_error(self):
        self.assertRaises(
            crontabber.JobDescriptionError,
            self._setup_config_manager,
            'socorro.unittest.cron.test_crontabber.FooJob'
        )

    def test_configtest_bad_frequency(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.FooJob|3e'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            old_stderr = sys.stderr
            new_stderr = StringIO()
            sys.stderr = new_stderr
            try:
                self.assertTrue(not tab.configtest())
            finally:
                sys.stderr = old_stderr
            output = new_stderr.getvalue()
            self.assertTrue('FrequencyDefinitionError' in output)
            # twice per not found
            self.assertEqual(output.count('FrequencyDefinitionError'), 2)
            self.assertTrue('Error value: e' in output)

    def test_configtest_bad_time(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.FooJob|24:59\n'
          'socorro.unittest.cron.test_crontabber.BasicJob|23:60'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            old_stderr = sys.stderr
            new_stderr = StringIO()
            sys.stderr = new_stderr
            try:
                self.assertTrue(not tab.configtest())
            finally:
                sys.stderr = old_stderr
            output = new_stderr.getvalue()
            self.assertTrue('TimeDefinitionError' in output)
            # twice per not found
            self.assertEqual(output.count('TimeDefinitionError'), 2 + 2)
            self.assertTrue('24:59' in output)

    def test_configtest_bad_time_invariance(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.FooJob|3h|23:59'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            old_stderr = sys.stderr
            new_stderr = StringIO()
            sys.stderr = new_stderr
            try:
                self.assertTrue(not tab.configtest())
            finally:
                sys.stderr = old_stderr
            output = new_stderr.getvalue()
            self.assertTrue('FrequencyDefinitionError' in output)
            # twice per not found
            self.assertTrue(output.count('FrequencyDefinitionError'))
            self.assertTrue('23:59' in output)

    def test_execute_postgres_based_job(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.PostgresSampleJob|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            config.logger.info.assert_called_with('Ran PostgresSampleJob')

            self.psycopg2().cursor().execute.assert_any_call(
              'INSERT INTO test_cron_victim (time) VALUES (now())'
            )
            self.psycopg2().cursor().execute.assert_any_call(
              'COMMIT'
            )
            self.psycopg2().close.assert_called_with()

    def test_execute_postgres_transaction_managed_job(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.'
          'PostgresTransactionSampleJob|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            (config.logger.info
             .assert_called_with('Ran PostgresTransactionSampleJob'))
            _sql = 'INSERT INTO test_cron_victim (time) VALUES (now())'
            self.psycopg2().cursor().execute.assert_called_with(_sql)
            self.psycopg2().commit.assert_called_with()

    def test_execute_failing_postgres_based_job(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.BrokenPostgresSampleJob|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertTrue('Ran PostgresSampleJob' not in infos)

            self.assertTrue(self.psycopg2.called)
            self.psycopg2().close.assert_called_with()
            self.assertTrue(tab.database['broken-pg-job']['last_error'])
            self.assertTrue('ProgrammingError' in
                      tab.database['broken-pg-job']['last_error']['traceback'])

    def test_own_required_config_job(self):
        config_manager, json_file = self._setup_config_manager(
         'socorro.unittest.cron.test_crontabber.OwnRequiredConfigSampleJob|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertTrue(
              'Ran OwnRequiredConfigSampleJob(%r)' % 'bugz.mozilla.org'
              in infos
            )

    def test_own_required_config_job_overriding_config(self):
        config_manager, json_file = self._setup_config_manager(
         'socorro.unittest.cron.test_crontabber.OwnRequiredConfigSampleJob|1d',
          extra_value_source={
            'class-OwnRequiredConfigSampleJob.bugsy_url': 'bugs.peterbe.com'
          }
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertTrue(
              'Ran OwnRequiredConfigSampleJob(%r)' % 'bugs.peterbe.com'
              in infos
            )

    def test_automatic_backfill_basic_job(self):
        config_manager, json_file = self._setup_config_manager(
         'socorro.unittest.cron.test_crontabber.FooBackfillJob|1d'
        )

        def fmt(d):
            return d.split('.')[0]

        # first just run it as is
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            structure = json.load(open(json_file))
            information = structure['foo-backfill']
            self.assertEqual(information['first_run'], information['last_run'])

            # last_success might be a few microseconds off
            self.assertEqual(fmt(information['last_run']),
                             fmt(information['last_success']))
            self.assertTrue(not information['last_error'])

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertEqual(len(infos), 1)

            # now, pretend the last 2 days have failed
            interval = datetime.timedelta(days=2)
            tab.database['foo-backfill']['first_run'] = \
              tab.database['foo-backfill']['first_run'] - interval
            tab.database['foo-backfill']['last_success'] = \
              tab.database['foo-backfill']['last_success'] - interval
            tab.database.save(json_file)

            self._wind_clock(json_file, days=1)
            tab._database = None

            tab.run_all()

            previous_infos = infos
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            infos = [x for x in infos if x not in previous_infos]
            infos.sort()
            # last success was 2 days ago plus today
            assert len(infos) == 3

            today = utc_now()
            yesterday = today - datetime.timedelta(days=1)
            day_before_yesterday = today - datetime.timedelta(days=2)
            for each in (today, yesterday, day_before_yesterday):
                formatted = each.strftime('%Y-%m-%d')
                self.assertTrue([x for x in infos
                                 if formatted in x])

    def test_backfilling_failling_midway(self):
        """ this test simulates when you have something like this:

            Monday: Success
            Tuesday: Failure
            Wednesday: Failure
            Thursday: today!

        When encountering this on the Thursday it will run (in order):

            Tuesday, Wednesday, Thursday

        Suppose then that something goes wrong on the Wednesday.
        Then, if so, we don't want to run Tueday again and Thursday shouldn't
        even be attempted.
        """

        config_manager, json_file = self._setup_config_manager(
         'socorro.unittest.cron.test_crontabber.CertainDayHaterBackfillJob|1d'
        )
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            app_name = CertainDayHaterBackfillJob.app_name

            # now, pretend the last 2 days have failed
            interval = datetime.timedelta(days=2)
            tab.database[app_name]['first_run'] = \
              tab.database[app_name]['first_run'] - interval
            tab.database[app_name]['last_success'] = \
              tab.database[app_name]['last_success'] - interval
            tab.database.save(json_file)

            self._wind_clock(json_file, days=1)
            tab._database = None

            CertainDayHaterBackfillJob.fail_on = \
              tab.database[app_name]['first_run'] + interval

            first_last_success = tab.database[app_name]['last_success']
            tab.run_all()

            # now, we expect the new last_success to be 1 day more
            new_last_success = tab.database[app_name]['last_success']
            self.assertEqual((new_last_success - first_last_success).days, 1)

    def test_backfilling_postgres_based_job(self):
        config_manager, json_file = self._setup_config_manager(
         'socorro.unittest.cron.test_crontabber.PGBackfillJob|1d'
        )

        def fmt(d):
            return d.split('.')[0]

        # first just run it as is
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            structure = json.load(open(json_file))
            information = structure['pg-backfill']  # app_name of PGBackfillJob

            # Note, these are strings of dates
            self.assertEqual(information['first_run'], information['last_run'])

            # last_success might be a few microseconds off
            self.assertEqual(fmt(information['last_run']),
                             fmt(information['last_success']))
            self.assertTrue(not information['last_error'])

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertEqual(len(infos), 1)

            # now, pretend the last 2 days have failed
            interval = datetime.timedelta(days=2)
            tab.database['pg-backfill']['first_run'] = \
              tab.database['pg-backfill']['first_run'] - interval
            tab.database['pg-backfill']['last_success'] = \
              tab.database['pg-backfill']['last_success'] - interval
            tab.database.save(json_file)

            self._wind_clock(json_file, days=1)
            tab._database = None

            tab.run_all()
            previous_infos = infos
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            infos = [x for x in infos if x not in previous_infos]
            infos.sort()
            # last success was 2 days ago plus today
            assert len(infos) == 3

            today = utc_now()
            yesterday = today - datetime.timedelta(days=1)
            day_before_yesterday = today - datetime.timedelta(days=2)
            for each in (today, yesterday, day_before_yesterday):
                formatted = each.strftime('%Y-%m-%d')
                self.assertTrue([x for x in infos
                                 if formatted in x])


#==============================================================================
@attr(integration='postgres')  # for nosetests
class TestFunctionalCrontabber(_TestCaseBase):

    def setUp(self):
        super(TestFunctionalCrontabber, self).setUp()
        # prep a fake table
        assert 'test' in databaseName.default, databaseName.default
        dsn = ('host=%(database_host)s dbname=%(database_name)s '
               'user=%(database_user)s password=%(database_password)s' % DSN)
        self.conn = psycopg2.connect(dsn)
        cursor = self.conn.cursor()
        cursor.execute("""
        DROP TABLE IF EXISTS test_cron_victim;
        CREATE TABLE test_cron_victim (
          id serial primary key,
          time timestamp DEFAULT current_timestamp
        );
        """)
        self.conn.commit()
        assert self.conn.get_transaction_status() == TRANSACTION_STATUS_IDLE

    def tearDown(self):
        super(TestFunctionalCrontabber, self).tearDown()
        self.conn.cursor().execute("""
        DROP TABLE IF EXISTS test_cron_victim;
        """)
        self.conn.commit()

    def test_postgres_job(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.PostgresSampleJob|1d'
        )

        cur = self.conn.cursor()
        cur.execute('select * from test_cron_victim')
        self.assertTrue(not cur.fetchall())

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertTrue('Ran PostgresSampleJob' in infos)

            cur = self.conn.cursor()
            cur.execute('select * from test_cron_victim')
            self.assertTrue(cur.fetchall())

    def test_postgres_job_with_broken(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.BrokenPostgresSampleJob|1d\n'
          'socorro.unittest.cron.test_crontabber.PostgresSampleJob|1d'
        )

        cur = self.conn.cursor()
        cur.execute('select * from test_cron_victim')
        self.assertTrue(not cur.fetchall())

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertTrue('Ran PostgresSampleJob' in infos)

            cur = self.conn.cursor()
            cur.execute('select * from test_cron_victim')
            # Note! The BrokenPostgresSampleJob actually does an insert first
            # before it raises the ProgrammingError. The following test
            # makes sure to test that the rollback of the transaction works
            self.assertEqual(len(cur.fetchall()), 1)
            out = StringIO()
            tab.list_jobs(stream=out)
            output = out.getvalue()
            outputs = {}
            for block in re.split('={5,80}', output)[1:]:
                key = re.findall('App name:\s+([\w-]+)', block)[0]
                outputs[key] = block

            self.assertTrue('Error' in outputs['broken-pg-job'])
            self.assertTrue('ProgrammingError' in outputs['broken-pg-job'])
            self.assertTrue('Error' not in outputs['sample-pg-job'])

    def test_postgres_job_with_backfill_basic(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.PostgresBackfillSampleJob|1d'
        )

        cur = self.conn.cursor()
        cur.execute('select * from test_cron_victim')
        self.assertTrue(not cur.fetchall())

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertEqual(len(infos), 1)

            cur = self.conn.cursor()
            cur.execute('select * from test_cron_victim')
            self.assertTrue(cur.fetchall())

    def test_postgres_job_with_backfill_3_days_back(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.PostgresBackfillSampleJob|1d'
        )

        def fmt(d):
            wo_microseconds = d.split('.')[0]
            # because it has happened, it can happen again.
            # the number of microseconds between 'last_run' and 'last_success'
            # can be so many it rounds to a different second, so let's drop
            # the last second too
            return wo_microseconds[:-1]

        # first just run it as is
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            cur = self.conn.cursor()

            cur.execute('select count(*) from test_cron_victim')
            count, = cur.fetchall()[0]
            self.assertEqual(count, 1)

            structure = json.load(open(json_file))

            app_name = PostgresBackfillSampleJob.app_name
            information = structure[app_name]

            # Note, these are strings of dates
            self.assertEqual(information['first_run'], information['last_run'])

            # last_success might be a few microseconds off
            self.assertEqual(fmt(information['last_run']),
                             fmt(information['last_success']))
            self.assertTrue(not information['last_error'])

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertEqual(len(infos), 1)

            # now, pretend the last 2 days have failed
            interval = datetime.timedelta(days=2)
            tab.database[app_name]['first_run'] = \
              tab.database[app_name]['first_run'] - interval
            tab.database[app_name]['last_success'] = \
              tab.database[app_name]['last_success'] - interval
            tab.database.save(json_file)

            self._wind_clock(json_file, days=1)
            tab._database = None

            tab.run_all()
            previous_infos = infos
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            infos = [x for x in infos if x not in previous_infos]
            infos.sort()
            # last success was 2 days ago plus today
            assert len(infos) == 3

            cur.execute('select time from test_cron_victim')
            records = cur.fetchall()
            self.assertEqual(len(records), 4)

            today = utc_now()
            yesterday = today - datetime.timedelta(days=1)
            day_before_yesterday = today - datetime.timedelta(days=2)
            for each in (today, yesterday, day_before_yesterday):
                formatted = each.strftime('%Y-%m-%d')
                self.assertTrue([x for x in infos
                                 if formatted in x])


#==============================================================================
## Various mock jobs that the tests depend on
class _Job(crontabber.BaseCronApp):

    def run(self):
        assert self.app_name
        self.config.logger.info("Ran %s" % self.__class__.__name__)


class _PGJob(crontabber.PostgresCronApp, _Job):

    def run(self, connection):
        _Job.run(self)


class _PGTransactionManagedJob(crontabber.PostgresTransactionManagedCronApp,
                               _Job):

    def run(self, connection):
        _Job.run(self)


class BasicJob(_Job):
    app_name = 'basic-job'


class FooJob(_Job):
    app_name = 'foo'


class BarJob(_Job):
    app_name = 'bar'
    depends_on = 'foo'


class TroubleJob(_Job):
    app_name = 'trouble'

    def run(self):
        super(TroubleJob, self).run()
        raise NameError("Trouble!!")


class SadJob(_Job):
    app_name = 'sad'
    depends_on = 'trouble',  # <-- note: a tuple


class PostgresSampleJob(_PGJob):
    app_name = 'sample-pg-job'

    def run(self, connection):
        cursor = connection.cursor()
        cursor.execute('INSERT INTO test_cron_victim (time) VALUES (now())')
        # need this because this is not a TransactionManaged subclass
        cursor.execute('COMMIT')
        super(PostgresSampleJob, self).run(connection)


class PostgresTransactionSampleJob(_PGTransactionManagedJob):
    app_name = 'sample-transaction-pg-job'

    def run(self, connection):
        cursor = connection.cursor()
        cursor.execute('INSERT INTO test_cron_victim (time) VALUES (now())')
        super(PostgresTransactionSampleJob, self).run(connection)


class BrokenPostgresSampleJob(_PGJob):
    app_name = 'broken-pg-job'

    def run(self, connection):
        cursor = connection.cursor()
        cursor.execute('INSERT INTO test_cron_victim (time) VALUES (now())')
        raise psycopg2.ProgrammingError("shit!")


class OwnRequiredConfigSampleJob(_Job):
    app_name = 'bugsy'
    app_description = 'has its own config'

    required_config = Namespace()
    required_config.add_option(
        'bugsy_url',
        default='bugz.mozilla.org'
    )

    def run(self):
        self.config.logger.info("Ran %s(%r)" %
          (self.__class__.__name__, self.config.bugsy_url)
        )


class _BackfillJob(crontabber.BaseBackfillCronApp):

    def run(self, date):
        assert isinstance(date, datetime.datetime)
        assert self.app_name
        self.config.logger.info(
          "Ran %s(%s, %s)" % (self.__class__.__name__, date, id(date))
        )


class FooBackfillJob(_BackfillJob):
    app_name = 'foo-backfill'


class CertainDayHaterBackfillJob(_BackfillJob):
    app_name = 'certain-day-hater-backfill'

    fail_on = None

    def run(self, date):
        if (self.fail_on
             and date.strftime('%m%d') == self.fail_on.strftime('%m%d')):
            raise Exception("bad date!")


class PGBackfillJob(crontabber.PostgresBackfillCronApp):
    app_name = 'pg-backfill'

    def run(self, connection, date):
        assert isinstance(date, datetime.datetime)
        assert self.app_name
        # The reason for using `id(date)` is because of the way the tests
        # winds back the clock from the previous last_success
        # so that:
        #    2012-04-27 17:13:56.700184+00:00
        # becomes:
        #    2012-04-24 17:13:56.700184+00:00
        # And since the winding back in the test is "unnatural" the numbers
        # in the dates are actually the same but the instances are different
        self.config.logger.info(
          "Ran %s(%s, %r)" % (self.__class__.__name__, date, id(date))
        )


class PostgresBackfillSampleJob(crontabber.PostgresBackfillCronApp):
    app_name = 'sample-pg-job-backfill'

    def run(self, connection, date):
        cursor = connection.cursor()
        cursor.execute('INSERT INTO test_cron_victim (time) VALUES (%s)',
                       (date.strftime('%Y-%m-%d %H:%M:%S'),))
        # need this because this is not a TransactionManaged subclass
        cursor.execute('COMMIT')
        self.config.logger.info(
          "Ran %s(%s, %r)" % (self.__class__.__name__, date, id(date))
        )
