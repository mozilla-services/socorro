# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import dataclasses
import sys
from typing import Any, Dict, List

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


@dataclasses.dataclass
class Result:
    signature: str = ""
    notes: List[str] = dataclasses.field(default_factory=list, repr=False)
    debug_log: List[str] = dataclasses.field(default_factory=list, repr=False)
    extra: Dict[str, Any] = dataclasses.field(default_factory=dict, repr=False)

    def set_signature(self, rule, signature):
        self.debug(rule, 'change: "%s" -> "%s"', self.signature, signature)
        self.signature = signature

    def info(self, rule, msg, *args):
        if args:
            msg = msg % args
        self.notes.append("%s: %s" % (rule, msg))

    def debug(self, rule, msg, *args):
        if args:
            msg = msg % args
        self.debug_log.append("%s: %s" % (rule, msg))


class SignatureGenerator:
    def __init__(self, pipeline=None, error_handler=None):
        """
        :arg pipeline: list of rules to use for signature generation
        :arg error_handler: error handling function with signature
            ``fun(signature_data, exc_info, extra)``

        """
        self.pipeline = pipeline or list(DEFAULT_PIPELINE)
        self.error_handler = error_handler

    def generate(self, signature_data):
        """Takes data and returns a signature

        :arg dict signature_data: data to use to generate a signature

        :returns: ``Result`` instance

        """
        result = Result()

        for rule in self.pipeline:
            rule_name = rule.__class__.__name__

            try:
                if rule.predicate(signature_data, result):
                    rule.action(signature_data, result)

            except Exception as exc:
                if self.error_handler:
                    self.error_handler(
                        signature_data,
                        exc_info=sys.exc_info(),
                        extra={"rule": rule_name},
                    )
                result.info(rule_name, "Rule failed: %s", exc)

        return result
