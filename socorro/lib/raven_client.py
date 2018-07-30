# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys

from pkg_resources import resource_string
import raven

# When socorro is installed (python setup.py install), it will create
# a file in site-packages for socorro called "socorro/socorro_revision.txt".
# If this socorro was installed like that, let's pick it up and use it.
try:
    SOCORRO_REVISION = resource_string('socorro', 'socorro_revision.txt').strip()
except IOError:
    SOCORRO_REVISION = None


def get_client(dsn, **kwargs):
    kwargs['dsn'] = dsn
    if not kwargs.get('release') and SOCORRO_REVISION:
        kwargs['release'] = SOCORRO_REVISION
    return raven.Client(**kwargs)


def capture_error(sentry_dsn, logger, exc_info=None, extra=None):
    """Capture an error in sentry if able

    :arg sentry_dsn: the sentry dsn (or None)
    :arg logger: the logger to use
    :arg exc_info: the exception information as a tuple like from `sys.exc_info`
    :arg extra: any extra information to send along as a dict

    """
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
                logger.info('Error captured in Sentry! Reference: {}'.format(identifier))

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
