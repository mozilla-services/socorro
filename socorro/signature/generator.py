# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys

from .rules import (
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


class SignatureGenerator:
    def __init__(self, pipeline=None, error_handler=None, debug=False):
        """
        :arg pipeline: list of rules to use for signature generation
        :arg error_handler: error handling function with signature
            ``fun(signature_data, exc_info, extra)``
        :arg debug: whether or not to be in debug mode which shows verbose
            output about what happend

        """
        self.pipeline = pipeline or list(DEFAULT_PIPELINE)
        self.error_handler = error_handler
        self.debug = debug

    def generate(self, signature_data):
        """Takes data and returns a signature

        :arg dict signature_data: data to use to generate a signature

        :returns: dict containing ``signature`` and ``notes`` keys representing the
            signature and processor notes

        """
        # NOTE(willkg): Rules mutate the result structure in-place
        result = {
            'signature': '',
            'notes': []
        }

        for rule in self.pipeline:
            rule_name = rule.__class__.__name__

            try:
                if rule.predicate(signature_data, result):
                    old_sig = result['signature']
                    rule.action(signature_data, result)

                    if self.debug:
                        result['notes'].append(
                            '%s: %s -> %s' % (rule_name, old_sig, result['signature'])
                        )

            except Exception as exc:
                if self.error_handler:
                    self.error_handler(
                        signature_data,
                        exc_info=sys.exc_info(),
                        extra={'rule': rule_name}
                    )

                result['notes'].append('Rule %s failed: %s' % (rule_name, exc))

        return result
