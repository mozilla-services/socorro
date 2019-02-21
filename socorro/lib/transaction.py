# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
This module contains convenience classes for managing "transactions"
that involve doing something and then committing or rolling back
depending on what happened.
"""

from contextlib import contextmanager
import sys
import time

import six


@contextmanager
def transaction_context(connection_context):
    """Creates a transaction context

    The connection context must implement the following:

    * ``commit() -> None``

      Commits the transaction.

    * ``rollback() -> None``

      Rolls the transaction back.

    * ``logger``

      Python logger.

    :arg connection_context: the connection context to use

    :yields: the connection the context wraps

    """
    with connection_context() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            excinfo = sys.exc_info()
            try:
                conn.rollback()
            except Exception:
                # NOTE(willkg): This exception is effectively getting
                # swallowed. We're assuming it's a red herring for whatever
                # threw the original exception. In Python 3, we can chain them.
                conn.logger.exception('cannot rollback')
            six.reraise(*excinfo)


# Backoff amounts in seconds; last is a 0 so it doesn't sleep after the last
# failure before exiting the loop
BACKOFF_TIMES = [1, 1, 1, 1, 1, 0]


def retry(connection_context, quit_check, fun, **kwargs):
    """Runs the function retrying periodically

    The connection context must define the following:

    * ``is_retryable_exception(Exception) -> bool``

      If this returns true, then ``retry` will call ``force_reconnect()``,
      wait some time, and try again.

    * ``force_reconnect() -> None``

      Forces recreation of the connection the connection context wraps.

    :arg connection_context: the connection context
    :arg quit_check: the quit_check function
    :arg fun: the function to retry
    :arg kwargs: named arguments to pass to the function

    :returns: varies

    """
    last_failure = None

    for backoff_time in BACKOFF_TIMES:
        try:
            with connection_context() as conn:
                return fun(conn, **kwargs)
        except Exception as exc:
            last_failure = sys.exc_info()
            if connection_context.is_retryable_exception(exc):
                # Force a reconnection because that sometimes fixes things
                connection_context.force_reconnect()
            else:
                six.reraise(*last_failure)

        time.sleep(backoff_time)
        if quit_check is not None:
            quit_check()

    # If it gets here, it's because we've dropped out of the loop and there's
    # no more retry attempts, so reraise the last error
    six.reraise(*last_failure)
