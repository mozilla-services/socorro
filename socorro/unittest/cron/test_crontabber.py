# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import sys
import datetime
import time
import unittest
import collections
from cStringIO import StringIO

import mock
import psycopg2
from nose.plugins.attrib import attr
from nose.tools import eq_, ok_, assert_raises

from socorro.cron import crontabber
from socorro.cron import base
from socorro.lib.datetimeutil import utc_now
from configman import Namespace, ConfigurationManager
from .base import DSN, IntegrationTestCaseBase
from socorro.cron.mixins import (
    as_backfill_cron_app,
    with_postgres_transactions,
    with_postgres_connection_as_argument,
    with_single_postgres_transaction
)


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
        eq_(new_names, ['A', 'B', 'C'])

    def test_three_levels(self):
        sequence = [
            _Item('A', []),
            _Item('B', ['A']),
            _Item('D', ['B', 'C']),
            _Item('C', ['B']),

        ]
        new_sequence = base.reorder_dag(sequence)
        new_names = [x.app_name for x in new_sequence]
        eq_(new_names, ['A', 'B', 'C', 'D'])

    def test_basic_completely_reversed(self):
        sequence = [
            _Item('C', ['B']),
            _Item('B', ['A']),
            _Item('A', []),
        ]
        new_sequence = base.reorder_dag(sequence)
        new_names = [x.app_name for x in new_sequence]
        eq_(new_names, ['A', 'B', 'C'])

    def test_basic_sloppy_depends_on(self):
        sequence = [
            _Item('C', ('B',)),
            _Item('B', 'A'),
            _Item('A', None),
        ]
        new_sequence = base.reorder_dag(sequence)
        new_names = [x.app_name for x in new_sequence]
        eq_(new_names, ['A', 'B', 'C'])

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
        ok_(
            new_names.index('A')
            <
            new_names.index('B')
            <
            new_names.index('C')
        )
        ok_(
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
        assert_raises(
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
        assert_raises(
            base.CircularDAGError,
            base.reorder_dag,
            sequence
        )


#==============================================================================
@attr(integration='postgres')
class TestStateDatabase(IntegrationTestCaseBase):

    def setUp(self):
        super(TestStateDatabase, self).setUp()
        required_config = crontabber.CronTabber.get_required_config()
        config_manager = ConfigurationManager(
            [required_config,
             #logging_required_config(app_name)
             ],
            values_source_list=[DSN],
            app_name='crontabber',
            argv_source=[]
        )

        config = config_manager.get_config()
        config.crontabber.logger = mock.Mock()
        self.database = crontabber.StateDatabase(config.crontabber)

    def test_has_data(self):
        ok_(not self.database.has_data())
        self.database['foo'] = {
            'next_run': utc_now(),
            'last_run': utc_now(),
            'first_run': utc_now(),
            'depends_on': [],
            'error_count': 0,
            'last_error': {}
        }
        ok_(self.database.has_data())

    def test_iterate_app_names(self):
        app_names = set()
        for app_name in self.database:
            app_names.add(app_name)
        eq_(app_names, set())

        self.database['foo'] = {
            'next_run': utc_now(),
            'last_run': utc_now(),
            'first_run': utc_now(),
            'depends_on': [],
            'error_count': 0,
            'last_error': {}
        }
        self.database['bar'] = {
            'next_run': utc_now(),
            'last_run': utc_now(),
            'first_run': utc_now(),
            'depends_on': [],
            'error_count': 0,
            'last_error': {}
        }

        app_names = set()
        for app_name in self.database:
            app_names.add(app_name)
        eq_(app_names, set(['foo', 'bar']))

    def test_keys_values_items(self):
        foo = {
            'next_run': utc_now(),
            'last_run': utc_now(),
            'first_run': utc_now(),
            'last_success': utc_now(),
            'depends_on': [],
            'error_count': 0,
            'last_error': {}
        }
        self.database['foo'] = foo
        bar = {
            'next_run': utc_now(),
            'last_run': utc_now(),
            'first_run': utc_now(),
            'last_success': None,
            'depends_on': [],
            'error_count': 0,
            'last_error': {}
        }
        self.database['bar'] = bar
        eq_(set(['foo', 'bar']), set(self.database.keys()))
        items = dict(self.database.items())
        eq_(items['foo'], foo)
        eq_(items['bar'], bar)

        values = self.database.values()
        eq_(len(values), 2)
        ok_(foo in values)
        ok_(bar in values)

    def test_contains(self):
        ok_('foo' not in self.database)
        self.database['foo'] = {
            'next_run': utc_now(),
            'last_run': utc_now(),
            'first_run': utc_now(),
            'depends_on': [],
            'error_count': 0,
            'last_error': {}
        }
        ok_('foo' in self.database)

    def test_getitem_and_setitem(self):
        data = {
            'next_run': utc_now(),
            'last_run': utc_now(),
            'first_run': utc_now(),
            'last_success': None,
            'depends_on': [],
            'error_count': 0,
            'last_error': {}
        }
        self.database['foo'] = data
        eq_(self.database['foo'], data)

    def test_copy_and_update(self):
        foo = {
            'next_run': utc_now(),
            'last_run': utc_now(),
            'first_run': utc_now(),
            'last_success': utc_now(),
            'depends_on': ['bar'],
            'error_count': 1,
            'last_error': {}
        }
        bar = {
            'next_run': utc_now(),
            'last_run': utc_now(),
            'first_run': utc_now(),
            'last_success': None,
            'depends_on': [],
            'error_count': 2,
            'last_error': {}
        }
        self.database['foo'] = foo
        self.database['bar'] = bar

        stuff = self.database.copy()
        eq_(stuff['foo'], foo)
        eq_(stuff['bar'], bar)

        stuff['foo']['error_count'] = 10
        self.database.update(stuff)

        new_foo = self.database['foo']
        eq_(new_foo, dict(foo, error_count=10))

    def test_get(self):
        foo = {
            'next_run': utc_now(),
            'last_run': utc_now(),
            'first_run': utc_now(),
            'last_success': None,
            'depends_on': [],
            'error_count': 0,
            'last_error': {}
        }
        self.database['foo'] = foo
        eq_(self.database.get('foo'), foo)
        eq_(self.database.get('bar', 'default'), 'default')

    def test_pop(self):
        foo = {
            'next_run': utc_now(),
            'last_run': utc_now(),
            'first_run': utc_now(),
            'last_success': None,
            'depends_on': [],
            'error_count': 0,
            'last_error': {}
        }
        self.database['foo'] = foo
        popped_foo = self.database.pop('foo')
        eq_(popped_foo, foo)
        ok_('foo' not in self.database)
        assert not self.database.has_data()
        popped = self.database.pop('foo', 'default')
        eq_(popped, 'default')
        assert_raises(KeyError, self.database.pop, 'bar')


#==============================================================================
@attr(integration='postgres')
class TestCrontabber(IntegrationTestCaseBase):

    def setUp(self):
        super(TestCrontabber, self).setUp()
        cursor = self.conn.cursor()
        cursor.execute("""
        DROP TABLE IF EXISTS test_cron_victim;
        CREATE TABLE test_cron_victim (
          id serial primary key,
          time timestamp DEFAULT current_timestamp
        );
        """)
        self.conn.commit()

    def tearDown(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        DROP TABLE IF EXISTS test_cron_victim;
        """)
        self.conn.commit()
        super(TestCrontabber, self).tearDown()

    def test_basic_run_job(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BasicJob|7d'
        )

        def fmt(d):
            return d.split('.')[0]

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            config['job'] = 'unheard-of-app-name'
            assert_raises(
                crontabber.JobNotFoundError,
                tab.main,
            )
            config['job'] = 'basic-job'
            assert tab.main() == 0
            config.logger.info.assert_called_with('Ran BasicJob')

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            # check that this was written to the JSON file
            # and that the next_run is going to be 1 day from now
            structure = self._load_structure()
            information = structure['basic-job']
            eq_(information['error_count'], 0)
            eq_(information['last_error'], {})
            today = utc_now()
            one_week = today + datetime.timedelta(days=7)
            self.assertAlmostEqual(today, information['last_run'])
            self.assertAlmostEqual(today, information['last_run'])
            self.assertAlmostEqual(one_week, information['next_run'])
            self.assertAlmostEqual(
                information['last_run'],
                information['last_success']
            )

            # run it again and nothing should happen
            count_infos = len([x for x in infos if 'Ran BasicJob' in x])
            assert count_infos > 0
            tab.run_one('basic-job')
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            count_infos_after = len([x for x in infos if 'Ran BasicJob' in x])
            eq_(count_infos, count_infos_after)

            # force it the second time
            tab.run_one('basic-job', force=True)
            ok_('Ran BasicJob' in infos)
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            count_infos_after_second = len([x for x in infos
                                            if 'Ran BasicJob' in x])
            eq_(count_infos_after_second, count_infos + 1)

            logs = self._load_logs()
            eq_(len(logs['basic-job']), 2)
            ok_(logs['basic-job'][0]['success'])
            ok_(logs['basic-job'][0]['duration'])

    def test_run_job_by_class_path(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BasicJob|30m'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_one('socorro.unittest.cron.test_crontabber.BasicJob')
            config.logger.info.assert_called_with('Ran BasicJob')

    def test_basic_run_all(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.FooJob|3d\n'
            'socorro.unittest.cron.test_crontabber.BarJob|4d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            assert tab.main() == 0

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            ok_('Ran FooJob' in infos)
            ok_('Ran BarJob' in infos)
            ok_(infos.index('Ran FooJob') <
                            infos.index('Ran BarJob'))
            count = len(infos)

            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            count_after = len(infos)
            eq_(count, count_after)

            # wind the clock forward by three days
            combined_state = tab.job_database.copy()
            self._wind_clock(combined_state, days=3)
            tab.job_database.update(combined_state)

            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            eq_(infos[-1], 'Ran FooJob')
            count_after_after = len(infos)
            eq_(count_after + 1, count_after_after)

    def test_run_into_error_first_time(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.TroubleJob|7d\n',
            extra_value_source={
                'crontabber.error_retry_time': '100'
            }
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            structure = self._load_structure()
            information = structure['trouble']

            eq_(information['error_count'], 1)
            ok_(information['last_error'])
            ok_(not information.get('last_success'), {})
            today = utc_now()
            self.assertAlmostEqual(today, information['last_run'])
            _next_run = utc_now() + datetime.timedelta(seconds=100)
            self.assertAlmostEqual(_next_run, information['next_run'])

            # list the output
            old_stdout = sys.stdout
            new_stdout = StringIO()
            sys.stdout = new_stdout

            config['list-jobs'] = True
            try:
                assert tab.main() == 0
            finally:
                sys.stdout = old_stdout
            output = new_stdout.getvalue()
            last_success_line = [x for x in output.splitlines()
                                 if 'Last success' in x][0]
            ok_('no previous successful run' in last_success_line)

            logs = self._load_logs()
            eq_(len(logs['trouble']), 1)
            ok_(not logs['trouble'][0]['success'])
            ok_(logs['trouble'][0]['duration'])
            ok_(logs['trouble'][0]['exc_type'])
            ok_(logs['trouble'][0]['exc_value'])
            ok_(logs['trouble'][0]['exc_traceback'])

    def test_run_all_with_failing_dependency(self):
        config_manager = self._setup_config_manager(
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
            eq_(
                infos,
                ['Ran BasicJob', 'Ran TroubleJob', 'Ran FooJob']
            )
            # note how SadJob couldn't be run!
            # let's see what information we have
            structure = self._load_structure()
            assert structure
            ok_('basic-job' in structure)
            ok_('trouble' in structure)
            ok_('sad' not in structure)
            eq_(structure['trouble']['error_count'], 1)
            err = structure['trouble']['last_error']
            ok_('NameError' in err['traceback'])
            ok_('NameError' in err['type'])
            ok_('Trouble!!' in err['value'])

            # you can't run the sad job either
            count_before = len(infos)
            tab.run_one('sad')
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            count_after = len(infos)
            eq_(count_before, count_after)

            # unless you force it
            tab.run_one('sad', force=True)
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            count_after_after = len(infos)
            eq_(count_after + 1, count_after_after)

    def test_run_all_basic_with_failing_dependency_without_errors(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BarJob|1d'
        )

        # the BarJob one depends on FooJob but suppose that FooJob
        # hasn't never run
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            assert_raises(
                base.CircularDAGError,
                tab.run_all
            )

    def test_run_all_with_failing_dependency_without_errors_but_old(self):
        config_manager = self._setup_config_manager(
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
            eq_(infos, ['Ran FooJob', 'Ran BarJob'])

            combined_state = tab.job_database.copy()
            self._wind_clock(combined_state, days=1, seconds=1)
            tab.job_database.update(combined_state)

            # this forces in crontabber instance to reload the JSON file
            tab._database = None

            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            # obvious
            eq_(
                infos,
                ['Ran FooJob', 'Ran BarJob', 'Ran FooJob', 'Ran BarJob']
            )

            # repeat
            combined_state = tab.job_database.copy()
            self._wind_clock(combined_state, days=2)
            tab.job_database.update(combined_state)

            # now, let's say FooJob hasn't errored but instead we try to run
            # the dependent and it shouldn't allow it
            tab.run_one('bar')
            infos_before = infos[:]
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            eq_(infos, infos_before)

    def test_depends_on_recorded_in_state(self):
        # set up a couple of jobs that depend on each other
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.FooJob|1d\n'
            'socorro.unittest.cron.test_crontabber.BarJob|1d\n'
            'socorro.unittest.cron.test_crontabber.FooBarJob|1d'
        )
        # the BarJob one depends on FooJob but suppose that FooJob
        # has run for but a very long time ago
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            structure = self._load_structure()
            assert 'foo' in structure
            assert 'bar' in structure
            assert 'foobar' in structure

            eq_(structure['foo']['depends_on'], [])
            eq_(structure['bar']['depends_on'], ['foo'])
            eq_(structure['foobar']['depends_on'], ['foo', 'bar'])

    @mock.patch('socorro.cron.crontabber.utc_now')
    def test_basic_run_job_with_hour(self, mocked_utc_now):
        config_manager = self._setup_config_manager(
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

            structure = self._load_structure()
            assert 'basic-job' in structure
            information = structure['basic-job']
            eq_(
                information['next_run'].strftime('%H:%M:%S'), '03:00:00'
            )
            assert 'foo' in structure
            information = structure['foo']
            eq_(
                information['next_run'].strftime('%H:%M:%S'), '01:45:00'
            )

    @mock.patch('socorro.cron.crontabber.utc_now')
    def test_list_jobs(self, mocked_utc_now):
        config_manager = self._setup_config_manager(
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
            eq_(output.count('Class:'), 4)
            eq_(
                4,
                len(re.findall('App name:\s+(trouble|basic-job|foo|sad)',
                               output, re.I))
            )
            eq_(
                4,
                len(re.findall('No previous run info', output, re.I))
            )

            tab.run_all()
            assert 'sad' not in tab.job_database
            assert 'basic-job' in tab.job_database
            assert 'foo' in tab.job_database
            assert 'trouble' in tab.job_database
            old_stdout = sys.stdout
            new_stdout = StringIO()
            sys.stdout = new_stdout
            try:
                tab.list_jobs()
            finally:
                sys.stdout = old_stdout
            output = new_stdout.getvalue()
            # sad job won't be run since its depdendent keeps failing
            eq_(
                1,
                len(re.findall('No previous run info', output, re.I))
            )

            # split them up so that we can investigate each block of output
            outputs = {}
            for block in re.split('={5,80}', output)[1:]:
                key = re.findall('App name:\s+([\w-]+)', block)[0]
                outputs[key] = block

            ok_(re.findall('No previous run info',
                                       outputs['sad'], re.I))
            ok_(re.findall('Error',
                                       outputs['trouble'], re.I))
            ok_(re.findall('1 time',
                                       outputs['trouble'], re.I))
            ok_(re.findall('raise NameError',
                                       outputs['trouble'], re.I))
            # since the exception type and exception value is also displayed
            # in the output we can expect these to be shown twice
            eq_(outputs['trouble'].count('NameError'), 2)
            eq_(outputs['trouble'].count('Trouble!!'), 2)
            ok_(re.findall('7d @ 03:00',
                                       outputs['basic-job'], re.I))

    def test_configtest_ok(self):
        config_manager = self._setup_config_manager(
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
            config['configtest'] = True
            try:
                assert tab.main() == 0
            finally:
                sys.stderr = old_stderr
                sys.stdout = old_stdout
            ok_(not new_stderr.getvalue())
            ok_(not new_stdout.getvalue())

    def test_configtest_not_found(self):
        assert_raises(
            crontabber.JobNotFoundError,
            self._setup_config_manager,
            'socorro.unittest.cron.test_crontabber.YYYYYY|3d'
        )

    def test_configtest_definition_error(self):
        assert_raises(
            crontabber.JobDescriptionError,
            self._setup_config_manager,
            'socorro.unittest.cron.test_crontabber.FooJob'
        )

    def test_configtest_bad_frequency(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.FooJob|3e'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            old_stderr = sys.stderr
            new_stderr = StringIO()
            sys.stderr = new_stderr
            try:
                ok_(not tab.configtest())
            finally:
                sys.stderr = old_stderr
            output = new_stderr.getvalue()
            ok_('FrequencyDefinitionError' in output)
            # twice per not found
            eq_(output.count('FrequencyDefinitionError'), 2)
            ok_('Error value: e' in output)

    def test_configtest_bad_time(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.FooJob|24:59\n'
            'socorro.unittest.cron.test_crontabber.BasicJob|23:60'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            old_stderr = sys.stderr
            new_stderr = StringIO()
            sys.stderr = new_stderr
            try:
                ok_(not tab.configtest())
            finally:
                sys.stderr = old_stderr
            output = new_stderr.getvalue()
            ok_('TimeDefinitionError' in output)
            # twice per not found
            eq_(output.count('TimeDefinitionError'), 2 + 2)
            ok_('24:59' in output)

    def test_configtest_bad_time_invariance(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.FooJob|3h|23:59'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            old_stderr = sys.stderr
            new_stderr = StringIO()
            sys.stderr = new_stderr
            try:
                ok_(not tab.configtest())
            finally:
                sys.stderr = old_stderr
            output = new_stderr.getvalue()
            ok_('FrequencyDefinitionError' in output)
            # twice per not found
            ok_(output.count('FrequencyDefinitionError'))
            ok_('23:59' in output)

    @mock.patch('socorro.cron.crontabber.utc_now')
    @mock.patch('socorro.cron.base.utc_now')
    def test_basic_job_at_specific_hour(self,
                                        mocked_utc_now,
                                        mocked_utc_now_2):
        # let's pretend the clock is 09:00 and try to run this
        # the first time, then nothing should happen
        config_manager = self._setup_config_manager(
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
            ok_(not self._load_structure())

        # Pretend it's now 10:30 UTC
        def mock_utc_now_2():
            n = utc_now()
            return n.replace(hour=10, minute=30)

        mocked_utc_now.side_effect = mock_utc_now_2
        mocked_utc_now_2.side_effect = mock_utc_now_2

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            structure = self._load_structure()
            assert structure
            information = structure['foo']
            eq_(
                information['first_run'].strftime('%H:%M'), '10:30'
            )
            eq_(
                information['last_run'].strftime('%H:%M'), '10:30'
            )
            eq_(
                information['last_success'].strftime('%H:%M'), '10:30'
            )
            eq_(
                information['next_run'].strftime('%H:%M'), '10:00'
            )

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
            structure = self._load_structure()
            assert structure
            information = structure['foo']
            assert not information['last_error']

            eq_(
                information['first_run'].strftime('%H:%M'), '10:30'
            )
            eq_(
                information['last_run'].strftime('%H:%M'), '10:30'
            )
            eq_(
                information['last_success'].strftime('%H:%M'), '10:30'
            )
            eq_(
                information['next_run'].strftime('%H:%M'), '10:00'
            )

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            assert len(infos) == 2, infos

    @mock.patch('socorro.cron.crontabber.utc_now')
    @mock.patch('socorro.cron.base.utc_now')
    def test_backfill_job_at_specific_hour(self,
                                           mocked_utc_now,
                                           mocked_utc_now_2):
        # let's pretend the clock is 09:00 and try to run this
        # the first time, then nothing should happen
        config_manager = self._setup_config_manager(
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
            structure = self._load_structure()
            ok_(not structure)

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
            structure = self._load_structure()
            ok_(structure)
            information = structure['foo-backfill']
            assert not information['last_error']
            eq_(
                information['first_run'].strftime('%H:%M'), '10:30'
            )
            eq_(
                information['last_run'].strftime('%H:%M'), '10:30'
            )
            eq_(
                information['last_success'].strftime('%H:%M'), '10:30'
            )
            eq_(
                information['next_run'].strftime('%H:%M'), '10:00'
            )

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
            structure = self._load_structure()
            ok_(structure)
            information = structure['foo-backfill']
            assert not information['last_error']

            eq_(
                information['first_run'].strftime('%H:%M'),
                '10:30'
            )
            eq_(
                information['last_run'].strftime('%H:%M'),
                '10:30'
            )
            eq_(
                information['last_success'].strftime('%H:%M'),
                '10:00'
            )
            eq_(
                information['next_run'].strftime('%H:%M'),
                '10:00'
            )

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            assert len(infos) == 2, infos

    def test_execute_postgres_based_job(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.PostgresSampleJob|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            config.logger.info.assert_called_with('Ran PostgresSampleJob')

            structure = self._load_structure()
            assert structure['sample-pg-job']
            ok_(not structure['sample-pg-job']['last_error'])

    def test_execute_postgres_transaction_managed_job(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.'
            'PostgresTransactionSampleJob|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            (config.logger.info
             .assert_called_with('Ran PostgresTransactionSampleJob'))
            structure = self._load_structure()
            assert structure['sample-transaction-pg-job']
            ok_(
                not structure['sample-transaction-pg-job']['last_error']
            )

    def test_execute_failing_postgres_based_job(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BrokenPostgresSampleJob|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            ok_('Ran PostgresSampleJob' not in infos)

            information = tab.job_database['broken-pg-job']
            ok_(information['last_error'])
            ok_(
                'ProgrammingError' in
                information['last_error']['type']
            )

    def test_own_required_config_job(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber'
            '.OwnRequiredConfigSampleJob|1d'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            ok_(
                'Ran OwnRequiredConfigSampleJob(%r)' % 'bugz.mozilla.org'
                in infos
            )

    def test_own_required_config_job_overriding_config(self):
        config_manager = self._setup_config_manager(
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
            ok_(
                'Ran OwnRequiredConfigSampleJob(%r)' % 'bugs.peterbe.com'
                in infos
            )

    def test_automatic_backfill_basic_job(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.FooBackfillJob|1d'
        )

        def fmt(d):
            return d.split('.')[0]

        # first just run it as is
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            structure = self._load_structure()
            information = structure['foo-backfill']
            eq_(information['first_run'], information['last_run'])

            # last_success might be a few microseconds off
            self.assertAlmostEqual(
                information['last_run'],
                information['last_success']
            )
            ok_(not information['last_error'])

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            eq_(len(infos), 1)

            # now, pretend the last 2 days have failed
            interval = datetime.timedelta(days=2)
            state = tab.job_database['foo-backfill']
            state['first_run'] -= interval
            state['last_success'] -= interval
            #tab.database['foo-backfill'] = state

            state = self._wind_clock(state, days=1)
            tab.job_database['foo-backfill'] = state

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
                ok_([x for x in infos
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

        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber'
            '.CertainDayHaterBackfillJob|1d'
        )
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            app_name = CertainDayHaterBackfillJob.app_name

            # now, pretend the last 2 days have failed
            interval = datetime.timedelta(days=2)
            state = tab.job_database[app_name]
            state['first_run'] -= interval
            state['last_success'] -= interval

            self._wind_clock(state, days=1)
            tab.job_database[app_name] = state

            CertainDayHaterBackfillJob.fail_on = (
                tab.job_database[app_name]['first_run'] + interval
            )

            first_last_success = tab.job_database[app_name]['last_success']
            tab.run_all()

            # now, we expect the new last_success to be 1 day more
            new_last_success = tab.job_database[app_name]['last_success']
            eq_((new_last_success - first_last_success).days, 1)

    def test_backfilling_postgres_based_job(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.PGBackfillJob|1d'
        )

        def fmt(d):
            return d.split('.')[0]

        # first just run it as is
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            structure = self._load_structure()
            information = structure['pg-backfill']  # app_name of PGBackfillJob

            # Note, these are strings of dates
            eq_(information['first_run'], information['last_run'])

            # last_success might be a few microseconds off
            self.assertAlmostEqual(
                information['last_run'],
                information['last_success']
            )
            ok_(not information['last_error'])

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            eq_(len(infos), 1)

            # now, pretend the last 2 days have failed
            interval = datetime.timedelta(days=2)
            state = tab.job_database['pg-backfill']
            state['first_run'] -= interval
            state['last_success'] -= interval

            self._wind_clock(state, days=1)
            tab.job_database['pg-backfill'] = state

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
                ok_([x for x in infos
                                 if formatted in x])

    def test_run_with_excess_whitespace(self):
        # this test asserts a found bug where excess newlines
        # caused configuration exceptions
        config_manager = self._setup_config_manager(
            '\n \n'
            ' socorro.unittest.cron.test_crontabber.BasicJob|7d\n\t  \n'
        )

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            structure = self._load_structure()
            information = structure['basic-job']
            ok_(information['last_success'])
            ok_(not information['last_error'])

    def test_commented_out_jobs_from_option(self):
        config_manager = self._setup_config_manager('''
          socorro.unittest.cron.test_crontabber.FooJob|3d
        #  socorro.unittest.cron.test_crontabber.BarJob|4d
        ''')

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            structure = self._load_structure()
            ok_('foo' in structure)
            ok_('bar' not in structure)
            eq_(structure.keys(), ['foo'])

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
        config_manager = self._setup_config_manager(
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

            structure = self._load_structure()
            information = structure['slow-backfill']
            eq_(
                information['next_run'].strftime('%H:%M:%S'),
                '18:00:00'
            )
            eq_(
                information['first_run'].strftime('%H:%M:%S'),
                '18:02:00'
            )
            eq_(
                information['last_run'].strftime('%H:%M:%S'),
                '18:02:00'
            )
            eq_(
                information['last_success'].strftime('%H:%M:%S'),
                '18:02:00'
            )

            eq_(
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

            structure = self._load_structure()
            information = structure['slow-backfill']
            eq_(
                information['next_run'].strftime('%H:%M:%S'),
                '18:00:00'
            )
            eq_(
                information['last_run'].strftime('%H:%M:%S'),
                '18:01:01'
            )
            eq_(
                information['last_success'].strftime('%H:%M:%S'),
                '18:00:00'
            )

    @mock.patch('socorro.cron.crontabber.utc_now')
    @mock.patch('socorro.cron.base.utc_now')
    @mock.patch('time.sleep')
    def test_slow_backfilled_timed_daily_job(self, time_sleep,
                                             mocked_utc_now, mocked_utc_now_2):
        config_manager = self._setup_config_manager(
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
            eq_(len(SlowBackfillJob.times_used), 1)
            time_after = crontabber.utc_now()
            # double-checking
            assert (time_after - time_before).seconds == 1

            structure = self._load_structure()
            information = structure['slow-backfill']
            ok_(information['last_success'])
            ok_(not information['last_error'])
            # easy
            eq_(
                information['next_run'].strftime('%H:%M:%S'),
                '10:00:00'
            )
            eq_(information['first_run'], information['last_run'])

            # pretend one day passes
            _extra_time.append(datetime.timedelta(days=1))
            time_later = crontabber.utc_now()
            assert (time_later - time_after).days == 1
            assert (time_later - time_after).seconds == 0
            assert (time_later - time_before).days == 1
            assert (time_later - time_before).seconds == 1

            tab.run_all()
            eq_(len(SlowBackfillJob.times_used), 2)
            structure = self._load_structure()
            information = structure['slow-backfill']

            # another day passes
            _extra_time.append(datetime.timedelta(days=1))
            # also, simulate that it starts a second earlier this time
            _extra_time.append(-datetime.timedelta(seconds=1))
            tab.run_all()
            assert len(SlowBackfillJob.times_used) == 3
            structure = self._load_structure()
            information = structure['slow-backfill']

    @mock.patch('socorro.cron.base.utc_now')
    @mock.patch('socorro.cron.crontabber.utc_now')
    @mock.patch('time.sleep')
    def test_slow_backfilled_timed_daily_job_first_failure(self,
                                                           time_sleep,
                                                           mocked_utc_now,
                                                           mocked_utc_now_2):
        config_manager = self._setup_config_manager(
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
            eq_(len(SlowBackfillJob.times_used), 1)

            #db = crontabber.JSONJobDatabase()
            #db.load(json_file)
            state = tab.job_database['slow-backfill']
            del state['last_success']
            tab.job_database['slow-backfill'] = state

        _extra_time.append(datetime.timedelta(days=1))
        _extra_time.append(-datetime.timedelta(seconds=1))

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            eq_(len(SlowBackfillJob.times_used), 2)

    def test_reset_job(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BasicJob|1d\n'
            'socorro.unittest.cron.test_crontabber.FooJob|1d'
        )
        BasicJob.times_used = []
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            config['reset-job'] = 'never-heard-of'
            assert_raises(
                crontabber.JobNotFoundError,
                tab.main,
            )

            config['reset-job'] = 'basic-job'
            assert tab.main() == 0
            config.logger.warning.assert_called_with('App already reset')

            # run them
            config['reset-job'] = None
            assert tab.main() == 0
            eq_(len(BasicJob.times_used), 1)
            structure = self._load_structure()
            assert 'basic-job' in structure

            config['reset-job'] = 'basic-job'
            assert tab.main() == 0
            config.logger.info.assert_called_with('App reset')
            structure = self._load_structure()
            ok_('basic-job' not in structure)

    def test_nagios_ok(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BasicJob|1d\n'
            'socorro.unittest.cron.test_crontabber.FooJob|1d'
        )
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            stream = StringIO()
            exit_code = tab.nagios(stream=stream)
            eq_(exit_code, 0)
            eq_(stream.getvalue(), 'OK - All systems nominal\n')

    def test_nagios_warning(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BasicJob|1d\n'
            'socorro.unittest.cron.test_crontabber.BackfillbasedTrouble|1d'
        )
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            stream = StringIO()
            exit_code = tab.nagios(stream=stream)
            eq_(exit_code, 1)
            output = stream.getvalue()
            ok_('WARNING' in output)
            ok_('backfill-trouble' in output)
            ok_('BackfillbasedTrouble' in output)
            ok_('NameError' in output)
            ok_('bla bla' in output)

            # run it a second time
            # wind the clock forward
            state = tab.job_database['backfill-trouble']
            self._wind_clock(state, days=1)
            tab.job_database['backfill-trouble'] = state

            state = tab.job_database['basic-job']
            self._wind_clock(state, days=1)
            tab.job_database['basic-job'] = state

            # this forces in crontabber instance to reload the JSON file
            tab._database = None

            tab.run_all()
            stream = StringIO()
            exit_code = tab.nagios(stream=stream)
            eq_(exit_code, 2)
            output = stream.getvalue()
            ok_('CRITICAL' in output)
            ok_('backfill-trouble' in output)
            ok_('BackfillbasedTrouble' in output)
            ok_('NameError' in output)
            ok_('bla bla' in output)

    def test_nagios_critical(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BasicJob|1d\n'
            'socorro.unittest.cron.test_crontabber.TroubleJob|1d'
        )
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            stream = StringIO()
            exit_code = tab.nagios(stream=stream)
            eq_(exit_code, 2)
            output = stream.getvalue()
            ok_('CRITICAL' in output)
            ok_('trouble' in output)
            ok_('TroubleJob' in output)
            ok_('NameError' in output)
            ok_('Trouble!!' in output)

    def test_nagios_multiple_messages(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.TroubleJob|1d\n'
            'socorro.unittest.cron.test_crontabber.MoreTroubleJob|1d'
        )
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            stream = StringIO()
            exit_code = tab.nagios(stream=stream)
            eq_(exit_code, 2)
            output = stream.getvalue()
            eq_(len(output.strip().splitlines()), 1)
            eq_(output.count('CRITICAL'), 1)
            ok_('trouble' in output)
            ok_('more-trouble' in output)
            ok_('TroubleJob' in output)
            ok_('MoreTroubleJob' in output)
            ok_('NameError' in output)
            ok_('Trouble!!' in output)

    def test_reorder_dag_on_joblist(self):
        config_manager = self._setup_config_manager(
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
            structure = self._load_structure()
            ok_('foo' in structure)
            ok_('bar' in structure)
            ok_('foobar' in structure)
            ok_(
                structure['foo']['last_run']
                <
                structure['bar']['last_run']
                <
                structure['foobar']['last_run']
            )

    def test_retry_errors_sooner(self):
        """
        FooBarBackfillJob depends on FooBackfillJob and BarBackfillJob
        BarBackfillJob depends on FooBackfillJob
        FooBackfillJob doesn't depend on anything
        We'll want to pretend that BarBackfillJob (second to run)
        fails and notice that FooBarBackfillJob won't run.
        Then we wind the clock forward 5 minutes and run all again,
        this time, the FooBackfillJob shouldn't need to run but
        BarBackfillJob and FooBackfillJob should both run twice
        """
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.BarBackfillJob|1d\n'
            'socorro.unittest.cron.test_crontabber.FooBackfillJob|1d\n'
            'socorro.unittest.cron.test_crontabber.FooBarBackfillJob|1d',
            extra_value_source={
                # crontabber already has a good default for this but by
                # being explict like this we not only show that it can be
                # changed, we also make it clear what the unit test is
                # supposed to do.
                'crontabber.error_retry_time': '3600'  # 1 hour
            }
        )

        # first we need to hack-about so that BarBackfillJob fails only
        # once.

        class SomeError(Exception):
            pass

        def nosy_run(self, date):
            dates_used[self.__class__].append(date)
            if self.__class__ == BarBackfillJob:
                if len(dates_used[self.__class__]) == 1:
                    # first time run, simulate trouble
                    raise SomeError("something went wrong")
            return originals[self.__class__](self, date)

        classes = BarBackfillJob, FooBackfillJob, FooBarBackfillJob
        originals = {}
        dates_used = collections.defaultdict(list)
        for klass in classes:
            originals[klass] = klass.run
            klass.run = nosy_run

        try:
            with config_manager.context() as config:
                tab = crontabber.CronTabber(config)
                tab.run_all()
                eq_(len(dates_used[FooBackfillJob]), 1)
                eq_(len(dates_used[FooBackfillJob]), 1)
                # never gets there because dependency fails
                eq_(len(dates_used[FooBarBackfillJob]), 0)

                structure = self._load_structure()
                assert structure['foo-backfill']
                assert not structure['foo-backfill']['last_error']
                next_date = utc_now() + datetime.timedelta(days=1)
                self.assertAlmostEqual(
                    next_date,
                    structure['foo-backfill']['next_run']
                )

                assert structure['bar-backfill']
                assert structure['bar-backfill']['last_error']
                next_date = utc_now() + datetime.timedelta(hours=1)
                self.assertAlmostEqual(
                    next_date,
                    structure['bar-backfill']['next_run']
                )

                assert 'foobar-backfill' not in structure

                # Now, let the magic happen, we pretend time passes by 2 hours
                # and run all jobs again
                combined_state = tab.job_database.copy()
                self._wind_clock(combined_state, hours=2)
                tab.job_database.update(combined_state)

                # here, we go two hours later
                tab.run_all()

                # Here's the magic sauce! The FooBarBackfillJob had to wait
                # two hours to run after FooBackfillJob but it should
                # have been given the same date input as when FooBackfillJob
                # ran.
                eq_(len(dates_used[FooBackfillJob]), 1)
                eq_(len(dates_used[FooBackfillJob]), 1)
                eq_(len(dates_used[FooBarBackfillJob]), 1)

                # use this formatter so that we don't have to compare
                # datetimes with microseconds
                format = lambda x: x.strftime('%Y%m%d %H:%M %Z')
                eq_(
                    format(dates_used[FooBackfillJob][0]),
                    format(dates_used[FooBarBackfillJob][0])
                )
                # also check the others
                eq_(
                    format(dates_used[BarBackfillJob][0]),
                    format(dates_used[FooBarBackfillJob][0])
                )

                structure = self._load_structure()
                ok_(structure['foo-backfill'])
                ok_(not structure['foo-backfill']['last_error'])
                ok_(structure['bar-backfill'])
                ok_(not structure['bar-backfill']['last_error'])
                ok_(structure['foobar-backfill'])
                ok_(not structure['foobar-backfill']['last_error'])

        finally:
            for klass in classes:
                klass.run = originals[klass]

    @mock.patch('raven.Client')
    def test_sentry_sending(self, raven_client_mocked):
        FAKE_DSN = 'https://24131e9070324cdf99d@errormill.mozilla.org/XX'
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.TroubleJob|7d',
            extra_value_source={
                'sentry.dsn': FAKE_DSN,
            }
        )

        get_ident_calls = []

        def fake_get_ident(exception):
            get_ident_calls.append(exception)
            return '123456789'

        mocked_client = mock.MagicMock()
        mocked_client.get_ident.side_effect = fake_get_ident

        def fake_client(dsn):
            assert dsn == FAKE_DSN
            return mocked_client

        raven_client_mocked.side_effect = fake_client

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            config.logger.info.assert_any_call(
                'Error captured in Sentry. Reference: 123456789',
            )

        structure = self._load_structure()
        assert structure['trouble']['last_error']
        ok_(get_ident_calls)

    @mock.patch('raven.Client')
    def test_sentry_failing(self, raven_client_mocked):
        FAKE_DSN = 'https://24131e9070324cdf99d@errormill.mozilla.org/XX'
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.TroubleJob|7d',
            extra_value_source={
                'sentry.dsn': FAKE_DSN,
            }
        )

        def fake_get_ident(exception):
            raise NameError('waldo')

        mocked_client = mock.MagicMock()
        mocked_client.get_ident.side_effect = fake_get_ident

        def fake_client(dsn):
            assert dsn == FAKE_DSN
            return mocked_client

        raven_client_mocked.side_effect = fake_client

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            config.logger.debug.assert_any_call(
                'Failed to capture and send error to Sentry',
                exc_info=True
            )

        structure = self._load_structure()
        assert structure['trouble']['last_error']

    def test_postgres_job(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber.PostgresSampleJob|1d'
        )

        cur = self.conn.cursor()
        cur.execute('select * from test_cron_victim')
        ok_(not cur.fetchall())

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            ok_('Ran PostgresSampleJob' in infos)

            cur = self.conn.cursor()
            cur.execute('select * from test_cron_victim')
            ok_(cur.fetchall())

        structure = self._load_structure()
        assert structure
        information = structure['sample-pg-job']
        ok_(information['next_run'])
        ok_(information['last_run'])
        ok_(information['first_run'])
        ok_(not information.get('last_error'))

    def test_postgres_job_with_broken(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber'
            '.BrokenPostgresSampleJob|1d\n'
            'socorro.unittest.cron.test_crontabber'
            '.PostgresSampleJob|1d'
        )

        cur = self.conn.cursor()
        cur.execute('select * from test_cron_victim')
        ok_(not cur.fetchall())

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            ok_('Ran PostgresSampleJob' in infos)

            cur = self.conn.cursor()
            cur.execute('select * from test_cron_victim')
            # Note! The BrokenPostgresSampleJob actually does an insert first
            # before it raises the ProgrammingError. The following test
            # makes sure to test that the rollback of the transaction works
            eq_(len(cur.fetchall()), 1)
            out = StringIO()
            tab.list_jobs(stream=out)
            output = out.getvalue()
            outputs = {}
            for block in re.split('={5,80}', output)[1:]:
                key = re.findall('App name:\s+([\w-]+)', block)[0]
                outputs[key] = block

            ok_('Error' in outputs['broken-pg-job'])
            ok_('ProgrammingError' in outputs['broken-pg-job'])
            ok_('Error' not in outputs['sample-pg-job'])

    def test_postgres_job_with_backfill_basic(self):
        config_manager = self._setup_config_manager(
            'socorro.unittest.cron.test_crontabber'
            '.PostgresBackfillSampleJob|1d'
        )

        cur = self.conn.cursor()
        cur.execute('select * from test_cron_victim')
        ok_(not cur.fetchall())

        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()
            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            eq_(len(infos), 1)

            cur = self.conn.cursor()
            cur.execute('select * from test_cron_victim')
            ok_(cur.fetchall())

    def test_postgres_job_with_backfill_3_days_back(self):
        config_manager = self._setup_config_manager(
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
            eq_(count, 1)

            structure = self._load_structure()

            app_name = PostgresBackfillSampleJob.app_name
            information = structure[app_name]

            # Note, these are strings of dates
            eq_(information['first_run'], information['last_run'])

            # last_success might be a few microseconds off
            self.assertAlmostEqual(
                information['last_run'],
                information['last_success']
            )
            ok_(not information['last_error'])

            infos = [x[0][0] for x in config.logger.info.call_args_list]
            infos = [x for x in infos if x.startswith('Ran ')]
            eq_(len(infos), 1)

            # now, pretend the last 2 days have failed
            interval = datetime.timedelta(days=2)
            state = tab.job_database[app_name]
            state['first_run'] -= interval
            state['last_success'] -= interval

            self._wind_clock(state, days=1)
            tab.job_database[app_name] = state

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
            eq_(len(records), 4)

            today = utc_now()
            yesterday = today - datetime.timedelta(days=1)
            day_before_yesterday = today - datetime.timedelta(days=2)
            for each in (today, yesterday, day_before_yesterday):
                formatted = each.strftime('%Y-%m-%d')
                ok_([x for x in infos
                                 if formatted in x])


#==============================================================================
## Various mock jobs that the tests depend on
class _Job(base.BaseCronApp):

    def run(self):
        assert self.app_name
        self.config.logger.info("Ran %s" % self.__class__.__name__)


@with_postgres_transactions()
@with_postgres_connection_as_argument()
class _PGJob(_Job):

    def run(self, connection):
        _Job.run(self)


@with_postgres_transactions()
@with_single_postgres_transaction()
class _PGTransactionManagedJob(_Job):

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


class MoreTroubleJob(TroubleJob):
    app_name = 'more-trouble'


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
        raise psycopg2.ProgrammingError("Egads!")


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


@as_backfill_cron_app
class _BackfillJob(_Job):

    def run(self, date):
        assert isinstance(date, datetime.datetime)
        assert self.app_name
        self.config.logger.info(
            "Ran %s(%s, %s)" % (self.__class__.__name__, date, id(date))
        )


class FooBackfillJob(_BackfillJob):
    app_name = 'foo-backfill'


class BarBackfillJob(_BackfillJob):
    app_name = 'bar-backfill'
    depends_on = 'foo-backfill'


class FooBarBackfillJob(_BackfillJob):
    app_name = 'foobar-backfill'
    depends_on = ('foo-backfill', 'bar-backfill')


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


@with_postgres_transactions()
@with_postgres_connection_as_argument()
@as_backfill_cron_app
class PGBackfillJob(_Job):
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


@with_postgres_transactions()
@with_postgres_connection_as_argument()
@as_backfill_cron_app
class PostgresBackfillSampleJob(_Job):
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
