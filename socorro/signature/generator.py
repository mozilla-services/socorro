# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.signature.rules import (
    SignatureGenerationRule,
    StackwalkerErrorSignatureRule,
    OOMSignature,
    AbortSignature,
    SignatureShutdownTimeout,
    SignatureRunWatchDog,
    SignatureIPCChannelError,
    SignatureIPCMessageName,
    SigFixWhitespace,
    SigTruncate,
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
    SigFixWhitespace(),
    SigTruncate(),
]


logger = logging.getLogger(__name__)


class SignatureGenerator:
    def __init__(self, pipeline=None, error_handler=None, debug=False):
        self.pipeline = pipeline or list(DEFAULT_PIPELINE)
        self.error_handler = error_handler
        self.debug = debug

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
                if self.error_handler:
                    self.error_handler(
                        raw_crash,
                        processed_crash,
                        extra={'rule': rule.__class__.__name__}
                    )
                notes.append('Rule %s failed: %s' % (rule.__class__.__name__, exc))

            if notes:
                all_notes.extend(notes)

        return {
            'signature': processed_crash.get('signature', ''),
            'notes': all_notes
        }
