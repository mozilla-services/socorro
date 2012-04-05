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

class TestCaseWithTempDir(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.tempdir):
            shutil.rmtree(self.tempdir)

    def _setup_config_manager(self, jobs_string):
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
            }, DSN]
        )
        return config_manager, json_file


class TestJSONJobsDatabase(TestCaseWithTempDir):

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

        old_stderr = sys.stderr
        new_stderr = StringIO()
        sys.stderr = new_stderr
        try:
            self.assertRaises(ValueError, db.load, file1)
            output = new_stderr.getvalue()
            self.assertTrue(file1 in output)
            self.assertTrue('{Junk' in output)
        finally:
            sys.stderr = old_stderr


class TestCrontabber(TestCaseWithTempDir):

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

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            self.assertRaises(
                crontabber.JobNotFoundError,
                tab.run_one,
                'unheard-of-app-name'
            )
            tab.run_one('basic-job')
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            self.assertTrue('Ran BasicJob' in infos)

            # check that this was written to the JSON file
            # and that the next_run is going to be 1 day from now
            assert os.path.isfile(json_file)
            structure = json.load(open(json_file))
            information = structure['basic-job']
            self.assertEqual(information['error_count'], 0)
            self.assertEqual(information['last_error'], {})
            today = datetime.datetime.now()
            one_week = today + datetime.timedelta(days=7)
            self.assertTrue(today.strftime('%Y-%m-%d')
                            in information['last_run'])
            self.assertTrue(today.strftime('%H:%M:%S')
                            in information['last_run'])
            self.assertTrue(one_week.strftime('%Y-%m-%d')
                            in information['next_run'])

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
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.YYYYYY|3d\n'
          'socorro.unittest.cron.test_crontabber.XXXXXX|4d'
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
            self.assertTrue('JobNotFoundError' in output)
            # twice per not found
            self.assertEqual(output.count('JobNotFoundError'), 4)
            self.assertTrue('XXXXXX' in output)
            self.assertTrue('YYYYYY' in output)

    def test_configtest_definition_error(self):
        config_manager, json_file = self._setup_config_manager(
          # missing frequency or time
          'socorro.unittest.cron.test_crontabber.FooJob'
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
            self.assertTrue('JobDescriptionError' in output)
            # twice per not found
            self.assertEqual(output.count('JobDescriptionError'), 2)
            self.assertTrue('test_crontabber.FooJob' in output)

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
          'socorro.unittest.cron.test_crontabber.FooJob|24:59'
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
            self.assertEqual(output.count('TimeDefinitionError'), 2)
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
            self.assertEqual(output.count('FrequencyDefinitionError'), 2)
            self.assertTrue('23:59' in output)

    def test_execute_postgres_based_job(self):
        config_manager, json_file = self._setup_config_manager(
          'socorro.unittest.cron.test_crontabber.PostgresSampleJob|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertTrue('Ran PostgresSampleJob' in infos)
            self.assertTrue(self.psycopg2.called)

            calls = self.psycopg2.mock_calls
            self.assertEqual(calls[1], mock.call().cursor())
            self.assertEqual(calls[2],  mock.call().cursor()
              .execute('INSERT INTO test_cron_victim (time) VALUES (now())'))
            self.assertEqual(calls[3], mock.call().commit())
            self.assertEqual(calls[4], mock.call().close())

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
            calls = self.psycopg2.mock_calls
            self.assertEqual(calls[-1], mock.call().close())

            self.assertTrue(tab.database['broken-pg-job']['last_error'])
            self.assertTrue('ProgrammingError' in
                      tab.database['broken-pg-job']['last_error']['traceback'])


class TestFunctionalCrontabber(TestCaseWithTempDir):

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


## Various mock jobs that the tests depend on
class _Job(crontabber.BaseCronApp):

    def run(self):
        assert self.app_name
        self.config.logger.info("Ran %s" % self.__class__.__name__)


class _PGJob(crontabber.PostgreSQLCronApp, _Job):

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
        super(PostgresSampleJob, self).run(connection)


class BrokenPostgresSampleJob(_PGJob):
    app_name = 'broken-pg-job'

    def run(self, connection):
        import psycopg2
        raise psycopg2.ProgrammingError("shit!")
