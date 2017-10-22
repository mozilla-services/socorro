# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""this file defines the method of converting a raw crash into a processed
crash.  In this latest version, all transformations have been reimplemented
as sets of loadable rules.  The rules are applied one at a time, each doing
some small part of the transformation process."""

import ujson

from configman import Namespace, RequiredConfig
from configman.dotdict import DotDict as OrderedDotDict
# from configman.converters import str_to_python_object
from socorro.lib.converters import str_to_classes_in_namespaces_converter
from socorro.lib.datetimeutil import utc_now
from socorro.lib.transform_rules import TransformRuleSystem
from socorro.lib.util import DotDict


# Rule sets are defined as lists of lists (or tuples).  As they will be loaded
# from json, they will always come in a lists rather than tuples. Arguably,
# tuples may be more appropriate, but really, they can be anything iterable.

# The outermost sequence is a list of rule sets.  There can be any number of
# them and can be organized at will.  The example below shows an organization
# by processing stage: pre-processing the raw_crash, converter raw to
# processed, and post-processing the processed_crash.

# Each rule set is defined by five elements:
#    rule name: any useful string
#    tag: a categorization system, programmer defined system (for future)
#    rule set class: the fully qualified name of the class that implements
#                    the rule application process.  On the introduction of
#                    Processor2015, the only option is the one in the example.
#    rule list: a comma delimited list of fully qualified class names that
#               implement the individual transformation rules.  The API that
#               these classes must conform to is defined by the rule base class
#               socorro.lib.transform_rules.Rule
default_rule_set = [
    [   # rules to change the internals of the raw crash
        "raw_transform",  # name of the rule
        ""  # comma delimited list of fully qualified rule class names
    ],
    [   # rules to transform a raw crash into a processed crash
        "raw_to_processed_transform",
        ""
    ],
    [   # post processing of the processed crash
        "processed_transform",
        ""
    ],
]

# rules come into Socorro via Configman.  Configman defines them as strings
# conveniently, a json module can be used to serialize and deserialize them.
default_rules_set_str = ujson.dumps(default_rule_set)


def rule_sets_from_string(rule_sets_as_string):
    """this configman converter takes a json file in the form of a string,
    and converts it into rules sets for use in the processor.  See the
    default rule set above for the form."""
    rule_sets = ujson.loads(rule_sets_as_string)

    class ProcessorRuleSets(RequiredConfig):
        # why do rules come in sets?  Why not just have a big list of rules?
        # rule sets are containers for rules with a similar purpose and
        # execution mode.  For example, there are rule sets for adjusting the
        # raw_crash, transforming raw to processed, post processing the
        # processed_crash and then all the different forms of classifiers.
        # Some rule sets have different execution modes: run all the rules,
        # run the rules until one fails, run the rules until one succeeds,
        # etc.
        required_config = Namespace()

        names = []
        for (name, default_rules_str) in rule_sets:
            names.append(name)
            required_config.namespace(name)

            required_config[name].add_option(
                name='rules_list',
                doc='a list of fully qualified class names for the rules',
                default=default_rules_str,
                from_string_converter=str_to_classes_in_namespaces_converter(
                    name_of_class_option='rule_class'
                ),
                likely_to_be_changed=True,
            )

        @classmethod
        def to_str(klass):
            return "'%s'" % rule_sets_as_string

    return ProcessorRuleSets


class Processor2015(RequiredConfig):
    """this class is a generalization of the Processor into a rule processing
    framework. This class is suitable for use in the 'processor_app'
    introducted in 2012."""

    required_config = Namespace()
    required_config.add_option(
        name='rule_sets',
        doc="a hierarchy of rules in json form",
        default=default_rules_set_str,
        from_string_converter=rule_sets_from_string,
        likely_to_be_changed=True,
    )

    def __init__(self, config, quit_check_callback=None):
        super(Processor2015, self).__init__()
        self.config = config
        # the quit checks are components of a system of callbacks used
        # primarily by the TaskManager system.  This is the system that
        # controls the execution model.  If the ThreadedTaskManager is in use,
        # these callbacks just check the ThreadedTaskManager task manager's
        # quit flag.  If they detect a quit condition, they raise an exception
        # that causes the thread to shut down.  For the GreenletTaskMangager,
        # using cooperative multitasking, the callbacks do the 'yield' to
        # allow another green thread to take over.
        # It is perfectly acceptable to hook into this callback system to
        # accomplish any task that needs be done periodically.
        if quit_check_callback:
            self.quit_check = quit_check_callback
        else:
            self.quit_check = lambda: False

        # here we instantiate the rule sets and their rules.
        self.rule_system = OrderedDotDict()
        for a_rule_set_name in config.rule_sets.names:
            self.config.logger.debug(
                'setting up rule set: %s',
                a_rule_set_name
            )
            self.rule_system[a_rule_set_name] = (
                TransformRuleSystem(
                    config[a_rule_set_name],
                    self.quit_check
                )
            )

    def process_crash(self, raw_crash, raw_dumps, processed_crash):
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
        processor_meta_data.config = self.config

        if "processor_notes" in processed_crash:
            original_processor_notes = [
                x.strip() for x in processed_crash.processor_notes.split(";")
            ]
            processor_meta_data.processor_notes.append(
                "earlier processing: %s" % processed_crash.get(
                    "started_datetime",
                    'Unknown Date'
                )
            )
        else:
            original_processor_notes = []

        processed_crash.success = False
        processed_crash.started_datetime = utc_now()
        # for backwards compatibility:
        processed_crash.startedDateTime = processed_crash.started_datetime
        processed_crash.signature = 'EMPTY: crash failed to process'

        crash_id = raw_crash.get('uuid', 'unknown')
        try:
            # quit_check calls ought to be scattered around the code to allow
            # the processor to be responsive to requests to shut down.
            self.quit_check()

            processor_meta_data.started_timestamp = self._log_job_start(
                crash_id
            )

            # apply transformations
            #    step through each of the rule sets to apply the rules.
            for a_rule_set_name, a_rule_set in self.rule_system.iteritems():
                # for each rule set, invoke the 'act' method - this method
                # will be the method specified in fourth element of the
                # rule set configuration list.
                a_rule_set.apply_all_rules(
                    raw_crash,
                    raw_dumps,
                    processed_crash,
                    processor_meta_data,
                )
                self.quit_check()

            # the crash made it through the processor rules with no exceptions
            # raised, call it a success.
            processed_crash.success = True

        except Exception as exception:
            self.config.logger.warning(
                'Error while processing %s: %s',
                crash_id,
                str(exception),
                exc_info=True
            )
            processor_meta_data.processor_notes.append(
                'unrecoverable processor error: %s' % exception
            )

        # the processor notes are in the form of a list.  Join them all
        # together to make a single string
        processor_meta_data.processor_notes.extend(original_processor_notes)
        processed_crash.processor_notes = '; '.join(
            processor_meta_data.processor_notes
        )
        completed_datetime = utc_now()
        processed_crash.completed_datetime = completed_datetime
        # for backwards compatibility:
        processed_crash.completeddatetime = completed_datetime

        self._log_job_end(
            processed_crash.success,
            crash_id
        )
        return processed_crash

    def reject_raw_crash(self, crash_id, reason):
        self._log_job_start(crash_id)
        self.config.logger.warning('%s rejected: %s', crash_id, reason)
        self._log_job_end(False, crash_id)

    def _log_job_start(self, crash_id):
        self.config.logger.info("starting job: %s", crash_id)

    def _log_job_end(self, success, crash_id):
        self.config.logger.info(
            "finishing %s job: %s",
            'successful' if success else 'failed',
            crash_id
        )

    def close(self):
        for a_rule_set_name, a_rule_set in self.rule_system.iteritems():
            self.config.logger.debug('closing %s', a_rule_set_name)
            try:
                a_rule_set.close()
            except AttributeError:
                # guess we don't need to close that rule
                pass
        self.config.logger.debug('done closing rules')
