# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import sys

import raven

from socorro.lib.revision_data import get_version


def get_client(dsn):
    return raven.Client(dsn=dsn, release=get_version())


def capture_error(sentry_dsn, logger=None, exc_info=None, extra=None):
    """Capture an error in sentry if able

    :arg sentry_dsn: the sentry dsn (or None)
    :arg logger: the logger to use
    :arg exc_info: the exception information as a tuple like from `sys.exc_info`
    :arg extra: any extra information to send along as a dict

    """
    logger = logger or logging.getLogger(__name__)

    exc_info = exc_info or sys.exc_info()

    if sentry_dsn:
        extra = extra or {}

        try:
            # Set up the Sentry client.
            client = get_client(sentry_dsn)
            client.context.activate()
            client.context.merge({'extra': extra})

            # Try to send the exception.
            try:
                identifier = client.captureException(exc_info)
                logger.info('Error captured in Sentry! Reference: %s' % identifier)

                # At this point, if everything is good, the exceptions were
                # successfully sent to sentry and we can return.
                return
            finally:
                client.context.clear()
        except Exception:
            # Log the exception from trying to send the error to Sentry.
            logger.error('Unable to report error with Raven', exc_info=True)

    # Sentry isn't configured or it's busted, so log the error we got that we
    # wanted to capture.
    logger.warning('Sentry DSN is not configured and an exception happened')
    logger.error('Exception occurred', exc_info=exc_info)
