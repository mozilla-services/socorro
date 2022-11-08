# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import dataclasses
import inspect
import sys
from typing import Any, Dict, List

from .rules import (
    AbortSignature,
    BadHardware,
    OOMSignature,
    SigFixWhitespace,
    SignatureGenerationRule,
    SignatureIPCChannelError,
    SignatureIPCMessageName,
    SignatureParentIDNotEqualsChildID,
    SignatureRunWatchDog,
    SignatureShutdownTimeout,
    SigTruncate,
    StackOverflowSignature,
    StackwalkerErrorSignatureRule,
)


DEFAULT_RULESET = [
    SignatureGenerationRule,
    StackwalkerErrorSignatureRule,
    BadHardware,
    OOMSignature,
    AbortSignature,
    SignatureShutdownTimeout,
    SignatureRunWatchDog,
    SignatureIPCChannelError,
    SignatureIPCMessageName,
    SignatureParentIDNotEqualsChildID,
    StackOverflowSignature,
    # NOTE(willkg): These should always come last and in this order
    SigFixWhitespace,
    SigTruncate,
]


@dataclasses.dataclass
class Result:
    signature: str = ""
    notes: List[str] = dataclasses.field(default_factory=list, repr=False)
    debug_log: List[str] = dataclasses.field(default_factory=list, repr=False)
    extra: Dict[str, Any] = dataclasses.field(default_factory=dict, repr=False)

    def set_signature(self, rule, signature):
        self.debug(rule, 'change signature: "%s" -> "%s"', self.signature, signature)
        self.signature = signature

    def info(self, rule, msg, *args):
        if args:
            msg = msg % args
        self.notes.append("%s: %s" % (rule, msg))

    def debug(self, rule, msg, *args):
        if args:
            msg = msg % args
        self.debug_log.append("%s: %s" % (rule, msg))

    def to_dict(self):
        return {
            "signature": self.signature,
            "notes": self.notes,
            "debug_log": self.debug_log,
            "extra": self.extra,
        }


class SignatureGenerator:
    def __init__(self, ruleset=None, error_handler=None, **cfg):
        """
        :param ruleset: list of rule classes to use for signature generation
        :param error_handler: error handling function with signature
            ``fun(signature_data, exc_info, extra)``
        :param cfg: configuration keyword arguments to pass to rules being
            instantiated

        """
        self.error_handler = error_handler
        self.pipeline = self.initialize_pipeline(
            ruleset or list(DEFAULT_RULESET), **cfg
        )

    def initialize_pipeline(self, ruleset, **cfg):
        """Initialize a pipeline of rules

        For each rule in the ruleset:

        * if the rule is an instance, adds it to pipeline
        * if the rule is a class, uses introspection to determine the configuration
          required and instantiates the rule class with that

        :param ruleset: list of rule instances and classes
        :param cfg: configuration kwargs to pass to rules being instantiated; see each
            rule's documentation for what configuration is supported

        :returns: list of rule instances

        """
        pipeline = []
        for rule in ruleset:
            instance = None
            if inspect.isclass(rule):
                fun_signature = inspect.signature(rule)
                kwargs = {}
                for key, param in fun_signature.parameters.items():
                    if (
                        param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD
                        and key in cfg
                    ):
                        kwargs[key] = cfg[key]

                instance = rule(**kwargs)
            else:
                instance = rule
            pipeline.append(instance)
        return pipeline

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
