# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import functools

import mock
from nose.plugins.attrib import attr
from nose.tools import eq_, ok_

from crontabber.app import CronTabber
from socorro.unittest.cron.jobs.base import IntegrationTestBase

import datetime

from socorro.lib.datetimeutil import utc_now
from socorro.unittest.cron.setup_configman import (
    get_config_manager_for_crontabber,
)


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
class TestModulelist(IntegrationTestBase):

    def setUp(self):
        super(TestModulelist, self).setUp()
        self.Popen_patcher = mock.patch('subprocess.Popen')
        self.Popen = self.Popen_patcher.start()

    def tearDown(self):
        super(TestModulelist, self).tearDown()
        self.Popen_patcher.stop()

    def _setup_config_manager(self):
        overrides = {
            'crontabber.class-ModulelistCronApp.pig_classpath': '/some/place',
            'crontabber.class-ModulelistCronApp.output_file':
                '/some/other/place/%(date)s-modulelist.txt'
        }
        return get_config_manager_for_crontabber(
            jobs='socorro.cron.jobs.modulelist.ModulelistCronApp|1d',
            overrides=overrides
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
            tab = CronTabber(config)
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
            ok_(
                'PIG_CLASSPATH=/some/place pig' in first
            )
            ok_(
                '-param start_date=%s' % yesterday_fmt in first
            )
            ok_(
                '-param end_date=%s' % yesterday_fmt in first
            )
            ok_(
                '/some/place/modulelist.pig' in first
            )

            ok_(
                'PIG_CLASSPATH=/some/place hadoop fs -getmerge' in second
            )
            ok_(
                'modulelist-%s-%s' % (yesterday_fmt, yesterday_fmt) in second
            )
            ok_(
                '/some/other/place/%s-modulelist.txt' % (yesterday_fmt,)
                in second
            )

            ok_(
                'PIG_CLASSPATH=/some/place hadoop fs ' in third
            )
            ok_(
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
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['modulelist']
            assert information['modulelist']['last_error']
            _traceback = information['modulelist']['last_error']['traceback']
            ok_('pig run failed' in _traceback)
            # the other two where cancelled
            eq_(len(commands_sent), 1)
            config.logger.error.has_calls([
                mock.call('First command failed :(')
            ])

    def test_failing_hadoop_getmerge_job(self):
        # a mutable where commands sent are stored
        commands_sent = []
        self.Popen.side_effect = functools.partial(
            mocked_Popen,
            _commands_sent=commands_sent,
            _exit_code=lambda cmd: 1 if cmd.count('getmerge') else 0,
            _stdout='',
            _stderr=lambda cmd: 'Enormity' if cmd.count('getmerge') else '',
        )

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()

            information = self._load_structure()
            assert information['modulelist']
            assert information['modulelist']['last_error']
            _traceback = information['modulelist']['last_error']['traceback']
            ok_('hadoop getmerge failed' in _traceback)
            # the other two where cancelled
            eq_(len(commands_sent), 2)
            config.logger.error.has_calls([mock.call('Enormity')])

    def test_failing_hadoop_cleanup_job(self):
        # a mutable where commands sent are stored
        commands_sent = []
        self.Popen.side_effect = functools.partial(
            mocked_Popen,
            _commands_sent=commands_sent,
            _exit_code=lambda cmd: 1 if cmd.count('-rmr') else 0,
            _stdout='',
            _stderr=lambda cmd: 'Iniquity' if cmd.count('-rmr') else '',
        )

        config_manager = self._setup_config_manager()
        with config_manager.context() as config:
            tab = CronTabber(config)
            tab.run_all()
            information = self._load_structure()
            assert information['modulelist']
            assert information['modulelist']['last_error']
            _traceback = information['modulelist']['last_error']['traceback']
            ok_('hadoop cleanup failed' in _traceback)
            # the other two where cancelled
            eq_(len(commands_sent), 3)
            config.logger.error.has_calls([mock.call('Iniquity')])
