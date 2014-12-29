# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from mock import Mock
from nose.tools import eq_, ok_

from socorro.lib.task_manager import TaskManager, default_task_func
from socorro.lib.util import DotDict, SilentFakeLogger
from socorro.unittest.testbase import TestCase


class TestTaskManager(TestCase):

    def setUp(self):
        super(TestTaskManager, self).setUp()
        self.logger = SilentFakeLogger()

    def test_constuctor1(self):
        config = DotDict()
        config.logger = self.logger
        config.quit_on_empty_queue =  False

        tm = TaskManager(config)
        ok_(tm.config == config)
        ok_(tm.logger == self.logger)
        ok_(tm.task_func == default_task_func)
        ok_(tm.quit == False)

    def test_executor_identity(self):
        config = DotDict()
        config.logger = self.logger
        tm = TaskManager(
            config,
            job_source_iterator=range(1),

        )
        tm._pid = 666
        eq_(tm.executor_identity(), '666-MainThread')

    def test_get_iterator(self):
        config = DotDict()
        config.logger = self.logger
        config.quit_on_empty_queue =  False

        tm = TaskManager(
            config,
            job_source_iterator=range(1),
        )
        eq_(tm._get_iterator(), [0])

        def an_iter(self):
            for i in range(5):
                yield i

        tm = TaskManager(
            config,
            job_source_iterator=an_iter,
        )
        eq_(
            [x for x in tm._get_iterator()],
            [0, 1, 2, 3, 4]
        )

        class X(object):
            def __init__(self, config):
                self.config = config

            def __iter__(self):
                for key in self.config:
                    yield key

        tm = TaskManager(
            config,
            job_source_iterator=X(config)
        )
        eq_(
            [x for x in tm._get_iterator()],
            [y for y in config.keys()]
        )

    def test_blocking_start(self):
        config = DotDict()
        config.logger = self.logger
        config.idle_delay = 1
        config.quit_on_empty_queue =  False

        class MyTaskManager(TaskManager):
            def _responsive_sleep(
                self,
                seconds,
                wait_log_interval=0,
                wait_reason=''
            ):
                try:
                    if self.count >= 2:
                        self.quit = True
                    self.count += 1
                except AttributeError:
                    self.count = 0

        tm = MyTaskManager(
            config,
            task_func=Mock()
        )

        waiting_func = Mock()

        tm.blocking_start(waiting_func=waiting_func)

        eq_(
            tm.task_func.call_count,
            10
        )
        eq_(waiting_func.call_count, 0)


    def test_blocking_start_with_quit_on_empty(self):
        config = DotDict()
        config.logger = self.logger
        config.idle_delay = 1
        config.quit_on_empty_queue =  True

        tm = TaskManager(
            config,
            task_func=Mock()
        )

        waiting_func = Mock()

        tm.blocking_start(waiting_func=waiting_func)

        eq_(
            tm.task_func.call_count,
            10
        )
        eq_(waiting_func.call_count, 0)
