# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Defines the ThreadedTaskManager.

This module defines classes that implements a threaded producer/consumer system. A
single iterator thread pushes jobs into an internal queue while a flock of
consumer/worker threads do the jobs. A job consists of a function and the data applied
to the function.

"""

import logging
import queue
import threading
import time

from socorro.lib.task_manager import (
    default_heartbeat,
    default_iterator,
    default_task_func,
    TaskManager,
)


STOP_TOKEN = (None, None)


class ThreadedTaskManager(TaskManager):
    """Threaded task manager."""

    def __init__(
        self,
        idle_delay=7,
        quit_on_empty_queue=False,
        number_of_threads=4,
        maximum_queue_size=8,
        job_source_iterator=default_iterator,
        heartbeat_func=default_heartbeat,
        task_func=default_task_func,
    ):
        """
        :arg idle_delay: the delay in seconds if no job is found
        :arg quit_on_empty_queue: stop if the queue is empty
        :arg number_of_threads: number of worker threads to run
        :arg maximum_queue_size: maximum size of the internal queue from which the
            threads poll
        :arg job_source_iterator: an iterator to serve as the source of data. it can
            be of the form of a generator or iterator; a function that returns an
            iterator; a instance of an iterable object; or a class that when
            instantiated with a config object can be iterated. The iterator must
            yield a tuple consisting of a function's tuple of args and, optionally,
            a mapping of kwargs. Ex:  (('a', 17), {'x': 23})
        :arg heartbeat_func: a function to run every second
        :arg task_func: a function that will accept the args and kwargs yielded
            by the job_source_iterator
        """

        # If number of threads is None, set it to default
        if number_of_threads is None:
            number_of_threads = 4

        # If maximum queue size is None, set it to default
        if maximum_queue_size is None:
            maximum_queue_size = 8

        super().__init__(
            idle_delay=idle_delay,
            quit_on_empty_queue=quit_on_empty_queue,
            job_source_iterator=job_source_iterator,
            heartbeat_func=heartbeat_func,
            task_func=task_func,
        )
        self.thread_list = []  # the thread object storage
        self.number_of_threads = number_of_threads
        self.task_queue = queue.Queue(maximum_queue_size)

        self.queueing_thread = None

    def start(self):
        """Starts the queueing thread and creates workers.

        The queueing thread executes the iterator and feeds jobs into the work queue.
        This then starts the worker threads.

        """
        self.logger.debug("start")
        # start each of the task threads.
        for _ in range(self.number_of_threads):
            # each thread is given the config object as well as a reference to
            # this manager class.  The manager class is where the queue lives
            # and the task threads will refer to it to get their next jobs.
            new_thread = TaskThread(self.task_queue)
            self.thread_list.append(new_thread)
            new_thread.start()

        self.queueing_thread = threading.Thread(
            name="queueingThread", target=self._queueing_thread_func
        )
        self.queueing_thread.start()

    def wait_for_completion(self):
        """Blocks on queueing thread completion."""
        if self.queueing_thread is None:
            return

        self.logger.debug("waiting to join queueing_thread")
        while True:
            self.heartbeat_func()
            try:
                self.queueing_thread.join(1.0)
                if not self.queueing_thread.is_alive():
                    break
            except KeyboardInterrupt:
                self.logger.debug("quit detected by wait_for_completion")

    def stop(self):
        """Stop all worker threads."""
        self.quit = True
        self.wait_for_completion()

    def blocking_start(self):
        """Starts queueing thread and waits for it to complete.

        If run by the main thread, it will detect the KeyboardInterrupt exception and
        will stop worker threads.

        """
        try:
            self.start()
            self.wait_for_completion()
        except KeyboardInterrupt:
            while True:
                try:
                    self.stop()
                    break
                except KeyboardInterrupt:
                    pass

    def wait_for_empty_queue(self, wait_log_interval=0, wait_reason=""):
        """Wait for queue to become empty.

        :arg wait_log_interval: While sleeping, it is helpful if the thread periodically
            announces itself so that we know that it is still alive. This number is the
            time in seconds between log entries.
        :arg wait_reason: The is for the explaination of why the thread is sleeping.
            This is likely to be a message like: 'there is no work to do'.

        """
        seconds = 0
        while True:
            if self.task_queue.empty():
                break
            if wait_log_interval and not seconds % wait_log_interval:
                self.logger.info("%s: %dsec so far", wait_reason, seconds)
            seconds += 1
            time.sleep(1.0)

    def _stop_worker_threads(self):
        """Stop worker threads.

        When called by the queueing thread, one STOP_TOKEN will be placed on the queue
        for each thread. Each worker thread works until it hits a STOP_TOKEN and then
        immediately ends.

        This is a blocking call. The thread using this function will wait for
        all the worker threads to end.

        """
        for _ in range(self.number_of_threads):
            self.task_queue.put(STOP_TOKEN)
        self.logger.debug("waiting for standard worker threads to stop")
        for t in self.thread_list:
            t.join()

    def _queueing_thread_func(self):
        """Main function for queueing thread

        This is the function responsible for reading the iterator and putting contents
        into the queue. It loops as long as there are items in the iterator. Should
        something go wrong with this thread, or it detects the quit flag, it will stop
        workers and then quit.

        """
        self.logger.debug("_queueing_thread_func start")
        try:
            # May never exhaust
            for job_params in self._get_iterator():
                if self.quit:
                    raise KeyboardInterrupt

                if job_params is None:
                    if self.quit_on_empty_queue:
                        self.wait_for_empty_queue(
                            wait_log_interval=10,
                            wait_reason="waiting for queue to drain",
                        )
                        raise KeyboardInterrupt

                    self._responsive_sleep(self.idle_delay)
                    continue

                self.logger.debug("received %r", job_params)
                self.task_queue.put((self.task_func, job_params))
        except Exception:
            self.logger.error("queueing jobs has failed", exc_info=True)
        except KeyboardInterrupt:
            self.logger.debug("queueing_thread gets quit request")
        finally:
            self.logger.debug("we're quitting queueing_thread")
            self._stop_worker_threads()
            self.logger.debug("all worker threads stopped")


class TaskThread(threading.Thread):
    """This class represents a worker thread for the TaskManager class"""

    def __init__(self, task_queue):
        """Initialize a new thread.

        :arg task_queue: a reference to the queue from which to fetch jobs

        """
        super().__init__()
        self.task_queue = task_queue
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

    def _get_name(self):
        return threading.currentThread().getName()

    def run(self):
        """The main routine for a thread's work.

        The thread pulls tasks from the task queue and executes them until it
        encounters a death token.  The death token is a tuple of two Nones.
        """
        try:
            quit_request_detected = False
            while True:
                task = self.task_queue.get()
                if task is STOP_TOKEN:
                    self.logger.info("quits")
                    break
                if quit_request_detected:
                    continue

                function, arguments = task
                try:
                    try:
                        args, kwargs = arguments
                    except ValueError:
                        args = arguments
                        kwargs = {}
                    function(*args, **kwargs)  # execute the task
                except Exception:
                    self.logger.error("Error in processing a job", exc_info=True)
                except KeyboardInterrupt:  # TODO: can probably go away
                    self.logger.info("quit request detected")
                    quit_request_detected = True
                    # Only needed if signal handler is not registered
                    # thread.interrupt_main()
        except Exception:
            self.logger.critical("Failure in task_queue", exc_info=True)
