# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

try:
    import raven
except ImportError:
    raven = None

from socorro.signature.rules import (
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
    SignatureParentIDNotEqualsChildID,
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
    SignatureParentIDNotEqualsChildID(),
    SignatureJitCategory(),

    # NOTE(willkg): These should always come last and in this order
    SigTrim(),
    SigTrunc(),
]


logger = logging.getLogger(__name__)


class SignatureGenerator:
    def __init__(self, pipeline=None, sentry_dsn=None, debug=False):
        self.pipeline = pipeline or list(DEFAULT_PIPELINE)
        self.sentry_dsn = sentry_dsn
        self.debug = debug

    def _send_to_sentry(self, rule, raw_crash, processed_crash):
        """Sends an unhandled error to Sentry

        If self.sentry_dsn is non-None, it will try to send it to Sentry.

        """
        if self.sentry_dsn is None:
            logger.warning('Sentry DSN is not configured and an exception happened')
            return

        extra = {
            'rule': rule.__class__.__name__,
        }

        if 'uuid' in raw_crash:
            extra['crash_id'] = raw_crash['uuid']

        try:
            client = raven.Client(dsn=self.sentry_dsn)
            client.context.activate()
            client.context.merge({'extra': extra})
            try:
                identifier = client.captureException()
                logger.info('Error captured in Sentry! Reference: {}'.format(identifier))

            finally:
                client.context.clear()
        except Exception:
            logger.error('Unable to report error with Raven', exc_info=True)

    def generate(self, raw_crash, processed_crash):
        """Takes data and returns a signature

        :arg dict raw_crash: the raw crash data
        :arg dict processed_crash: the processed crash data

        :returns: dict containing ``signature`` and ``notes`` keys representing the
            signature and processor notes

        """
        all_notes = []

        for rule in self.pipeline:
            notes = []
            try:
                if rule.predicate(raw_crash, processed_crash):
                    sig = processed_crash.get('signature', '')
                    rule.action(raw_crash, processed_crash, notes)
                    if self.debug:
                        notes.append('%s: %s -> %s' % (
                            rule.__class__.__name__, sig, processed_crash['signature']
                        ))

            except Exception as exc:
                self._send_to_sentry(rule, raw_crash, processed_crash)
                notes.append('Rule %s failed: %s' % (rule.__class__.__name__, exc))

            if notes:
                all_notes.extend(notes)

        return {
            'signature': processed_crash.get('signature', ''),
            'notes': all_notes
        }
