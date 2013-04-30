"""This module defines classes that implements a threaded
producer/consumer system.  A single iterator thread pushes jobs into an
internal queue while a flock of consumer/worker threads do the jobs.  A job
consists of a function and the data applied to the function."""

import time
import threading
import Queue

from configman import RequiredConfig, Namespace
from configman.converters import class_converter


#------------------------------------------------------------------------------
def default_task_func(a_param):
    """This default consumer function just doesn't do anything.  It is a
    placeholder just to demonstrate the api and not really for any other
    purpose"""
    pass


#------------------------------------------------------------------------------
def default_iterator():
    """This default producer's iterator yields the integers 0 through 9 and
    then yields none forever thereafter.  It is a placeholder to demonstrate
    the  api and not used for anything in a real system."""
    for x in range(10):
        yield ((x,), {})
    while True:
        yield None


#------------------------------------------------------------------------------
# TODO: This may not be necessary anymore; I believe Python has ironed out
# ctrl-C in multithreaded situations.
def respond_to_SIGTERM(signal_number, frame):
    """ these classes are instrumented to respond to a KeyboardInterrupt by
    cleanly shutting down.  This function, when given as a handler to for
    a SIGTERM event, will make the program respond to a SIGTERM as neatly
    as it responds to ^C.

    This function is used in registering a signal handler from the signal
    module.  It should be registered for any signal for which the desired
    behavior is to kill the application:
        signal.signal(signal.SIGTERM, respondToSIGTERM)
        signal.signal(signal.SIGHUP, respondToSIGTERM)

    parameters:
        signal_number - unused in this function but required by the api.
        frame - unused in this function but required by the api.
    """
    raise KeyboardInterrupt


#==============================================================================
class ThreadedTaskManager(RequiredConfig):
    """Given an iterator over a sequence of job parameters and a function,
    this class will execute the function in a set of threads."""
    required_config = Namespace()
    required_config.add_option(
      'idle_delay',
      default=7,
      doc='the delay in seconds if no job is found'
    )
    # how does one choose how many threads to use?  Keep the number low if your
    # application is compute bound.  You can raise it if your app is i/o
    # bound.  The best thing to do is to test the through put of your app with
    # several values.  For Socorro, we've found that setting this value to the
    # number of processor cores in the system gives the best throughput.
    required_config.add_option(
      'number_of_threads',
      default=4,
      doc='the number of threads'
    )
    # there is wisdom is setting the maximum queue size to be no more than
    # twice the number of threads.  By keeping the threads starved, the
    # queing thread will be blocked more more frequently.  Once an item
    # is in the queue, there may be no way to fetch it again if disaster
    # strikes and this app quits or fails.  Potentially anything left in
    # the queue could be lost.  Limiting the queue size insures minimal
    # damage in a worst case scenario.
    required_config.add_option(
      'maximum_queue_size',
      default=8,
      doc='the maximum size of the internal queue'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config,
                 job_source_iterator=default_iterator,
                 task_func=default_task_func):
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
        super(ThreadedTaskManager, self).__init__()
        self.config = config
        self.logger = config.logger
        self.job_param_source_iter = job_source_iterator
        self.task_func = task_func

        self.thread_list = []  # the thread object storage
        self.number_of_threads = config.number_of_threads
        self.task_queue = Queue.Queue(config.maximum_queue_size)

        self.quit = False
        self.logger.debug('finished init')

    #--------------------------------------------------------------------------
    def start(self):
        """this function will start the queing thread that executes the
        iterator and feeds jobs into the queue.  It also starts the worker
        threads that just sit and wait for items to appear on the queue. This
        is a non blocking call, so the executing thread is free to do other
        things while the other threads work."""
        self.logger.debug('start')
        # start each of the task threads.
        for x in range(self.number_of_threads):
            # each thread is given the config object as well as a reference to
            # this manager class.  The manager class is where the queue lives
            # and the task threads will refer to it to get their next jobs.
            new_thread = TaskThread(self.config, self)
            self.thread_list.append(new_thread)
            new_thread.start()
        self.queuing_thread = threading.Thread(
          name="QueuingThread",
          target=self._queuing_thread_func
        )
        self.queuing_thread.start()

    #--------------------------------------------------------------------------
    def wait_for_completion(self, waiting_func=None):
        """This is a blocking function call that will wait for the queuing
        thread to complete.

        parameters:
            waiting_func - this function will be called every one second while
                           waiting for the queuing thread to quit.  This allows
                           for logging timers, status indicators, etc."""
        self.logger.debug("waiting to join queuingThread")
        self._responsive_join(self.queuing_thread, waiting_func)

    #--------------------------------------------------------------------------
    def stop(self):
        """This function will tell all threads to quit.  All threads
        periodically look at the value of quit.  If they detect quit is True,
        then they commit ritual suicide.  After setting the quit flag, this
        function will wait for the queuing thread to quit."""
        self.quit = True
        self.wait_for_completion()

    #--------------------------------------------------------------------------
    def blocking_start(self, waiting_func=None):
        """this function is just a wrapper around the start and
        wait_for_completion methods.  It starts the queuing thread and then
        waits for it to complete.  If run by the main thread, it will detect
        the KeyboardInterrupt exception (which is what SIGTERM and SIGHUP
        have been translated to) and will order the threads to die."""
        try:
            self.start()
            self.wait_for_completion(waiting_func)
            # it only ends if someone hits  ^C or sends SIGHUP or SIGTERM -
            # any of which will get translated into a KeyboardInterrupt
        except KeyboardInterrupt:
            while True:
                try:
                    self.stop()
                    break
                except KeyboardInterrupt:
                    self.logger.warning('We heard you the first time.  There '
                                   'is no need for further keyboard or signal '
                                   'interrupts.  We are waiting for the '
                                   'worker threads to stop.  If this app '
                                   'does not halt soon, you may have to send '
                                   'SIGKILL (kill -9)')

    #--------------------------------------------------------------------------
    def quit_check(self):
        """this is the polling function that the threads periodically look at.
        If they detect that the quit flag is True, then a KeyboardInterrupt
        is raised which will result in the threads dying peacefully"""
        if self.quit:
            raise KeyboardInterrupt

    #--------------------------------------------------------------------------
    def _responsive_sleep(self, seconds, wait_log_interval=0, wait_reason=''):
        """When there is litte work to do, the queuing thread sleeps a lot.
        It can't sleep for too long without checking for the quit flag and/or
        logging about why it is sleeping.

        parameters:
            seconds - the number of seconds to sleep
            wait_log_interval - while sleeping, it is helpful if the thread
                                periodically announces itself so that we
                                know that it is still alive.  This number is
                                the time in seconds between log entries.
            wait_reason - the is for the explaination of why the thread is
                          sleeping.  This is likely to be a message like:
                          'there is no work to do'.

        This was also partially motivated by old versions' of Python inability
        to KeyboardInterrupt out of a long sleep()."""
        for x in xrange(int(seconds)):
            self.quit_check()
            if wait_log_interval and not x % wait_log_interval:
                self.logger.info('%s: %dsec of %dsec',
                                 wait_reason,
                                 x,
                                 seconds)
                self.quit_check()
            time.sleep(1.0)

    #--------------------------------------------------------------------------
    def wait_for_empty_queue(self, wait_log_interval=0, wait_reason=''):
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
            self.quit_check()
            if wait_log_interval and not seconds % wait_log_interval:
                self.logger.info('%s: %dsec so far',
                                 wait_reason,
                                 seconds)
                self.quit_check()
            seconds += 1
            time.sleep(1.0)

    #--------------------------------------------------------------------------
    def _responsive_join(self, thread, waiting_func=None):
        """similar to the responsive sleep, a join function blocks a thread
        until some other thread dies.  If that takes a long time, we'd like to
        have some indicaition as to what the waiting thread is doing.  This
        method will wait for another thread while calling the waiting_func
        once every second.

        parameters:
            thread - an instance of the TaskThread class representing the
                     thread to wait for
            waiting_func - a function to call every second while waiting for
                           the thread to die"""
        while True:
            try:
                thread.join(1.0)
                if not thread.isAlive():
                    break
                if waiting_func:
                    waiting_func()
            except KeyboardInterrupt:
                self.logger.debug('quit detected by _responsive_join')
                self.quit = True

    #--------------------------------------------------------------------------
    def _get_iterator(self):
        """The iterator passed in can take several forms: a class that can be
        instantiated and then iterated over; a function that when called
        returns an iterator; an actual iterator/generator or an iterable
        collection.  This function sorts all that out and returns an iterator
        that can be used"""
        try:
            return self.job_param_source_iter(self.config)
        except TypeError:
            try:
                return self.job_param_source_iter()
            except TypeError:
                return self.job_param_source_iter

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    def _queuing_thread_func(self):
        """This is the function responsible for reading the iterator and
        putting contents into the queue.  It loops as long as there are items
        in the iterator.  Should something go wrong with this thread, or it
        detects the quit flag, it will calmly kill its workers and then
        quit itself."""
        self.logger.debug('_queuing_thread_func start')
        try:
            for job_params in self._get_iterator():  # may never raise
                                                     # StopIteration
                if job_params is None:
                    self.logger.info("there is nothing to do.  Sleeping "
                                     "for %d seconds" %
                                     self.config.idle_delay)
                    self._responsive_sleep(self.config.idle_delay)
                    continue
                self.quit_check()
                #self.logger.debug("queuing job %s", job_params)
                self.task_queue.put((self.task_func, job_params))
            else:
                self.logger.debug("the loop didn't actually loop")
        except Exception:
            self.logger.error('queuing jobs has failed', exc_info=True)
        except KeyboardInterrupt:
            self.logger.debug('queuingThread gets quit request')
        finally:
            self.quit = True
            self.logger.debug("we're quitting queuingThread")
            self._kill_worker_threads()
            self.logger.debug("all worker threads stopped")


#==============================================================================
class ThreadedTaskManagerWithConfigSetup(ThreadedTaskManager):
    """Given an iterator over a sequence of job parameters and a function,
    this class will execute the the function in a set of threads.

    Rather than accepting the job_source_iterator and task function as
    constructor arguments, this class gets those values from configuration.
    """
    required_config = Namespace()
    required_config = Namespace()
    required_config.add_option(
      'job_source_iterator',
      default=default_iterator,
      doc='an iterator or callable that will '
      'return an iterator',
      from_string_converter=class_converter
    )
    required_config.add_option(
      'task_func',
      default=default_task_func,
      doc='a callable that accomplishes a task',
      from_string_converter=class_converter
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        """Create the ThreadedTaskManager with config options rather than
        functions passed into the constructor."""
        super(ThreadedTaskManagerWithConfigSetup, self).__init__(
          config=config,
          job_source_iterator=config.job_source_iterator,
          task_func=config.task_func)


#==============================================================================
class TaskThread(threading.Thread):
    """This class represents a worker thread for the TaskManager class"""

    #--------------------------------------------------------------------------
    def __init__(self, config, manager):
        """Initialize a new thread.

        parameters:
            config - the configuration from configman
            manager - a reference to the controlling task manager.  It is
                      through this reference that the worker threads will
                      access the queue fromwhich to fetch jobs.
        """
        super(TaskThread, self).__init__()
        self.manager = manager
        self.config = config

    #--------------------------------------------------------------------------
    def run(self):
        """The main routine for a thread's work.

        The thread pulls tasks from the manager's task queue and executes
        them until it encounters a death token.  The death token is a tuple
        of two Nones.
        """
        try:
            quit_request_detected = False
            while True:
                aFunction, arguments = self.manager.task_queue.get()
                if aFunction is None:
                    break
                if quit_request_detected:
                    continue
                try:
                    try:
                        args, kwargs = arguments
                    except ValueError:
                        args = arguments
                        kwargs = {}
                    aFunction(*args, **kwargs)  # execute the task
                except Exception:
                    self.config.logger.error("Error in processing a job",
                                             exc_info=True)
                except KeyboardInterrupt:  # TODO: can probably go away
                    self.config.logger.info('quit request detected')
                    quit_request_detected = True
                    #thread.interrupt_main()  # only needed if signal handler
                                             # not registered
        except Exception:
            self.config.logger.critical("Failure in task_queue", exc_info=True)
