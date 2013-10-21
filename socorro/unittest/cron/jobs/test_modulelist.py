# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import functools

import mock
from nose.plugins.attrib import attr

from socorro.cron import crontabber
from ..base import IntegrationTestCaseBase
import datetime

from socorro.lib.datetimeutil import utc_now


#==============================================================================
# Tools for helping with the mocking

class _Proc(object):
    def __init__(self, exit_code, stdout, stderr):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = exit_code

    def communicate(self, input=None):
        return (self.stdout, self.stderr)


def mocked_Popen(command, **kwargs):
    kwargs['_commands_sent'].append(command)
    _exit_code = kwargs['_exit_code']
    _stdout = kwargs['_stdout']
    _stderr = kwargs['_stderr']
    # some might be callables
    if callable(_exit_code):
        _exit_code = _exit_code(command)
    if callable(_stdout):
        _stdout = _stdout(command)
    if callable(_stderr):
        _stderr = _stderr(command)

    return _Proc(
        _exit_code,
        _stdout,
        _stderr
    )


#==============================================================================
@attr(integration='postgres')
class TestModulelist(IntegrationTestCaseBase):

    def setUp(self):
        super(TestModulelist, self).setUp()
        self.Popen_patcher = mock.patch('subprocess.Popen')
        self.Popen = self.Popen_patcher.start()

    def tearDown(self):
        super(TestModulelist, self).tearDown()
        self.Popen_patcher.stop()

    def _setup_config_manager(self):
        _super = super(TestModulelist, self)._setup_config_manager
        _source = {}
        _source['crontabber.class-ModulelistCronApp.pig_classpath'] = (
            '/some/place'
        )
        _source['crontabber.class-ModulelistCronApp.output_file'] = (
            '/some/other/place/%(date)s-modulelist.txt'
        )
        return _super(
            'socorro.cron.jobs.modulelist.ModulelistCronApp|1d',
            extra_value_source=_source
        )

    def test_basic_run_no_errors(self):
        # a mutable where commands sent are stored
        commands_sent = []
        self.Popen.side_effect = functools.partial(
            mocked_Popen,
            _commands_sent=commands_sent,
            _exit_code=0,
            _stdout='Bla bla',
            _stderr='',
        )

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['modulelist']
            #print information['modulelist']['last_error']
            #print information['modulelist']['last_error']['traceback']
            if information['modulelist']['last_error']:
                raise AssertionError(information['modulelist']['last_error'])

            assert len(commands_sent) == 3
            first = commands_sent[0]
            second = commands_sent[1]
            third = commands_sent[2]
            yesterday = utc_now()
            yesterday -= datetime.timedelta(days=1)
            yesterday_fmt = yesterday.strftime('%Y%m%d')
            self.assertTrue(
                'PIG_CLASSPATH=/some/place pig' in first
            )
            self.assertTrue(
                '-param start_date=%s' % yesterday_fmt in first
            )
            self.assertTrue(
                '-param end_date=%s' % yesterday_fmt in first
            )
            self.assertTrue(
                '/some/place/modulelist.pig' in first
            )

            self.assertTrue(
                'PIG_CLASSPATH=/some/place hadoop fs -getmerge' in second
            )
            self.assertTrue(
                'modulelist-%s-%s' % (yesterday_fmt, yesterday_fmt) in second
            )
            self.assertTrue(
                '/some/other/place/%s-modulelist.txt' % (yesterday_fmt,)
                in second
            )

            self.assertTrue(
                'PIG_CLASSPATH=/some/place hadoop fs ' in third
            )
            self.assertTrue(
                'modulelist-%s-%s' % (yesterday_fmt, yesterday_fmt) in second
            )

            # note that all jobs spew out 'Bla bla' on stdout
            config.logger.info.assert_called_with('Bla bla')

    def test_failing_pig_job(self):
        # a mutable where commands sent are stored
        commands_sent = []
        self.Popen.side_effect = functools.partial(
            mocked_Popen,
            _commands_sent=commands_sent,
            _exit_code=1,
            _stdout='',
            _stderr='First command failed :(',
        )

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['modulelist']
            assert information['modulelist']['last_error']
            _traceback = information['modulelist']['last_error']['traceback']
            self.assertTrue('pig run failed' in _traceback)
            # the other two where cancelled
            self.assertEqual(len(commands_sent), 1)
            config.logger.error.assert_called_with('First command failed :(')

    def test_failing_hadoop_getmerge_job(self):
        # a mutable where commands sent are stored
        commands_sent = []
        self.Popen.side_effect = functools.partial(
            mocked_Popen,
            _commands_sent=commands_sent,
            _exit_code=lambda cmd: 1 if cmd.count('getmerge') else 0,
            _stdout='',
            _stderr=lambda cmd: 'Shit' if cmd.count('getmerge') else '',
        )

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['modulelist']
            assert information['modulelist']['last_error']
            _traceback = information['modulelist']['last_error']['traceback']
            self.assertTrue('hadoop getmerge failed' in _traceback)
            # the other two where cancelled
            self.assertEqual(len(commands_sent), 2)
            config.logger.error.assert_called_with('Shit')

    def test_failing_hadoop_cleanup_job(self):
        # a mutable where commands sent are stored
        commands_sent = []
        self.Popen.side_effect = functools.partial(
            mocked_Popen,
            _commands_sent=commands_sent,
            _exit_code=lambda cmd: 1 if cmd.count('-rmr') else 0,
            _stdout='',
            _stderr=lambda cmd: 'Poop' if cmd.count('-rmr') else '',
        )

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = crontabber.CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['modulelist']
            assert information['modulelist']['last_error']
            _traceback = information['modulelist']['last_error']['traceback']
            self.assertTrue('hadoop cleanup failed' in _traceback)
            # the other two where cancelled
            self.assertEqual(len(commands_sent), 3)
            config.logger.error.assert_called_with('Poop')
