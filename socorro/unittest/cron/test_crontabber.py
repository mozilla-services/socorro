# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import sys
import datetime
import os
import json
import time
import unittest
from cStringIO import StringIO
import mock
import psycopg2
from psycopg2.extensions import TRANSACTION_STATUS_IDLE
from nose.plugins.attrib import attr
from socorro.cron import crontabber
from socorro.cron import base
from socorro.lib.datetimeutil import utc_now, UTC
from configman import Namespace
from .base import DSN, TestCaseBase


#==============================================================================
class _Item(object):

    def __init__(self, name, depends_on):
        self.app_name = name
        self.depends_on = depends_on


class TestReordering(unittest.TestCase):

    def test_basic_already_right(self):
        sequence = [
            _Item('A', []),
            _Item('B', ['A']),
            _Item('C', ['B']),
        ]
        new_sequence = base.reorder_dag(sequence)
        new_names = [x.app_name for x in new_sequence]
        self.assertEqual(new_names, ['A', 'B', 'C'])

    def test_three_levels(self):
        sequence = [
            _Item('A', []),
            _Item('B', ['A']),
            _Item('D', ['B', 'C']),
            _Item('C', ['B']),

        ]
        new_sequence = base.reorder_dag(sequence)
        new_names = [x.app_name for x in new_sequence]
        self.assertEqual(new_names, ['A', 'B', 'C', 'D'])

    def test_basic_completely_reversed(self):
        sequence = [
            _Item('C', ['B']),
            _Item('B', ['A']),
            _Item('A', []),
        ]
        new_sequence = base.reorder_dag(sequence)
        new_names = [x.app_name for x in new_sequence]
        self.assertEqual(new_names, ['A', 'B', 'C'])

    def test_basic_sloppy_depends_on(self):
        sequence = [
            _Item('C', ('B',)),
            _Item('B', 'A'),
            _Item('A', None),
        ]
        new_sequence = base.reorder_dag(sequence)
        new_names = [x.app_name for x in new_sequence]
        self.assertEqual(new_names, ['A', 'B', 'C'])

    def test_two_trees(self):
        sequence = [
            _Item('C', ['B']),
            _Item('B', ['A']),
            _Item('A', []),
            _Item('X', ['Y']),
            _Item('Y', []),
        ]
        new_sequence = base.reorder_dag(sequence)
        new_names = [x.app_name for x in new_sequence]
        self.assertTrue(
            new_names.index('A')
            <
            new_names.index('B')
            <
            new_names.index('C')
        )
        self.assertTrue(
            new_names.index('Y')
            <
            new_names.index('X')
        )

    def test_circular_no_roots(self):
        sequence = [
            _Item('C', ['B']),
            _Item('B', ['A']),
            _Item('A', ['C']),
        ]
        self.assertRaises(
            base.CircularDAGError,
            base.reorder_dag,
            sequence
        )

    def test_circular_one_root_still_circular(self):
        sequence = [
            _Item('C', ['B']),
            _Item('X', ['Y']),
            _Item('Y', []),
            _Item('B', ['A']),
            _Item('A', ['C']),
        ]
        self.assertRaises(
            base.CircularDAGError,
            base.reorder_dag,
            sequence
        )


#==============================================================================
class TestJSONJobsDatabase(TestCaseBase):
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
        self.assertEqual(
            structure,
            {u'foo': 1, u'more': {u'bar': u'Bar'}}
        )

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
class TestCrontabber(TestCaseBase):

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
            self.assertTrue(today.strftime('%H:%M')
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

    @mock.patch('time.sleep')
    @mock.patch('socorro.cron.crontabber.utc_now')
    def test_slow_run_job(self, mocked_utc_now, time_sleep):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.SlowJob|1h'
        )

        _sleeps = []

        def mocked_sleep(seconds):
            _sleeps.append(seconds)

        def mock_utc_now():
            n = utc_now()
            for e in _sleeps:
                n += datetime.timedelta(seconds=e)
            return n

        mocked_utc_now.side_effect = mock_utc_now
        time_sleep.side_effect = mocked_sleep

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)

            time_before = crontabber.utc_now()
            _timestamp_before = time.time()
            tab.run_all()
            time_after = crontabber.utc_now()
            _timestamp_after = time.time()
            time_taken = (time_after - time_before).seconds
            self.assertEqual(round(time_taken), 1.0)

            # check that this was written to the JSON file
            # and that the next_run is going to be 1 day from now
            assert os.path.isfile(json_file)
            structure = json.load(open(json_file))
            information = structure['slow-job']
            self.assertEqual(information['error_count'], 0)
            self.assertEqual(information['last_error'], {})
            # `time.sleep` is mocked but we can't assume that `tab.run_all()`
            # takes no time. On a slow computer (e.g. jenkins) it can be such
            # significant delay that the time after is different from the time
            # before when you round it to the nearest second.
            # Adding this `_slowness_delay` takes that delay into account
            _slowness_delay = _timestamp_after - _timestamp_before

            # convert `information['next_run']` into a datetime.datetime object
            next_run = datetime.datetime.strptime(
                information['next_run'],
                '%Y-%m-%d %H:%M:%S.%f'
            )
            next_run = next_run.replace(tzinfo=UTC)
            # and then to a floating point number
            next_run_ts = time.mktime(next_run.timetuple())

            # do the same with the expected next_run
            expect_next_run = (
                time_before +
                datetime.timedelta(hours=1) +
                datetime.timedelta(seconds=_slowness_delay)
            )
            expect_next_run = expect_next_run.replace(tzinfo=UTC)
            expect_next_run_ts = time.mktime(expect_next_run.timetuple())
            # rounded, we expect these to be the same
            self.assertEqual(round(next_run_ts), round(expect_next_run_ts))

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
            self.assertTrue(today.strftime('%H:%M')
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
            'socorro.unittest.cron.test_crontabber.BasicJob|1d\n'
            'socorro.unittest.cron.test_crontabber.FooJob|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            self.assertEqual(
                infos,
                ['Ran BasicJob', 'Ran TroubleJob', 'Ran FooJob']
            )
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
            self.assertRaises(
                base.CircularDAGError,
                tab.run_all
            )

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
            self.assertEqual(
                infos,
                ['Ran FooJob', 'Ran BarJob', 'Ran FooJob', 'Ran BarJob']
            )

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

    def test_depends_on_recorded_in_state(self):
        # set up a couple of jobs that depend on each other
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.FooJob|1d\n'
            'socorro.unittest.cron.test_crontabber.BarJob|1d\n'
            'socorro.unittest.cron.test_crontabber.FooBarJob|1d'
        )
        # the BarJob one depends on FooJob but suppose that FooJob
        # has run for but a very long time ago
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            structure = json.load(open(json_file))
            assert 'foo' in structure
            assert 'bar' in structure
            assert 'foobar' in structure

            self.assertEqual(structure['foo']['depends_on'], [])
            self.assertEqual(structure['bar']['depends_on'], ['foo'])
            self.assertEqual(structure['foobar']['depends_on'], ['foo', 'bar'])

    @mock.patch('socorro.cron.crontabber.utc_now')
    def test_basic_run_job_with_hour(self, mocked_utc_now):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BasicJob|7d|03:00\n'
            'socorro.unittest.cron.test_crontabber.FooJob|1:45'
        )

        # Pretend it's 04:00 UTC
        def mock_utc_now():
            n = utc_now()
            return n.replace(hour=4, minute=0)

        mocked_utc_now.side_effect = mock_utc_now

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]

            assert os.path.isfile(json_file)
            structure = json.load(open(json_file))
            assert 'basic-job' in structure
            next_run = structure['basic-job']['next_run']
            self.assertTrue('03:00:00' in next_run)
            assert 'foo' in structure
            next_run = structure['foo']['next_run']
            self.assertTrue('01:45:00' in next_run)

    @mock.patch('socorro.cron.crontabber.utc_now')
    def test_list_jobs(self, mocked_utc_now):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.SadJob|5h\n'
            'socorro.unittest.cron.test_crontabber.TroubleJob|1d\n'
            'socorro.unittest.cron.test_crontabber.BasicJob|7d|03:00\n'
            'socorro.unittest.cron.test_crontabber.FooJob|2d'
        )

        # Pretend it's 04:00 UTC
        def mock_utc_now():
            n = utc_now()
            return n.replace(hour=4)

        mocked_utc_now.side_effect = mock_utc_now

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
            self.assertEqual(
                4,
                len(re.findall('App name:\s+(trouble|basic-job|foo|sad)',
                               output, re.I))
            )
            self.assertEqual(
                4,
                len(re.findall('No previous run info', output, re.I))
            )

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
            self.assertEqual(
                1,
                len(re.findall('No previous run info', output, re.I))
            )

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
            # since the exception type and exception value is also displayed
            # in the output we can expect these to be shown twice
            self.assertEqual(outputs['trouble'].count('NameError'), 2)
            self.assertEqual(outputs['trouble'].count('Trouble!!'), 2)
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

    @mock.patch('socorro.cron.crontabber.utc_now')
    @mock.patch('socorro.cron.base.utc_now')
    def test_basic_job_at_specific_hour(self, mocked_utc_now, mocked_utc_now_2):
        # let's pretend the clock is 09:00 and try to run this
        # the first time, then nothing should happen
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.FooJob|1d|10:00'
        )

        # Pretend it's 09:00 UTC
        def mock_utc_now():
            n = utc_now()
            return n.replace(hour=9, minute=0)

        mocked_utc_now.side_effect = mock_utc_now
        mocked_utc_now_2.side_effect = mock_utc_now

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            # if it never ran, no json_file would have been created
            self.assertTrue(not os.path.isfile(json_file))

        # Pretend it's now 10:30 UTC
        def mock_utc_now_2():
            n = utc_now()
            return n.replace(hour=10, minute=30)

        mocked_utc_now.side_effect = mock_utc_now_2
        mocked_utc_now_2.side_effect = mock_utc_now_2

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            self.assertTrue(os.path.isfile(json_file))
            structure = json.load(open(json_file))
            information = structure['foo']
            self.assertTrue('10:30' in information['first_run'])
            self.assertTrue('10:30' in information['last_run'])
            self.assertTrue('10:30' in information['last_success'])
            self.assertTrue('10:00' in information['next_run'])

        # Pretend it's now 1 day later
        def mock_utc_now_3():
            n = utc_now()
            n = n.replace(hour=10, minute=30)
            return n + datetime.timedelta(days=1)

        mocked_utc_now.side_effect = mock_utc_now_3
        mocked_utc_now_2.side_effect = mock_utc_now_3

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            self.assertTrue(os.path.isfile(json_file))
            structure = json.load(open(json_file))
            information = structure['foo']
            assert not information['last_error']
            self.assertTrue('10:30' in information['first_run'])
            self.assertTrue('10:30' in information['last_run'])
            self.assertTrue('10:30' in information['last_success'])
            self.assertTrue('10:00' in information['next_run'])

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            assert len(infos) == 2, infos

    @mock.patch('socorro.cron.crontabber.utc_now')
    @mock.patch('socorro.cron.base.utc_now')
    def test_backfill_job_at_specific_hour(self, mocked_utc_now, mocked_utc_now_2):
        # let's pretend the clock is 09:00 and try to run this
        # the first time, then nothing should happen
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.FooBackfillJob|1d|10:00'
        )

        # Pretend it's 09:00 UTC
        def mock_utc_now():
            n = utc_now()
            return n.replace(hour=9, minute=0)

        mocked_utc_now.side_effect = mock_utc_now
        mocked_utc_now_2.side_effect = mock_utc_now

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            # if it never ran, no json_file would have been created
            self.assertTrue(not os.path.isfile(json_file))

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            assert len(infos) == 0, infos

        # Pretend it's now 10:30 UTC
        def mock_utc_now_2():
            n = utc_now()
            return n.replace(hour=10, minute=30)

        mocked_utc_now.side_effect = mock_utc_now_2
        mocked_utc_now_2.side_effect = mock_utc_now_2

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            self.assertTrue(os.path.isfile(json_file))
            structure = json.load(open(json_file))
            information = structure['foo-backfill']
            assert not information['last_error']
            self.assertTrue('10:30' in information['first_run'])
            self.assertTrue('10:30' in information['last_run'])
            self.assertTrue('10:30' in information['last_success'])

            self.assertTrue('10:00' in information['next_run'])

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            assert len(infos) == 1, infos

        # Pretend it's now 1 day later
        def mock_utc_now_3():
            n = utc_now()
            n = n.replace(hour=10, minute=30)
            return n + datetime.timedelta(days=1)

        mocked_utc_now.side_effect = mock_utc_now_3
        mocked_utc_now_2.side_effect = mock_utc_now_3

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            self.assertTrue(os.path.isfile(json_file))
            structure = json.load(open(json_file))
            information = structure['foo-backfill']
            assert not information['last_error']
            self.assertTrue('10:30' in information['first_run'])
            self.assertTrue('10:30' in information['last_run'])
            self.assertTrue('10:00' in information['last_success'])
            self.assertTrue('10:00' in information['next_run'])

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            assert len(infos) == 2, infos

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
            self.psycopg2().cursor().execute.assert_any_call(_sql)
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
            self.assertTrue(
                'ProgrammingError' in
                tab.database['broken-pg-job']['last_error']['traceback']
            )

    def test_own_required_config_job(self):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber'
            '.OwnRequiredConfigSampleJob|1d'
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
            'socorro.unittest.cron.test_crontabber'
            '.OwnRequiredConfigSampleJob|1d',
            extra_value_source={
                'crontabber.class-OwnRequiredConfigSampleJob.bugsy_url':
                'bugs.peterbe.com'
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
            tab.database['foo-backfill']['first_run'] = (
                tab.database['foo-backfill']['first_run'] - interval
            )
            tab.database['foo-backfill']['last_success'] = (
                tab.database['foo-backfill']['last_success'] - interval
            )
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
            'socorro.unittest.cron.test_crontabber'
            '.CertainDayHaterBackfillJob|1d'
        )
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            app_name = CertainDayHaterBackfillJob.app_name

            # now, pretend the last 2 days have failed
            interval = datetime.timedelta(days=2)
            tab.database[app_name]['first_run'] = (
                tab.database[app_name]['first_run'] - interval
            )
            tab.database[app_name]['last_success'] = (
                tab.database[app_name]['last_success'] - interval
            )
            tab.database.save(json_file)

            self._wind_clock(json_file, days=1)
            tab._database = None

            CertainDayHaterBackfillJob.fail_on = (
                tab.database[app_name]['first_run'] + interval
            )

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
            tab.database['pg-backfill']['first_run'] = (
                tab.database['pg-backfill']['first_run'] - interval
            )
            tab.database['pg-backfill']['last_success'] = (
                tab.database['pg-backfill']['last_success'] - interval
            )
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

    def test_run_with_excess_whitespace(self):
        # this test asserts a found bug where excess newlines
        # caused configuration exceptions
        config_manager, json_file = self._setup_config_manager(
            '\n \n'
            ' socorro.unittest.cron.test_crontabber.BasicJob|7d\n\t  \n'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            structure = json.load(open(json_file))
            information = structure['basic-job']
            self.assertTrue(information['last_success'])
            self.assertTrue(not information['last_error'])

    def test_commented_out_jobs_from_option(self):
        config_manager, json_file = self._setup_config_manager('''
          socorro.unittest.cron.test_crontabber.FooJob|3d
        #  socorro.unittest.cron.test_crontabber.BarJob|4d
        ''')

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            structure = json.load(open(json_file))
            self.assertTrue('foo' in structure)
            self.assertTrue('bar' not in structure)
            self.assertEqual(structure.keys(), ['foo'])

    # the reason we need to mock both is because both
    # socorro.cron.crontabber and socorro.cron.base imports utc_now
    @mock.patch('socorro.cron.crontabber.utc_now')
    @mock.patch('socorro.cron.base.utc_now')
    @mock.patch('time.sleep')
    def test_backfilling_with_configured_time_slow_job(self,
                                                       time_sleep,
                                                       mocked_utc_now,
                                                       mocked_utc_now_2):
        """ see https://bugzilla.mozilla.org/show_bug.cgi?id=781010

        What we're simulating here is that the time when we get around to
        run this particular job is variable.
        It's configured to run at 18:00 but the first time it doesn't get
        around to running it until 18:02:00.

        For example, crontabber kicks in at 18:00:00 but it takes 2 minutes
        to run something before this job.

        The next day, the jobs before this one only takes 1 minute which means
        we get around to this job at 18:01:00 instead. If that's the case
        it should correct the hour/minute part so that the backfilling doesn't
        think 24 hours hasn't gone since the last time. Phew!
        """
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.SlowBackfillJob|1d|18:00'
        )
        SlowBackfillJob.times_used = []

        _extra_time = []

        def mocked_sleep(seconds):
            _extra_time.append(datetime.timedelta(seconds=seconds))

        now_time = utc_now()
        now_time = now_time.replace(hour=18, minute=2, second=0)

        def mock_utc_now():
            n = now_time
            for e in _extra_time:
                n += e
            return n

        time_sleep.side_effect = mocked_sleep
        mocked_utc_now.side_effect = mock_utc_now
        mocked_utc_now_2.side_effect = mock_utc_now

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            assert len(SlowBackfillJob.times_used) == 1
            _dates_used = [x.strftime('%d')
                           for x in SlowBackfillJob.times_used]
            assert len(set(_dates_used)) == 1

            structure = json.load(open(json_file))
            information = structure['slow-backfill']
            self.assertTrue('18:00:00' in information['next_run'])
            self.assertTrue('18:02:00' in information['first_run'])
            self.assertTrue('18:02:00' in information['last_run'])
            self.assertTrue('18:02:00' in information['last_success'])

            self.assertEqual(
                crontabber.utc_now().strftime('%H:%M:%S'),
                '18:02:01'
            )

        # a day goes by...
        _extra_time.append(datetime.timedelta(days=1))
        # but this time, the crontab wakes up a minute earlier
        now_time = now_time.replace(minute=1)

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            assert len(SlowBackfillJob.times_used) == 2
            _dates_used = [x.strftime('%d')
                           for x in SlowBackfillJob.times_used]
            assert len(set(_dates_used)) == 2

            structure = json.load(open(json_file))
            information = structure['slow-backfill']
            self.assertTrue('18:00:00' in information['next_run'])
            self.assertTrue('18:01:01' in information['last_run'])
            self.assertTrue('18:00:00' in information['last_success'])

    @mock.patch('socorro.cron.crontabber.utc_now')
    @mock.patch('socorro.cron.base.utc_now')
    @mock.patch('time.sleep')
    def test_slow_backfilled_timed_daily_job(self, time_sleep,
                                             mocked_utc_now, mocked_utc_now_2):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.SlowBackfillJob|1d|10:00'
        )

        SlowBackfillJob.times_used = []

        _extra_time = []

        def mocked_sleep(seconds):
            _extra_time.append(datetime.timedelta(seconds=seconds))

        # pretend it's 11AM UTC
        def mock_utc_now():
            n = utc_now()
            n = n.replace(hour=11)
            for e in _extra_time:
                n += e
            return n

        time_sleep.side_effect = mocked_sleep
        mocked_utc_now.side_effect = mock_utc_now
        mocked_utc_now_2.side_effect = mock_utc_now

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            time_before = crontabber.utc_now()
            tab.run_all()
            self.assertEqual(len(SlowBackfillJob.times_used), 1)
            time_after = crontabber.utc_now()
            # double-checking
            assert (time_after - time_before).seconds == 1

            structure = json.load(open(json_file))
            information = structure['slow-backfill']
            self.assertTrue(information['last_success'])
            self.assertTrue(not information['last_error'])
            # easy
            self.assertTrue('10:00:00' in information['next_run'])
            self.assertEqual(information['first_run'], information['last_run'])

            # pretend one day passes
            _extra_time.append(datetime.timedelta(days=1))
            time_later = crontabber.utc_now()
            assert (time_later - time_after).days == 1
            assert (time_later - time_after).seconds == 0
            assert (time_later - time_before).days == 1
            assert (time_later - time_before).seconds == 1

            tab.run_all()
            self.assertEqual(len(SlowBackfillJob.times_used), 2)
            structure = json.load(open(json_file))
            information = structure['slow-backfill']

            # another day passes
            _extra_time.append(datetime.timedelta(days=1))
            # also, simulate that it starts a second earlier this time
            _extra_time.append(-datetime.timedelta(seconds=1))
            tab.run_all()
            assert len(SlowBackfillJob.times_used) == 3
            structure = json.load(open(json_file))
            information = structure['slow-backfill']

    @mock.patch('socorro.cron.base.utc_now')
    @mock.patch('socorro.cron.crontabber.utc_now')
    @mock.patch('time.sleep')
    def test_slow_backfilled_timed_daily_job_first_failure(self,
                                                           time_sleep,
                                                           mocked_utc_now,
                                                           mocked_utc_now_2):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.SlowBackfillJob|1d|10:00'
        )

        SlowBackfillJob.times_used = []

        _extra_time = []

        def mocked_sleep(seconds):
            _extra_time.append(datetime.timedelta(seconds=seconds))

        # pretend it's 11AM UTC
        def mock_utc_now():
            n = utc_now()
            n = n.replace(hour=11)
            for e in _extra_time:
                n += e
            return n

        time_sleep.side_effect = mocked_sleep
        mocked_utc_now.side_effect = mock_utc_now
        mocked_utc_now_2.side_effect = mock_utc_now

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            self.assertEqual(len(SlowBackfillJob.times_used), 1)

            db = crontabber.JSONJobDatabase()
            db.load(json_file)
            del db['slow-backfill']['last_success']
            db.save(json_file)

        _extra_time.append(datetime.timedelta(days=1))
        _extra_time.append(-datetime.timedelta(seconds=1))

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            self.assertEqual(len(SlowBackfillJob.times_used), 2)

    def test_reset_job(self):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BasicJob|1d\n'
            'socorro.unittest.cron.test_crontabber.FooJob|1d'
        )
        BasicJob.times_used = []
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            self.assertRaises(
                crontabber.JobNotFoundError,
                tab.reset_job,
                'never-heard-of'
            )

            tab.reset_job('basic-job')
            config.logger.warning.assert_called_with('App already reset')

            # run them
            tab.run_all()
            self.assertEqual(len(BasicJob.times_used), 1)
            db = crontabber.JSONJobDatabase()
            db.load(json_file)
            assert 'basic-job' in db

            tab.reset_job('basic-job')
            config.logger.info.assert_called_with('App reset')
            db = crontabber.JSONJobDatabase()
            db.load(json_file)
            self.assertTrue('basic-job' not in db)

    def test_nagios_ok(self):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BasicJob|1d\n'
            'socorro.unittest.cron.test_crontabber.FooJob|1d'
        )
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            stream = StringIO()
            exit_code = tab.nagios(stream=stream)
            self.assertEqual(exit_code, 0)
            self.assertEqual(stream.getvalue(), '')

    def test_nagios_warning(self):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BasicJob|1d\n'
            'socorro.unittest.cron.test_crontabber.BackfillbasedTrouble|1d'
        )
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            stream = StringIO()
            exit_code = tab.nagios(stream=stream)
            self.assertEqual(exit_code, 1)
            output = stream.getvalue()
            self.assertTrue('WARNING' in output)
            self.assertTrue('backfill-trouble' in output)
            self.assertTrue('BackfillbasedTrouble' in output)
            self.assertTrue('NameError' in output)
            self.assertTrue('bla bla' in output)

            # run it a second time
            # wind the clock forward
            self._wind_clock(json_file, days=1)

            # this forces in crontabber instance to reload the JSON file
            tab._database = None

            tab.run_all()
            stream = StringIO()
            exit_code = tab.nagios(stream=stream)
            self.assertEqual(exit_code, 2)
            output = stream.getvalue()
            self.assertTrue('CRITICAL' in output)
            self.assertTrue('backfill-trouble' in output)
            self.assertTrue('BackfillbasedTrouble' in output)
            self.assertTrue('NameError' in output)
            self.assertTrue('bla bla' in output)

    def test_nagios_critical(self):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BasicJob|1d\n'
            'socorro.unittest.cron.test_crontabber.TroubleJob|1d'
        )
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            stream = StringIO()
            exit_code = tab.nagios(stream=stream)
            self.assertEqual(exit_code, 2)
            output = stream.getvalue()
            self.assertTrue('CRITICAL' in output)
            self.assertTrue('trouble' in output)
            self.assertTrue('TroubleJob' in output)
            self.assertTrue('NameError' in output)
            self.assertTrue('Trouble!!' in output)

    def test_reorder_dag_on_joblist(self):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.FooBarJob|1d\n'
            'socorro.unittest.cron.test_crontabber.BarJob|1d\n'
            'socorro.unittest.cron.test_crontabber.FooJob|1d'
        )
        # looking at the dependencies, since FooJob doesn't depend on anything
        # it should be run first, then BarJob and lastly FooBarJob because
        # FooBarJob depends on FooJob and BarJob.
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            structure = json.load(open(json_file))
            self.assertTrue('foo' in structure)
            self.assertTrue('bar' in structure)
            self.assertTrue('foobar' in structure)
            self.assertTrue(
                structure['foo']['last_run']
                <
                structure['bar']['last_run']
                <
                structure['foobar']['last_run']
            )


#==============================================================================
@attr(integration='postgres')  # for nosetests
class TestFunctionalCrontabber(TestCaseBase):

    def setUp(self):
        super(TestFunctionalCrontabber, self).setUp()
        # prep a fake table
        assert 'test' in DSN['database.database_name']
        dsn = ('host=%(database.database_host)s '
               'dbname=%(database.database_name)s '
               'user=%(database.database_user)s '
               'password=%(database.database_password)s' % DSN)
        self.conn = psycopg2.connect(dsn)
        cursor = self.conn.cursor()
        # double-check there is a crontabber_state row
        cursor.execute('select 1 from crontabber_state')
        if not cursor.fetchone():
            cursor.execute("""
            insert into crontabber_state (state, last_updated)
            values ('{}', now())
            """)
        cursor.execute("""
        DROP TABLE IF EXISTS test_cron_victim;
        CREATE TABLE test_cron_victim (
          id serial primary key,
          time timestamp DEFAULT current_timestamp
        );

        UPDATE crontabber_state SET state = '{}';
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

        cur.execute('select state from crontabber_state')
        state, = cur.fetchone()
        assert state
        information = json.loads(state)
        assert information['sample-pg-job']
        self.assertTrue(information['sample-pg-job']['next_run'])
        self.assertTrue(information['sample-pg-job']['last_run'])
        self.assertTrue(information['sample-pg-job']['first_run'])
        self.assertTrue(not information['sample-pg-job'].get('last_error'))

    def test_postgres_job_with_state_loaded_from_postgres_first(self):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.PostgresSampleJob|1d'
        )

        cur = self.conn.cursor()
        tomorrow = utc_now() + datetime.timedelta(days=1)
        information = {
            'sample-pg-job': {
                'next_run': tomorrow.strftime(
                    crontabber.JSONJobDatabase._date_fmt
                ),
            }
        }
        information_json = json.dumps(information)
        cur.execute('update crontabber_state set state=%s',
                    (information_json,))
        self.conn.commit()

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            # Note the 'NOT' in this test:
            self.assertTrue('Ran PostgresSampleJob' not in infos)

    def test_postgres_job_with_broken(self):
        config_manager, json_file = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber'
            '.BrokenPostgresSampleJob|1d\n'
            'socorro.unittest.cron.test_crontabber'
            '.PostgresSampleJob|1d'
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
            'socorro.unittest.cron.test_crontabber'
            '.PostgresBackfillSampleJob|1d'
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
            'socorro.unittest.cron.test_crontabber'
            '.PostgresBackfillSampleJob|1d'
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
            tab.database[app_name]['first_run'] = (
                tab.database[app_name]['first_run'] - interval
            )
            tab.database[app_name]['last_success'] = (
                tab.database[app_name]['last_success'] - interval
            )
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
class _Job(base.BaseCronApp):

    def run(self):
        assert self.app_name
        self.config.logger.info("Ran %s" % self.__class__.__name__)


class _PGJob(base.PostgresCronApp, _Job):

    def run(self, connection):
        _Job.run(self)


class _PGTransactionManagedJob(base.PostgresTransactionManagedCronApp,
                               _Job):

    def run(self, connection):
        _Job.run(self)


class BasicJob(_Job):
    app_name = 'basic-job'
    times_used = []

    def run(self):
        self.times_used.append(1)
        super(BasicJob, self).run()


class FooJob(_Job):
    app_name = 'foo'


class BarJob(_Job):
    app_name = 'bar'
    depends_on = 'foo'


class FooBarJob(_Job):
    app_name = 'foobar'
    depends_on = ('foo', 'bar')


class SlowJob(_Job):
    # an app that takes a whole second to run
    app_name = 'slow-job'

    def run(self):
        time.sleep(1)  # time.sleep() is a mock function by the way
        super(SlowJob, self).run()


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
        self.config.logger.info(
            "Ran %s(%r)" % (self.__class__.__name__, self.config.bugsy_url)
        )


class _BackfillJob(base.BaseBackfillCronApp):

    def run(self, date):
        assert isinstance(date, datetime.datetime)
        assert self.app_name
        self.config.logger.info(
            "Ran %s(%s, %s)" % (self.__class__.__name__, date, id(date))
        )


class FooBackfillJob(_BackfillJob):
    app_name = 'foo-backfill'


class BackfillbasedTrouble(_BackfillJob):
    app_name = 'backfill-trouble'

    def run(self, date):
        raise NameError('bla bla')


class CertainDayHaterBackfillJob(_BackfillJob):
    app_name = 'certain-day-hater-backfill'

    fail_on = None

    def run(self, date):
        if (self.fail_on
            and date.strftime('%m%d') == self.fail_on.strftime('%m%d')):
            raise Exception("bad date!")


class SlowBackfillJob(_BackfillJob):
    app_name = 'slow-backfill'

    times_used = []

    def run(self, date):
        self.times_used.append(date)
        time.sleep(1)
        super(SlowBackfillJob, self).run(date)


class PGBackfillJob(base.PostgresBackfillCronApp):
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


class PostgresBackfillSampleJob(base.PostgresBackfillCronApp):
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
