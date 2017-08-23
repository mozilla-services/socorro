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


PIPELINE = [
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
]


SIGNATURE_MAX_LENGTH = 255


logger = logging.getLogger(__name__)


class FakeConfig:
    def setdefault(self, key, value):
        setattr(self, key, getattr(self, key, value))
        return getattr(self, key)


class SignatureGenerator:
    def __init__(self, config=None):
        # FIXME(willkg): Redo this because it's sillypants
        if not config:
            config = FakeConfig()
            config.java_signature = FakeConfig()
            config.java_signature.java_signature_tool_class = JavaSignatureTool
            config.java_signature.signature_max_len = SIGNATURE_MAX_LENGTH
            config.java_signature.signature_escape_single_quote = True

            config.c_signature = FakeConfig()
            config.c_signature.c_signature_tool_class = CSignatureTool
            config.c_signature.maximum_frames_to_consider = 40
            config.c_signature.signature_max_len = SIGNATURE_MAX_LENGTH
            config.c_signature.signature_escape_single_quote = True

            config.signature_max_len = SIGNATURE_MAX_LENGTH
            config.signature_escape_single_quote = True

            config.logger = logger

        self.config = config

        # Instantiate all the rules in the signature pipeline
        self.pipeline = [rule(config) for rule in PIPELINE]

    def _send_to_sentry(self, rule, raw_crash, processed_crash):
        """Execute this when an exception has happened only

        If self.config.sentry.dsn is set up, it will try to send it to Sentry. If not configured,
        nothing happens.

        """
        try:
            dsn = self.config.sentry.dsn
        except (KeyError, AttributeError):
            # if self.config is not a DotDict, we can't access the sentry.dsn
            self.config.logger.warning(
                'Raven DSN is not configured and an exception happened'
            )
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
                self.config.logger.info(
                    'Error captured in Sentry! Reference: {}'.format(identifier)
                )
                return True  # it worked!
            finally:
                client.context.clear()
        except Exception:
            self.config.logger.error('Unable to report error with Raven', exc_info=True)

    def generate(self, raw_crash, processed_crash):
        """Takes data and returns a signature string"""
        notes = []

        for rule in self.pipeline:
            try:
                self.config.logger.debug(rule.__class__.__name__)
                if rule.predicate(raw_crash, processed_crash, notes):
                    rule.action(raw_crash, processed_crash, notes)
                self.config.logger.debug('    Signature: %r' % processed_crash['signature'])

            except Exception as exc:
                self._send_to_sentry(rule, raw_crash, processed_crash)
                self.config.logger.debug(
                    'Rule %s failed: "%s"',
                    str(rule.__class__),
                    exc,
                    exc_info=True
                )
                notes.append('Rule %s failed: %s' % (rule.__class__.__name__, exc))

        return {
            'signature': processed_crash['signature'],
            'notes': notes
        }
