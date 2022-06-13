# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
import sys

import sentry_sdk


def is_enabled():
    """Return True if sentry was initialized with a DSN."""
    return (
        sentry_sdk.Hub.current.client
        and sentry_sdk.Hub.current.client.options["dsn"] is not None
    )


def get_hub():
    """Get the initialized Sentry hub.

    With a previous SDK (raven), this was called get_client, and initialized
    the it with a DSN. With the current SDK, this returns the Hub, and is
    mostly used to give tests something to test against.
    """
    return sentry_sdk.Hub.current


def capture_error(logger=None, exc_info=None, extra=None):
    """Capture an error in sentry if enabled.

    :arg logger: the logger to use
    :arg exc_info: the exception information as a tuple like from `sys.exc_info`
    :arg extra: any extra information to send along as a dict

    """
    logger = logger or logging.getLogger(__name__)

    exc_info = exc_info or sys.exc_info()

    if is_enabled():
        extra = extra or {}

        try:
            # Get the configured Sentry hub
            hub = get_hub()

            with sentry_sdk.push_scope() as scope:
                for key, value in extra.items():
                    scope.set_extra(key, value)

                # Send the exception.
                identifier = hub.capture_exception(error=exc_info)
                logger.info("Error captured in Sentry! Reference: %s" % identifier)

                # At this point, if everything is good, the exceptions were
                # successfully sent to sentry and we can return.
                return
        except Exception:
            # Log the exception from trying to send the error to Sentry.
            logger.error("Unable to report error with Sentry", exc_info=True)

    # Sentry isn't configured or it's busted, so log the error we got that we
    # wanted to capture.
    logger.warning("Sentry DSN is not configured and an exception happened")
    logger.error("Exception occurred", exc_info=exc_info)
