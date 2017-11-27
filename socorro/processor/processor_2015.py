# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""this file defines the method of converting a raw crash into a processed
crash.  In this latest version, all transformations have been reimplemented
as sets of loadable rules.  The rules are applied one at a time, each doing
some small part of the transformation process."""

import ujson

from configman import Namespace, RequiredConfig, class_converter
from configman.dotdict import DotDict as OrderedDotDict

from socorro.lib.datetimeutil import utc_now
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
        "transform_rules",
        "socorro.processor.mozilla_transform_rules.ProductRewrite,"
        "socorro.processor.mozilla_transform_rules.ESRVersionRewrite,"
        "socorro.processor.mozilla_transform_rules.PluginContentURL,"
        "socorro.processor.mozilla_transform_rules.PluginUserComment,"
        # rules to transform a raw crash into a processed crash
        "socorro.processor.general_transform_rules.IdentifierRule, "
        "socorro.processor.breakpad_transform_rules.BreakpadStackwalkerRule2015, "
        "socorro.processor.mozilla_transform_rules.ProductRule, "
        "socorro.processor.mozilla_transform_rules.UserDataRule, "
        "socorro.processor.mozilla_transform_rules.EnvironmentRule, "
        "socorro.processor.mozilla_transform_rules.PluginRule, "
        "socorro.processor.mozilla_transform_rules.AddonsRule, "
        "socorro.processor.mozilla_transform_rules.DatesAndTimesRule, "
        "socorro.processor.mozilla_transform_rules.OutOfMemoryBinaryRule, "
        "socorro.processor.mozilla_transform_rules.JavaProcessRule, "
        "socorro.processor.mozilla_transform_rules.Winsock_LSPRule, "
        # post processing of the processed crash
        "socorro.processor.breakpad_transform_rules.CrashingThreadRule, "
        "socorro.processor.general_transform_rules.CPUInfoRule, "
        "socorro.processor.general_transform_rules.OSInfoRule, "
        "socorro.processor.mozilla_transform_rules.BetaVersionRule, "
        "socorro.processor.mozilla_transform_rules.ExploitablityRule, "
        "socorro.processor.mozilla_transform_rules.AuroraVersionFixitRule, "
        "socorro.processor.mozilla_transform_rules.FlashVersionRule, "
        "socorro.processor.mozilla_transform_rules.OSPrettyVersionRule, "
        "socorro.processor.mozilla_transform_rules.TopMostFilesRule, "
        "socorro.processor.mozilla_transform_rules.ThemePrettyNameRule, "
        "socorro.processor.rules.memory_report_extraction.MemoryReportExtraction, "
        # a set of classifiers to help with jit crashes
        "socorro.processor.breakpad_transform_rules.JitCrashCategorizeRule, "
        # generate signature now that we've done all the processing it depends on
        'socorro.processor.mozilla_transform_rules.SignatureGeneratorRule, '
    ]
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
            #name = "raw_to_processed_transform"
            names.append(name)
            required_config.namespace(name)

            required_config[name].add_option(
                name='rules_list',
                doc='a list of fully qualified class names for the rules',
                default=default_rules_str,
                from_string_converter=str_to_classes_in_namespaces_converter(),
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

        self.rule_system = OrderedDotDict()
        self.rules = []

        # here we instantiate the rule sets and their rules.
        if 'transform_rules' not in config:
            return  # no rules

        self.config.logger.debug('setting up transform_rules')

        # begin TRS insert
        trs_config = config['transform_rules']

        list_of_rules = trs_config.rules_list.class_list

        for a_rule_class_name, a_rule_class, ns_name in list_of_rules:
            try:
                self.rules.append(
                    a_rule_class(trs_config[ns_name])
                )
            except KeyError:
                self.rules.append(
                    a_rule_class(trs_config)
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

            # apply_all_rules
            for rule in self.rules:
                predicate_result, action_result = rule.act(
                    raw_crash,
                    raw_dumps,
                    processed_crash,
                    processor_meta_data
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
        self.config.logger.debug('done closing rules')
        for rule in self.rules:
            try:
                self.config.logger.debug('trying to close %s',
                                         rule.__class__)
                close_method = rule.close
            except AttributeError:
                self.config.logger.debug('%s has no close',
                                         rule.__class__)
                # no close method mean no need to close
                continue
            close_method()


def str_to_classes_in_namespaces_converter():

    def class_list_converter(class_list_str):
        """This function becomes the actual converter used by configman to
        take a string and convert it into the nested sequence of Namespaces,
        one for each class in the list.  It does this by creating a proxy
        class stuffed with its own 'required_config' that's dynamically
        generated."""
        if isinstance(class_list_str, basestring):
            class_str_list = []
            for class_str_padded in class_list_str.split(','):
                class_str = class_str_padded.strip()
                if class_str:
                    class_str_list.append(class_str)

        else:
            raise TypeError('must be derivative of a basestring')

        class InnerClassList(RequiredConfig):
            """This nested class is a proxy list for the classes.  It collects
            all the config requirements for the listed classes and places them
            each into their own Namespace.
            """
            # we're dynamically creating a class here.  The following block of
            # code is actually adding class level attributes to this new class

            # 1st requirement for configman
            required_config = Namespace()

            # to help the programmer know what Namespaces we added
            subordinate_namespace_names = []

            # for each class in the class list
            class_list = []
            for class_list_element in class_str_list:
                a_class = class_converter(class_list_element)

                # figure out the Namespace name
                namespace_name = a_class.__name__
                class_list.append((namespace_name, a_class, namespace_name))
                subordinate_namespace_names.append(namespace_name)
                # create the new Namespace
                required_config.namespace(namespace_name)
                a_class_namespace = required_config[namespace_name]
                a_class_namespace.add_option(
                    'qualified_class_name',
                    doc='fully qualified classname',
                    default=class_list_element,
                    from_string_converter=class_converter,
                    likely_to_be_changed=True,
                )

        return InnerClassList  # result of class_list_converter

    return class_list_converter  # result of classes_in_namespaces_converter
