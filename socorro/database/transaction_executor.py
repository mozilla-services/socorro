# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import time

from configman.config_manager import RequiredConfig
from configman import Namespace

#------------------------------------------------------------------------------
def string_to_list_of_ints(a_string):
    a_string = a_string.replace('"', '')
    a_string = a_string.replace("'", "")
    ints_as_strings = a_string.split(',')
    return [int(x) for x in ints_as_strings]


#==============================================================================
class TransactionExecutor(RequiredConfig):
    required_config = Namespace()

    #--------------------------------------------------------------------------
    def __init__(self, config, db_conn_context_source,
                 quit_check_callback=None):
        self.config = config
        self.db_conn_context_source = db_conn_context_source
        self.quit_check = quit_check_callback or (lambda: False)
        self.do_quit_check = True

    #--------------------------------------------------------------------------
    def __call__(self, function, *args, **kwargs):
        """execute a function within the context of a transaction"""
        if self.do_quit_check:
            self.quit_check()
        with self.db_conn_context_source() as connection:
            try:
                #self.config.logger.debug('starting transaction')
                result = function(connection, *args, **kwargs)
                connection.commit()
                return result
            except:
                connection.rollback()
                self.config.logger.error(
                  'Exception raised during transaction',
                  exc_info=True)
                self.db_conn_context_source.force_reconnect()
                raise


#==============================================================================
class TransactionExecutorWithInfiniteBackoff(TransactionExecutor):
    # back off times
    required_config = Namespace()
    required_config.add_option('backoff_delays',
                               default="10, 30, 60, 120, 300",
                               doc='delays in seconds between retries',
                               from_string_converter=string_to_list_of_ints)
    # wait_log_interval
    required_config.add_option('wait_log_interval',
                               default=10,
                               doc='seconds between log during retries')

    #--------------------------------------------------------------------------
    def backoff_generator(self):
        """Generate a series of integers used for the length of the sleep
        between retries.  It produces after exhausting the list, it repeats
        the last value from the list forever.  This generator will never raise
        the StopIteration exception."""
        for x in self.config.backoff_delays:
            yield x
        while True:
            yield self.config.backoff_delays[-1]

    #--------------------------------------------------------------------------
    def responsive_sleep(self, seconds, wait_reason=''):
        """Sleep for the specified number of seconds, logging every
        'wait_log_interval' seconds with progress info."""
        for x in xrange(int(seconds)):
            if (self.config.wait_log_interval and
                not x % self.config.wait_log_interval):
                self.config.logger.debug(
                  '%s: %dsec of %dsec' % (wait_reason, x, seconds))
            self.quit_check()
            time.sleep(1.0)

    #--------------------------------------------------------------------------
    def __call__(self, function, *args, **kwargs):
        """execute a function within the context of a transaction"""
        for wait_in_seconds in self.backoff_generator():
            try:
                if self.do_quit_check:
                    self.quit_check()
                # self.db_conn_context_source is an instance of a
                # wrapper class on the actual connection driver
                with self.db_conn_context_source() as connection:
                    try:
                        result = function(connection, *args, **kwargs)
                        connection.commit()
                        return result
                    except:
                        connection.rollback()
                        raise
            except self.db_conn_context_source.conditional_exceptions, x:
                # these exceptions may or may not be retriable
                # the test is for is a last ditch effort to see if
                # we can retry
                if not self.db_conn_context_source.is_operational_exception(x):
                    self.config.logger.critical(
                      'Unrecoverable transaction error',
                       exc_info=True
                    )
                    raise
                self.config.logger.critical(
                  'transaction error eligible for retry',
                  exc_info=True)

            except self.db_conn_context_source.operational_exceptions:
                self.config.logger.critical(
                  'transaction error eligible for retry',
                  exc_info=True)
            self.db_conn_context_source.force_reconnect()
            self.config.logger.debug(
              'retry in %s seconds' % wait_in_seconds
            )
            self.responsive_sleep(
              wait_in_seconds,
              'waiting for retry after failure in transaction'
            )
        raise


#==============================================================================
class TransactionExecutorWithLimitedBackoff(
                                       TransactionExecutorWithInfiniteBackoff):
    #--------------------------------------------------------------------------
    def backoff_generator(self):
        """Generate a series of integers used for the length of the sleep
        between retries."""
        for x in self.config.backoff_delays:
            yield x
