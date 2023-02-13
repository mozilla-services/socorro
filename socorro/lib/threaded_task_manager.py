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

from configman import Namespace

from socorro.lib.task_manager import default_task_func, default_iterator, TaskManager


class ThreadedTaskManager(TaskManager):
    """Threaded task manager."""

    required_config = Namespace()
    required_config.add_option(
        "idle_delay", default=7, doc="the delay in seconds if no job is found"
    )
    # how does one choose how many threads to use?  Keep the number low if your
    # application is compute bound.  You can raise it if your app is i/o
    # bound.  The best thing to do is to test the through put of your app with
    # several values.  For Socorro, we've found that setting this value to the
    # number of processor cores in the system gives the best throughput.
    required_config.add_option(
        "number_of_threads", default=4, doc="the number of threads"
    )
    # there is wisdom is setting the maximum queue size to be no more than
    # twice the number of threads.  By keeping the threads starved, the
    # queing thread will be blocked more more frequently.  Once an item
    # is in the queue, there may be no way to fetch it again if disaster
    # strikes and this app quits or fails.  Potentially anything left in
    # the queue could be lost.  Limiting the queue size insures minimal
    # damage in a worst case scenario.
    required_config.add_option(
        "maximum_queue_size", default=8, doc="the maximum size of the internal queue"
    )

    def __init__(
        self, config, job_source_iterator=default_iterator, task_func=default_task_func
    ):
        """the constructor accepts the function that will serve as the data
        source iterator and the function that the threads will execute on
        consuming the data.

        parameters:
            job_source_iterator - an iterator to serve as the source of data.
                                  it can be of the form of a generator or
                                  iterator; a function that returns an
                                  iterator; a instance of an iterable object;
                                  or a class that when instantiated with a
                                  config object can be iterated.  The iterator
                                  must yield a tuple consisting of a
                                  function's tuple of args and, optionally, a
                                  mapping of kwargs.
                                  Ex:  (('a', 17), {'x': 23})
            task_func - a function that will accept the args and kwargs yielded
                        by the job_source_iterator"""
        super().__init__(config, job_source_iterator, task_func)
        self.thread_list = []  # the thread object storage
        self.number_of_threads = config.number_of_threads
        self.task_queue = queue.Queue(config.maximum_queue_size)

    def start(self):
        """Starts the queueing thread and creates workers.

        The queueing thread executes the iterator and feeds jobs into the work queue.
        This then starts the worker threads.

        """
        self.logger.debug("start")
        # start each of the task threads.
        for x in range(self.number_of_threads):
            # each thread is given the config object as well as a reference to
            # this manager class.  The manager class is where the queue lives
            # and the task threads will refer to it to get their next jobs.
            new_thread = TaskThread(self.config, self.task_queue)
            self.thread_list.append(new_thread)
            new_thread.start()
        self.queuing_thread = threading.Thread(
            name="QueuingThread", target=self._queuing_thread_func
        )
        self.queuing_thread.start()

    def wait_for_completion(self):
        """Blocks on queueing thread completion."""
        self.logger.debug("waiting to join queuing_thread")
        while True:
            try:
                self.queuing_thread.join(1.0)
                if not self.queuing_thread.is_alive():
                    break
            except KeyboardInterrupt:
                self.logger.debug("quit detected by wait_for_completion")
                self.quit = True

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
            # it only ends if someone hits  ^C or sends SIGHUP or SIGTERM -
            # any of which will get translated into a KeyboardInterrupt
        except KeyboardInterrupt:
            while True:
                try:
                    self.stop()
                    break
                except KeyboardInterrupt:
                    self.logger.warning(
                        "We heard you the first time.  There "
                        "is no need for further keyboard or signal "
                        "interrupts.  We are waiting for the "
                        "worker threads to stop.  If this app "
                        "does not halt soon, you may have to send "
                        "SIGKILL (kill -9)"
                    )

    def wait_for_empty_queue(self, wait_log_interval=0, wait_reason=""):
        """Sit around and wait for the queue to become empty

        parameters:
            wait_log_interval - while sleeping, it is helpful if the thread
                                periodically announces itself so that we
                                know that it is still alive.  This number is
                                the time in seconds between log entries.
            wait_reason - the is for the explaination of why the thread is
                          sleeping.  This is likely to be a message like:
                          'there is no work to do'."""
        seconds = 0
        while True:
            if self.task_queue.empty():
                break
            if wait_log_interval and not seconds % wait_log_interval:
                self.logger.info("%s: %dsec so far", wait_reason, seconds)
            seconds += 1
            time.sleep(1.0)

    def _kill_worker_threads(self):
        """This function coerces the consumer/worker threads to kill
        themselves.  When called by the queuing thread, one death token will
        be placed on the queue for each thread.  Each worker thread is always
        looking for the death token.  When it encounters it, it immediately
        runs to completion without drawing anything more off the queue.

        This is a blocking call.  The thread using this function will wait for
        all the worker threads to die."""
        for x in range(self.number_of_threads):
            self.task_queue.put((None, None))
        self.logger.debug("waiting for standard worker threads to stop")
        for t in self.thread_list:
            t.join()

    def _queuing_thread_func(self):
        """This is the function responsible for reading the iterator and
        putting contents into the queue.  It loops as long as there are items
        in the iterator.  Should something go wrong with this thread, or it
        detects the quit flag, it will calmly kill its workers and then
        quit itself."""
        self.logger.debug("_queuing_thread_func start")
        try:
            # May never exhaust
            for job_params in self._get_iterator():
                if job_params is None:
                    if self.config.quit_on_empty_queue:
                        self.wait_for_empty_queue(
                            wait_log_interval=10,
                            wait_reason="waiting for queue to drain",
                        )
                        raise KeyboardInterrupt
                    self._responsive_sleep(self.config.idle_delay)
                    continue

                self.logger.debug("received %r", job_params)
                self.task_queue.put((self.task_func, job_params))
        except Exception:
            self.logger.error("queuing jobs has failed", exc_info=True)
        except KeyboardInterrupt:
            self.logger.debug("queuing_thread gets quit request")
        finally:
            self.logger.debug("we're quitting queuing_thread")
            self._kill_worker_threads()
            self.logger.debug("all worker threads stopped")
            self.quit = True


class TaskThread(threading.Thread):
    """This class represents a worker thread for the TaskManager class"""

    def __init__(self, config, task_queue):
        """Initialize a new thread.

        parameters:
            config - the configuration from configman
            task_queue - a reference to the queue from which to fetch jobs
        """
        super().__init__()
        self.task_queue = task_queue
        self.config = config
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
                function, arguments = self.task_queue.get()
                if function is None:
                    # this allows us to watch the threads die and identify
                    # threads that may be hanging or deadlocked
                    self.logger.info("quits")
                    break
                if quit_request_detected:
                    continue
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
