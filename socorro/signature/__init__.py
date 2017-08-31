# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

import raven

from socorro.signature.signature_utilities import (
    JavaSignatureTool,
    CSignatureTool,
    SignatureGenerationRule,
    StackwalkerErrorSignatureRule,
    OOMSignature,
    AbortSignature,
    SignatureShutdownTimeout,
    SignatureRunWatchDog,
    SignatureIPCChannelError,
    SignatureIPCMessageName,
    SigTrim,
    SigTrunc,
    SignatureJitCategory,
)


DEFAULT_PIPELINE = [
    SignatureGenerationRule(),
    StackwalkerErrorSignatureRule(),
    OOMSignature(),
    AbortSignature(),
    SignatureShutdownTimeout(),
    SignatureRunWatchDog(),
    SignatureIPCChannelError(),
    SignatureIPCMessageName(),
    SigTrim(),
    SigTrunc(),
    SignatureJitCategory(),
]


logger = logging.getLogger(__name__)


class SignatureGenerator:
    def __init__(self, pipeline=None):
        self.pipeline = pipeline or list(DEFAULT_PIPELINE)

    def _send_to_sentry(self, rule, raw_crash, processed_crash):
        """Execute this when an exception has happened only

        # FIXME(willkg): FIX THIS

        If self.config.sentry.dsn is set up, it will try to send it to Sentry. If not configured,
        nothing happens.

        """
        # FIXME(willkg): Fix this
        try:
            dsn = self.config.sentry.dsn
        except (KeyError, AttributeError):
            # if self.config is not a DotDict, we can't access the sentry.dsn
            logger.warning('Raven DSN is not configured and an exception happened')
            return

        extra = {
            'rule': rule.__class__.__name__,
        }

        if 'uuid' in raw_crash:
            extra['crash_id'] = raw_crash['uuid']

        try:
            client = raven.Client(dsn=dsn)
            client.context.activate()
            client.context.merge({'extra': extra})
            try:
                identifier = client.captureException()
                logger.info('Error captured in Sentry! Reference: {}'.format(identifier))
                # it worked!
                return True
            finally:
                client.context.clear()
        except Exception:
            logger.error('Unable to report error with Raven', exc_info=True)

    def generate(self, raw_crash, processed_crash):
        """Takes data and returns a signature string"""
        notes = []

        for rule in self.pipeline:
            try:
                logger.debug(rule.__class__.__name__)
                if rule.predicate(raw_crash, processed_crash, notes):
                    rule.action(raw_crash, processed_crash, notes)
                logger.debug('    -> %r' % processed_crash['signature'])

            except Exception as exc:
                self._send_to_sentry(rule, raw_crash, processed_crash)
                logger.debug('Rule %s failed: "%s"', str(rule.__class__), exc, exc_info=True)
                notes.append('Rule %s failed: %s' % (rule.__class__.__name__, exc))

        return {
            'signature': processed_crash['signature'],
            'notes': notes
        }
