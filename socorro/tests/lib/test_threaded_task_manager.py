# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import time

from socorro.lib.threaded_task_manager import ThreadedTaskManager


class TestThreadedTaskManager:
    def test_start(self):
        ttm = ThreadedTaskManager(
            idle_delay=1,
            number_of_threads=1,
            maximum_queue_size=1,
        )
        try:
            ttm.start()
            time.sleep(0.2)
            assert ttm.queueing_thread.is_alive()
            assert len(ttm.thread_list) == 1
            assert ttm.thread_list[0].is_alive()
            ttm.stop()
            assert not ttm.queueing_thread.is_alive()
        finally:
            # we got threads to join
            ttm.wait_for_completion()

    def test_doing_work_with_one_worker(self):
        my_list = []

        def insert_into_list(anItem):
            my_list.append(anItem)

        ttm = ThreadedTaskManager(
            idle_delay=1,
            number_of_threads=1,
            maximum_queue_size=1,
            task_func=insert_into_list,
        )
        try:
            ttm.start()
            time.sleep(0.2)
            assert len(my_list) == 10
            assert my_list == list(range(10))
            ttm.stop()
        finally:
            # we got threads to join
            ttm.wait_for_completion()

    def test_doing_work_with_two_workers_and_generator(self):
        my_list = []

        def insert_into_list(anItem):
            my_list.append(anItem)

        ttm = ThreadedTaskManager(
            idle_delay=1,
            number_of_threads=2,
            maximum_queue_size=2,
            task_func=insert_into_list,
            job_source_iterator=(((x,), {}) for x in range(10)),
        )
        try:
            ttm.start()
            time.sleep(0.2)
            assert len(ttm.thread_list) == 2
            assert len(my_list) == 10
            assert sorted(my_list) == list(range(10))
        finally:
            # we got threads to join
            ttm.wait_for_completion()

    def test_blocking_start_with_quit_on_empty(self):
        calls = []

        def task_func(index):
            calls.append(index)

        tm = ThreadedTaskManager(
            number_of_threads=2,
            maximum_queue_size=2,
            quit_on_empty_queue=True,
            task_func=task_func,
        )

        tm.blocking_start()
        assert len(calls) == 10
