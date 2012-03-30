import datetime
import shutil
import os
import json
import unittest
import tempfile
import mock
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


class TestJSONJobsDatabase(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.isdir(self.tempdir):
            shutil.rmtree(self.tempdir)

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
        import sys
        file1 = os.path.join(self.tempdir, 'file1.json')
        with open(file1, 'w') as f:
            f.write('{Junk\n')
        db = crontabber.JSONJobDatabase()

        from cStringIO import StringIO
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


class TestCrontabber(unittest.TestCase):

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
            }]
        )
        return config_manager, json_file

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
            today = datetime.datetime.utcnow()
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


## Various mock jobs that the tests depend on

class _Job(crontabber.BaseCronApp):

    def run(self):
        assert self.app_name
        self.config.logger.info("Ran %s" % self.__class__.__name__)


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
