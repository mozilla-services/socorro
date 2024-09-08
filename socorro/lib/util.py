# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from functools import wraps
import traceback
import time

from more_itertools import peekable


class MaxAttemptsError(Exception):
    """Maximum attempts error."""

    def __init__(self, msg, ret=None):
        super().__init__(msg)
        self.return_value = ret


def wait_time_generator():
    """Return generator for wait times."""
    yield from [1] * 5


def retry(
    retryable_exceptions=Exception,
    retryable_return=None,
    wait_time_generator=wait_time_generator,
    sleep_function=time.sleep,
    module_logger=None,
):
    """Retry decorated function with wait times, max attempts, and logging.

    Example with defaults::

        @retry()
        def some_thing_that_fails():
            pass


    Example with arguments::

        import logging
        logger = logging.getLogger(__name__)

        @retry(
            retryable_exceptions=[SocketTimeout, ConnectionError],
            retryable_return=lambda resp: resp.status_code != 200,
            module_logger=logger
        )
        def some_thing_that_does_connections():
            pass


    :arg exception/list retryable_exceptions:
        Exception class or list of exception classes to catch and retry on.

        Any exceptions not in this list will bubble up.

        Defaults to ``Exception``.

    :arg fun retryable_return:
        A function that takes a function return and returns ``True`` to retry
        or ``False`` to stop retrying.

        This allows you to retry based on a failed exception or failed return.

    :arg wait_time_generator:
        Generator function that returns wait times until a maximum number of
        attempts have been tried.

    :arg fun sleep_function:
        Function that takes the current attempt number as an int and sleeps.

    :arg logger/None module_logger:
        If you want to log all the exceptions that are caught and retried,
        then provide a logger.

        Otherwise exceptions are silently ignored.

    :raises MaxAttemptsError: if the maximum number of attempts have occurred.
        If the error is an exception, then the actual exception is part of
        the exception chain. If the error is a return value, then the
        problematic return value is in ``return_value``.

    """
    if not isinstance(retryable_exceptions, type):
        retryable_exceptions = tuple(retryable_exceptions)

    if module_logger is not None:
        log_warning = module_logger.warning
    else:
        log_warning = lambda *args, **kwargs: None  # noqa

    def _retry_inner(fun):
        @wraps(fun)
        def _retry_fun(*args, **kwargs):
            attempts = 0
            wait_times = peekable(wait_time_generator())
            while True:
                try:
                    ret = fun(*args, **kwargs)
                    if retryable_return is None or not retryable_return(ret):
                        # This was a successful return--yay!
                        return ret

                    # The return value is "bad", so we log something and then
                    # do another iteration.
                    log_warning(
                        "%s: bad return, retry attempt %s",
                        fun.__qualname__,
                        attempts,
                    )

                    # If last attempt,
                    if not wait_times:
                        raise MaxAttemptsError(
                            "Maximum retry attempts; last return %r." % ret, ret
                        )

                except retryable_exceptions as exc:
                    # If it's a MaxAttemptsError, re-raise that
                    if isinstance(exc, MaxAttemptsError):
                        raise

                    # Retryable exception is thrown, so we log something and then do
                    # another iteration
                    log_warning(
                        "%s: exception %s, retry attempt %s",
                        fun.__qualname__,
                        exc,
                        attempts,
                    )

                    # If last attempt, raise MaxAttemptsError which will chain the
                    # current errror
                    if not wait_times:
                        raise MaxAttemptsError(
                            f"Maximum retry attempts: {exc!r}"
                        ) from exc

                sleep_function(next(wait_times))
                attempts += 1

        return _retry_fun

    return _retry_inner


# Bug 1911612: Temporary decorator to log the method name, arguments and traceback
# for each ESCrashStorage and SuperSearch method to better understand where ES gets
# used by the webapp.
def es_usage_logger(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        stack_trace = "".join(traceback.format_stack())
        class_name = self.__class__.__name__
        method_name = func.__name__
        self.logger.info(
            f"Bug 1911612,\n{class_name}.{method_name} method called,\nArguments were: {args}, {kwargs},\nTraceback:\n{stack_trace}",
        )

        # Call the original function with its arguments and ensure we
        # return whatever it returns.
        return func(self, *args, **kwargs)

    return wrapper
