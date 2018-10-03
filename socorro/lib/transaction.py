# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
This module contains convenience classes for managing "transactions"
that involve doing something and then committing or rolling back
depending on what happened.
"""

import sys
import time

from configman.config_manager import RequiredConfig
from configman import Namespace
from six import reraise


class NonFatalException(Exception):
    """Exception for a non-fatal transaction that doesn't require reconnecting"""


def string_to_list_of_ints(a_string):
    a_string = a_string.replace('"', '')
    a_string = a_string.replace("'", "")
    ints_as_strings = a_string.split(',')
    return [int(x) for x in ints_as_strings]


class TransactionExecutor(RequiredConfig):
    required_config = Namespace()

    def __init__(self, config, db_conn_context_source, quit_check_callback=None):
        self.config = config
        self.db_conn_context_source = db_conn_context_source
        self.quit_check = quit_check_callback or (lambda: False)

    @property
    def connection_source_type(self):
        return self.db_conn_context_source.__module__

    def __call__(self, function, *args, **kwargs):
        """execute a function within the context of a transaction"""
        self.quit_check()
        with self.db_conn_context_source() as connection:
            try:
                result = function(connection, *args, **kwargs)
                connection.commit()
                return result
            except NonFatalException:
                # This is a non-fatal exception so we don't need to reconnect
                connection.rollback()
                raise
            except BaseException:
                # This is possibly a fatal exception requiring a reconnect
                excinfo = sys.exc_info()
                connection.rollback()
                self.config.logger.error(
                    'Fatal exception raised during %s transaction; will reconnect',
                    self.connection_source_type,
                    exc_info=True
                )
                self.db_conn_context_source.force_reconnect()
                reraise(*excinfo)


class TransactionExecutorWithInfiniteBackoff(TransactionExecutor):
    # back off times
    required_config = Namespace()
    required_config.add_option(
        'backoff_delays',
        default="10, 30, 60, 120, 300",
        doc='delays in seconds between retries',
        from_string_converter=string_to_list_of_ints
    )
    # wait_log_interval
    required_config.add_option(
        'wait_log_interval',
        default=10,
        doc='seconds between log during retries'
    )

    def backoff_generator(self):
        """Generate a series of integers used for the length of the sleep
        between retries.  It produces after exhausting the list, it repeats
        the last value from the list forever.  This generator will never raise
        the StopIteration exception."""
        for x in self.config.backoff_delays:
            yield x
        while True:
            yield self.config.backoff_delays[-1]

    def responsive_sleep(self, seconds, wait_reason=''):
        """Sleep for the specified number of seconds, logging every
        'wait_log_interval' seconds with progress info."""
        for x in range(int(seconds)):
            if self.config.wait_log_interval and not x % self.config.wait_log_interval:
                self.config.logger.debug('%s: %dsec of %dsec' % (wait_reason, x, seconds))
            self.quit_check()
            time.sleep(1.0)

    def __call__(self, function, *args, **kwargs):
        """execute a function within the context of a transaction"""
        last_failure = None
        for wait_in_seconds in self.backoff_generator():
            try:
                self.quit_check()
                # self.db_conn_context_source is an instance of a
                # wrapper class on the actual connection driver
                with self.db_conn_context_source() as connection:
                    try:
                        result = function(connection, *args, **kwargs)
                        connection.commit()
                        return result
                    except Exception:
                        connection.rollback()
                        last_failure = sys.exc_info()
                        reraise(*last_failure)

            except self.db_conn_context_source.conditional_exceptions as x:
                # these exceptions may or may not be retriable
                # the test is for is a last ditch effort to see if
                # we can retry
                if not self.db_conn_context_source.is_operational_exception(x):
                    # If the logger exists, log the issue, otherwise print it
                    # to stdout.
                    if self.config.logger:
                        self.config.logger.critical(
                            'Unrecoverable %s transaction error',
                            self.connection_source_type,
                            exc_info=True
                        )
                    else:
                        print('Unrecoverable %s transaction error' % self.connection_source_type)
                    reraise(*last_failure)
                self.config.logger.critical(
                    '%s transaction error eligible for retry',
                    self.connection_source_type,
                    exc_info=True
                )

            except self.db_conn_context_source.operational_exceptions:
                self.config.logger.critical(
                    '%s transaction error eligible for retry',
                    self.connection_source_type,
                    exc_info=True
                )

            except BaseException as x:
                reraise(*last_failure)

            self.db_conn_context_source.force_reconnect()
            self.config.logger.debug('retry in %s seconds' % wait_in_seconds)
            self.responsive_sleep(
                wait_in_seconds,
                'waiting for retry after failure in %s transaction' % self.connection_source_type,
            )
        if last_failure is not None:
            reraise(*last_failure)


class TransactionExecutorWithLimitedBackoff(TransactionExecutorWithInfiniteBackoff):
    def backoff_generator(self):
        """Generate a series of integers used for the length of the sleep
        between retries."""
        for x in self.config.backoff_delays:
            yield x
