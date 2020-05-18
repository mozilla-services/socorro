# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import time
from unittest import mock

from configman.dotdict import DotDict

from socorro.lib.threaded_task_manager import ThreadedTaskManager, default_task_func


class TestThreadedTaskManager:
    def test_constuctor1(self):
        config = DotDict()
        config.number_of_threads = 1
        config.maximum_queue_size = 1
        ttm = ThreadedTaskManager(config)
        try:
            assert ttm.config == config
            assert ttm.task_func == default_task_func
            assert not ttm.quit
        finally:
            # we got threads to join
            ttm._kill_worker_threads()

    def test_start1(self):
        config = DotDict()
        config.number_of_threads = 1
        config.maximum_queue_size = 1
        ttm = ThreadedTaskManager(config)
        try:
            ttm.start()
            time.sleep(0.2)
            assert ttm.queuing_thread.is_alive(), "the queing thread is not running"
            assert len(ttm.thread_list) == 1, "where's the worker thread?"
            assert ttm.thread_list[0].is_alive(), "the worker thread is stillborn"
            ttm.stop()
            assert not ttm.queuing_thread.is_alive(), "the queuing thread did not stop"
        except Exception:
            # we got threads to join
            ttm.wait_for_completion()

    def test_doing_work_with_one_worker(self):
        config = DotDict()
        config.number_of_threads = 1
        config.maximum_queue_size = 1
        my_list = []

        def insert_into_list(anItem):
            my_list.append(anItem)

        ttm = ThreadedTaskManager(config, task_func=insert_into_list)
        try:
            ttm.start()
            time.sleep(0.2)
            assert len(my_list) == 10
            assert my_list == list(range(10))
            ttm.stop()
        except Exception:
            # we got threads to join
            ttm.wait_for_completion()
            raise

    def test_doing_work_with_two_workers_and_generator(self):
        config = DotDict()
        config.number_of_threads = 2
        config.maximum_queue_size = 2
        my_list = []

        def insert_into_list(anItem):
            my_list.append(anItem)

        ttm = ThreadedTaskManager(
            config,
            task_func=insert_into_list,
            job_source_iterator=(((x,), {}) for x in range(10)),
        )
        try:
            ttm.start()
            time.sleep(0.2)
            assert len(ttm.thread_list) == 2
            assert len(my_list) == 10
            assert sorted(my_list) == list(range(10))
        except Exception:
            # we got threads to join
            ttm.wait_for_completion()
            raise

    # failure tests

    count = 0

    def test_blocking_start_with_quit_on_empty(self):
        config = DotDict()
        config.number_of_threads = 2
        config.maximum_queue_size = 2
        config.quit_on_empty_queue = True

        calls = []

        def task_func(index):
            calls.append(index)

        tm = ThreadedTaskManager(config, task_func=task_func)

        waiting_func = mock.Mock()

        tm.blocking_start(waiting_func=waiting_func)
        assert len(calls) == 10
