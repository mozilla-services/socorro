# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""this file defines the method of converting a raw crash into a processed
crash.  In this latest version, all transformations have be reimplemented
as sets of loadable rules.  The rules are applied one at a time, each doing
some small part of the transformation process."""

import ujson

from configman import Namespace, RequiredConfig
from configman.converters import (
    str_to_python_object,
)
from socorro.lib.converters import str_to_classes_in_namespaces_converter
from socorro.lib.datetimeutil import utc_now
from socorro.lib.util import DotDict


#
default_rule_set = [
    [   # rules to change the internals of the raw crash
        "raw_transform",
        "processor.json_rewrite",
        "socorro.lib.transform_rules.TransformRuleSystem",
        "apply_all_rules",
        ""
    ],
    [   # rules to transform a raw crash into a processed crash
        "raw_to_processed_transform",
        "processer.raw_to_processed",
        "socorro.lib.transform_rules.TransformRuleSystem",
        "apply_all_rules",
        ""
    ],
    [   # post processing of the processed crash
        "processed_transform",
        "processer.processed",
        "socorro.lib.transform_rules.TransformRuleSystem",
        "apply_all_rules",
        ""
    ],
]

default_rules_set_str = ujson.dumps(default_rule_set)


#------------------------------------------------------------------------------
def rule_sets_from_string(rule_sets_as_string):
    """this configman converter takes a json file in the form of a string,
    and converts it into rules sets for use in the processor.  See the
    default rule set above for the form."""
    rule_sets = ujson.loads(rule_sets_as_string)

    class ProcessorRuleSets(RequiredConfig):
        # why do rules come it sets?  Why not just have a big list of rules?
        # rule sets are containers for rules with a similar purpose and
        # execution mode.  For example, there are rule sets for adjusting the
        # raw_crash, transforming raw to processed, post processing the
        # processed_crasnh and then all the different forms of classifiers.
        # Some rule sets have different execution modes: run all the rules,
        # run the rules until one fails, run the rules until one succeeds,
        # etc.
        required_config = Namespace()

        names = []
        for (name, tag, rule_set_class_str, action_str, default_rules_str) \
            in rule_sets:
            names.append(name)
            required_config.namespace(name)
            required_config[name].add_option(
                name='tag',
                doc='the lookup tag associated with this rule set',
                default=tag
            )
            required_config[name].add_option(
                name='rule_system_class',
                default=rule_set_class_str,
                doc='the fully qualified name of the rule system class',
                from_string_converter=str_to_python_object,
            )
            required_config[name].add_option(
                name='action',
                default=action_str,
                doc=(
                    'the name of the rule set method to run to processes '
                    'these rules'
                ),
            )
            required_config[name].add_option(
                name='rules_list',
                doc='a list of fully qualified class names for the rules',
                default=default_rules_str,
                from_string_converter=str_to_classes_in_namespaces_converter(),
            )

    return ProcessorRuleSets


#==============================================================================
class Processor2015(RequiredConfig):
    """this class is a generalization of the Processor into a rule processing
    framework. This class is suitable for use in the 'processor_app'
    introducted in 2012."""

    required_config = Namespace()
    required_config.add_option(
        name='rule_sets',
        doc="a heirarchy of rules in json form",
        default=default_rules_set_str,
        from_string_converter=rule_sets_from_string,
    )

    #--------------------------------------------------------------------------
    def __init__(self, config, quit_check_callback=None):
        super(Processor2015, self).__init__()
        self.config = config
        if quit_check_callback:
            self.quit_check = quit_check_callback
        else:
            self.quit_check = lambda: False

        self.rule_system = DotDict()
        for a_rule_set_name in config.rule_sets.names:
            self.rule_system[a_rule_set_name] = (
                config[a_rule_set_name].rule_system_class(
                    config[a_rule_set_name]
                )
            )
            self.config.logger.debug('setting up %s rules', a_rule_set_name)
            for a_rule in self.rule_system[a_rule_set_name].rules:
                self.config.logger.debug('   %s', a_rule.__class__.__name__)

    #--------------------------------------------------------------------------
    def convert_raw_crash_to_processed_crash(self, raw_crash, raw_dumps):
        """Take a raw_crash and its associated raw_dumps and return a
        processed_crash.
        """
        # processor_meta_data will be used to ferry "inside information" to
        # transformation rules.  Sometimes rules need a bit more extra
        # information about the transformation process itself.
        processor_meta_data = DotDict()
        processor_meta_data.processor_notes = [
            self.config.processor_name,
            self.__class__.__name__
        ]
        processor_meta_data.quit_check = self.quit_check
        processor_meta_data.processor = self

        # create the empty processed crash
        processed_crash = DotDict()
        processed_crash.success = False
        processed_crash.started_datetime = utc_now()
        # for backwards compatibility:
        processed_crash.startedDateTime = processed_crash.started_datetime
        processed_crash.signature = 'EMPTY: crash failed to process'

        crash_id = raw_crash.get('uuid', 'unknown')
        try:
            self.quit_check()
            processor_meta_data.started_timestamp = self._log_job_start(
                crash_id
            )

            # apply transformations
            #    step through each of the rule systems, applying the rules of
            #    each to.
            for a_rule_set in self.rule_system:
                a_rule_set.act(
                    raw_crash,
                    raw_dumps,
                    processed_crash,
                    processor_meta_data
                )
                self.quit_check()

            processed_crash.success = True

        except Exception, x:
            self.config.logger.warning(
                'Error while processing %s: %s',
                crash_id,
                str(x),
                exc_info=True
            )
            processor_meta_data.processor_notes.append(
                'unrecoverable processor error: %s' % x
            )

        processed_crash.processor_notes = '; '.join(
            processor_meta_data.processor_notes
        )
        completed_datetime = utc_now()
        processed_crash.completed_datetime = completed_datetime
        # for backwards compatibility:
        processed_crash.completeddatetime = completed_datetime

        self._log_job_end(
            completed_datetime,
            processed_crash.success,
            crash_id
        )
        return processed_crash

    #--------------------------------------------------------------------------
    def reject_raw_crash(self, crash_id, reason):
        self._log_job_start(crash_id)
        self.config.logger.warning('%s rejected: %s', crash_id, reason)
        self._log_job_end(utc_now(), False, crash_id)

    #--------------------------------------------------------------------------
    def _log_job_start(self, crash_id):
        self.config.logger.info("starting job: %s", crash_id)

    #--------------------------------------------------------------------------
    def _log_job_end(self, completed_datetime, success, crash_id):
        self.config.logger.info(
            "finishing %s job: %s",
            'successful' if success else 'failed',
            crash_id
        )
