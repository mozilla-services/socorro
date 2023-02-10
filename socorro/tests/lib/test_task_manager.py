# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from unittest import mock

from socorro.lib.task_manager import TaskManager


class TestTaskManager:
    def test_get_iterator(self):
        # job_source_iterator as an iterable
        tm = TaskManager(job_source_iterator=range(3))
        assert list(tm._get_iterator()) == [0, 1, 2]

        tm = TaskManager(job_source_iterator=[1, 2, 3])
        assert list(tm._get_iterator()) == [1, 2, 3]

        class X:
            def __init__(self):
                self.items = [1, 2, 3, 4, 5]

            def __iter__(self):
                yield from self.items

        tm = TaskManager(job_source_iterator=X())
        assert list(tm._get_iterator()) == [1, 2, 3, 4, 5]

        # job_source_iterator as a callable
        def an_iter():
            yield from range(5)

        tm = TaskManager(job_source_iterator=an_iter)
        assert list(tm._get_iterator()) == [0, 1, 2, 3, 4]

    def test_blocking_start(self):

        class MyTaskManager(TaskManager):
            def _responsive_sleep(self, seconds, wait_log_interval=0, wait_reason=""):
                try:
                    if self.count >= 2:
                        raise KeyboardInterrupt
                    self.count += 1
                except AttributeError:
                    self.count = 0

        tm = MyTaskManager(idle_delay=1, task_func=mock.Mock())

        tm.blocking_start()

        assert tm.task_func.call_count == 10

    def test_blocking_start_with_quit_on_empty(self):
        tm = TaskManager(idle_delay=1, quit_on_empty_queue=True, task_func=mock.Mock())

        tm.blocking_start()

        assert tm.task_func.call_count == 10
