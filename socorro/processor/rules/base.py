# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

import markus


metrics = markus.get_metrics("processor.rule")


class Rule:
    """Base class for transform rules

    Provides structure for calling rules during the processor pipeline and also
    has some useful utilities for rules.

    """

    def __init__(self):
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)

    def predicate(self, raw_crash, dumps, processed_crash, processor_meta_data):
        """Determines whether to run the action for this crash

        :arg raw_crash: the raw crash data
        :arg dumps: any minidumps associated with this crash
        :arg processed_crash: the processed crash
        :arg processor_meta_data: any notes or bookkeeping we need to keep about
            processing as we process

        :returns: True if the action should run, False otherwise

        """
        return True

    def action(self, raw_crash, dumps, processed_crash, processor_meta_data):
        """Executes the rule transforming the crash data

        :arg raw_crash: the raw crash data
        :arg dumps: any minidumps associated with this crash
        :arg processed_crash: the processed crash
        :arg processor_meta_data: any notes or bookkeeping we need to keep about
            processing as we process

        """
        return

    def act(self, raw_crash, dumps, processed_crash, processor_meta_data):
        """Runs predicate and action for a rule

        :arg raw_crash: the raw crash data
        :arg dumps: any minidumps associated with this crash
        :arg processed_crash: the processed crash
        :arg processor_meta_data: any notes or bookkeeping we need to keep about
            processing as we process

        """
        rule_name = self.__class__.__name__
        with metrics.timer("act.timing", tags=["rule:%s" % rule_name]):
            ret = self.predicate(
                raw_crash=raw_crash,
                dumps=dumps,
                processed_crash=processed_crash,
                processor_meta_data=processor_meta_data,
            )
            if ret:
                self.action(
                    raw_crash=raw_crash,
                    dumps=dumps,
                    processed_crash=processed_crash,
                    processor_meta_data=processor_meta_data,
                )

    def close(self):
        pass

    def generate_repr(self, keys=None):
        keys = keys or []
        return (
            "<"
            + self.__class__.__name__
            + "".join([" %s=%r" % (key, getattr(self, key, None)) for key in keys])
            + ">"
        )

    def __repr__(self):
        return self.generate_repr()
