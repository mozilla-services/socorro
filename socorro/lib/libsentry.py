# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import sys

import sentry_sdk


LOGGER = logging.getLogger(__name__)


def capture_error(use_logger=None, exc_info=None, extra=None):
    """Capture an error to send to Sentry

    If Sentry is configured, this will send it using capture_exception().

    If Sentry is not enabled, this will log it to the logger.

    :arg use_logger: the logger to use; defaults to the logger for this module
    :arg exc_info: the exception information as a tuple like from ``sys.exc_info``
    :arg extra: dict holding additional information to add to the scope before
        capturing this exception

    """
    use_logger = use_logger or LOGGER
    exc_info = exc_info or sys.exc_info()
    extra = extra or {}

    hub = sentry_sdk.Hub.current

    try:
        with sentry_sdk.push_scope() as scope:
            for key, value in extra.items():
                scope.set_extra(key, value)

            # Send the exception.
            identifier = hub.capture_exception(error=exc_info)
            use_logger.info("Error captured in Sentry! Reference: %s" % identifier)
    except Exception:
        # Log the exception from trying to send the error to Sentry.
        use_logger.error("Unable to report error with Sentry", exc_info=True)
        use_logger.error("Exception occurred", exc_info=exc_info)
