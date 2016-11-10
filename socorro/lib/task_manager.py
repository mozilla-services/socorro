import time
import threading
import os

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
def respond_to_SIGTERM(signal_number, frame, target=None):
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
        target - an instance of a class that has a member called 'task_manager'
                 that is a derivative of the TaskManager class below.
    """
    if target:
        target.config.logger.info('detected SIGTERM')
        # by setting the quit flag to true, any calls to the 'quit_check'
        # method that is so liberally passed around in this framework will
        # result in raising the quit exception.  The current quit exception
        # is KeyboardInterrupt
        target.task_manager.quit = True
    else:
        raise KeyboardInterrupt


#==============================================================================
class TaskManager(RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
      'idle_delay',
      default=7,
      doc='the delay in seconds if no job is found'
    )
    required_config.add_option(
      'quit_on_empty_queue',
      default=False,
      doc='stop if the queue is empty'
    )

    #--------------------------------------------------------------------------
    def __init__(self, config,
                 job_source_iterator=default_iterator,
                 task_func=default_task_func):
        """
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
        super(TaskManager, self).__init__()
        self.config = config
        self._pid = os.getpid()
        self.logger = config.logger
        self.job_param_source_iter = job_source_iterator
        self.task_func = task_func
        self.quit = False
        self.logger.debug('TaskManager finished init')

    #--------------------------------------------------------------------------
    def quit_check(self):
        """this is the polling function that the threads periodically look at.
        If they detect that the quit flag is True, then a KeyboardInterrupt
        is raised which will result in the threads dying peacefully"""
        if self.quit:
            raise KeyboardInterrupt

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
    def blocking_start(self, waiting_func=None):
        """this function starts the task manager running to do tasks.  The
        waiting_func is normally used to do something while other threads
        are running, but here we don't have other threads.  So the waiting
        func will never get called.  I can see wanting this function to be
        called at least once after the end of the task loop."""
        self.logger.debug('threadless start')
        try:
            for job_params in self._get_iterator():  # may never raise
                                                     # StopIteration
                self.config.logger.debug('received %r', job_params)
                self.quit_check()
                if job_params is None:
                    if self.config.quit_on_empty_queue:
                        raise KeyboardInterrupt
                    self.logger.info("there is nothing to do.  Sleeping "
                                     "for %d seconds" %
                                     self.config.idle_delay)
                    self._responsive_sleep(self.config.idle_delay)
                    continue
                self.quit_check()
                try:
                    args, kwargs = job_params
                except ValueError:
                    args = job_params
                    kwargs = {}
                try:
                    self.task_func(*args, **kwargs)
                except Exception:
                    self.config.logger.error("Error in processing a job",
                                             exc_info=True)
        except KeyboardInterrupt:
            self.logger.debug('queuingThread gets quit request')
        finally:
            self.quit = True
            self.logger.debug("ThreadlessTaskManager dies quietly")

    #--------------------------------------------------------------------------
    def executor_identity(self):
        """this function is likely to be called via the configuration parameter
        'executor_identity' at the root of the self.config attribute of the
        application.  It is most frequently used in the Pooled
        ConnectionContext classes to ensure that connections aren't shared
        between threads, greenlets, or whatever the unit of execution is.
        This is useful for maintaining transactional integrity on a resource
        connection."""
        return "%s-%s" % (self._pid, threading.currentThread().getName())

