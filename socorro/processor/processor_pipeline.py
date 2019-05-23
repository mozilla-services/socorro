# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""this file defines the method of converting a raw crash into a processed
crash.  In this latest version, all transformations have been reimplemented
as sets of loadable rules.  The rules are applied one at a time, each doing
some small part of the transformation process."""

import logging
import os
import tempfile

from configman import (
    Namespace,
    RequiredConfig,
)
from configman.converters import str_to_list
from configman.dotdict import DotDict

from socorro.lib import sentry_client
from socorro.lib.datetimeutil import utc_now
from socorro.processor.rules.breakpad import (
    BreakpadStackwalkerRule2015,
    CrashingThreadRule,
    JitCrashCategorizeRule,
    MinidumpSha256Rule,
)
from socorro.processor.rules.general import (
    CPUInfoRule,
    DeNullRule,
    IdentifierRule,
    OSInfoRule,
)
from socorro.processor.rules.memory_report_extraction import (
    MemoryReportExtraction,
)
from socorro.processor.rules.mozilla import (
    AddonsRule,
    BetaVersionRule,
    DatesAndTimesRule,
    EnvironmentRule,
    ESRVersionRewrite,
    ExploitablityRule,
    FlashVersionRule,
    JavaProcessRule,
    MozCrashReasonRule,
    OSPrettyVersionRule,
    OutOfMemoryBinaryRule,
    PluginContentURL,
    PluginRule,
    PluginUserComment,
    ProductRewrite,
    ProductRule,
    SignatureGeneratorRule,
    ThemePrettyNameRule,
    TopMostFilesRule,
    UserDataRule,
)

DEFAULT_RULES = [
    # fix the raw crash removing null characters
    DeNullRule,
    # rules to change the internals of the raw crash
    ProductRewrite,
    ESRVersionRewrite,
    PluginContentURL,
    PluginUserComment,
    # rules to transform a raw crash into a processed crash
    IdentifierRule,
    MinidumpSha256Rule,
    BreakpadStackwalkerRule2015,
    ProductRule,
    UserDataRule,
    EnvironmentRule,
    PluginRule,
    AddonsRule,
    DatesAndTimesRule,
    OutOfMemoryBinaryRule,
    JavaProcessRule,
    MozCrashReasonRule,
    # post processing of the processed crash
    CrashingThreadRule,
    CPUInfoRule,
    OSInfoRule,
    BetaVersionRule,
    ExploitablityRule,
    FlashVersionRule,
    OSPrettyVersionRule,
    TopMostFilesRule,
    ThemePrettyNameRule,
    MemoryReportExtraction,
    # a set of classifiers to help with jit crashes
    JitCrashCategorizeRule,
    # generate signature now that we've done all the processing it depends on
    SignatureGeneratorRule,
]


class ProcessorPipeline(RequiredConfig):
    """this class is a generalization of the Processor into a rule processing
    framework. This class is suitable for use in the 'processor_app'
    introducted in 2012."""

    required_config = Namespace('transform_rules')
    required_config.add_option(
        'dump_field',
        doc='the default name of a dump',
        default='upload_file_minidump',
    )
    required_config.add_option(
        'command_pathname',
        doc='the full pathname to the external program to run (quote path with embedded spaces)',
        # NOTE(willkg): This is the path for the RPM-based Socorro deploy. When
        # we switch to Docker, we should change this.
        default='/data/socorro/stackwalk/bin/stackwalker',
    )
    required_config.add_option(
        'result_key',
        doc=(
            'the key where the external process result should be stored '
            'in the processed crash'
        ),
        default='stackwalker_result',
    )
    required_config.add_option(
        'return_code_key',
        doc=(
            'the key where the external process return code should be stored '
            'in the processed crash'
        ),
        default='stackwalker_return_code',
    )
    required_config.add_option(
        name='symbols_urls',
        doc='comma-delimited ordered list of urls for symbol lookup',
        default='https://localhost',
        from_string_converter=str_to_list,
        likely_to_be_changed=True
    )
    required_config.add_option(
        'command_line',
        doc='template for the command to invoke the external program; uses Python format syntax',
        default=(
            'timeout -s KILL {kill_timeout} {command_pathname} '
            '--raw-json {raw_crash_pathname} '
            '{symbols_urls} '
            '--symbols-cache {symbol_cache_path} '
            '--symbols-tmp {symbol_tmp_path} '
            '{dump_file_pathname}'
        )
    )
    required_config.add_option(
        'kill_timeout',
        doc='amount of time to let mdsw run before declaring it hung',
        default=600
    )
    required_config.add_option(
        'symbol_tmp_path',
        doc=(
            'directory to use as temp space for downloading symbols--must be '
            'on the same filesystem as symbols-cache'
        ),
        default=os.path.join(tempfile.gettempdir(), 'symbols-tmp'),
    ),
    required_config.add_option(
        'symbol_cache_path',
        doc=(
            'the path where the symbol cache is found, this location must be '
            'readable and writeable (quote path with embedded spaces)'
        ),
        default=os.path.join(tempfile.gettempdir(), 'symbols'),
    )
    required_config.add_option(
        'temporary_file_system_storage_path',
        doc='a path where temporary files may be written',
        default=tempfile.gettempdir(),
    )
    required_config.add_option(
        'version_string_api',
        doc='url for the version string api endpoint in the webapp',
        default='https://crash-stats.mozilla.org/api/VersionString'
    )

    def __init__(self, config, rules=None, quit_check_callback=None):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
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

        rule_set = rules or list(DEFAULT_RULES)

        self.rules = []
        for a_rule_class in rule_set:
            self.rules.append(a_rule_class(config))

    def process_crash(self, raw_crash, raw_dumps, processed_crash):
        """Take a raw_crash and its associated raw_dumps and return a processed_crash

        If this throws an exception, the crash was not processed correctly.

        """
        # processor_meta_data will be used to ferry "inside information" to
        # transformation rules. Sometimes rules need a bit more extra
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

        crash_id = raw_crash['uuid']

        # quit_check calls ought to be scattered around the code to allow
        # the processor to be responsive to requests to shut down.
        self.quit_check()

        start_time = self.logger.info('starting transform for crash: %s', crash_id)
        processor_meta_data.started_timestamp = start_time

        # Apply rules; if a rule fails, capture the error and continue onward
        for rule in self.rules:
            try:
                rule.act(raw_crash, raw_dumps, processed_crash, processor_meta_data)

            except Exception as exc:
                # If a rule throws an error, capture it and toss it in the
                # processor notes
                sentry_client.capture_error(
                    logger=self.logger,
                    extra={'crash_id': crash_id}
                )
                # NOTE(willkg): notes are public, so we can't put exception
                # messages in them
                processor_meta_data.processor_notes.append(
                    'rule %s failed: %s' % (rule.__class__.__name__, exc.__class__.__name__)
                )

            self.quit_check()

        # The crash made it through the processor rules with no exceptions
        # raised, call it a success
        processed_crash.success = True

        # The processor notes are in the form of a list.  Join them all
        # together to make a single string
        processor_meta_data.processor_notes.extend(original_processor_notes)
        processed_crash.processor_notes = '; '.join(processor_meta_data.processor_notes)
        completed_datetime = utc_now()
        processed_crash.completed_datetime = completed_datetime

        # For backwards compatibility
        processed_crash.completeddatetime = completed_datetime

        self.logger.info(
            "finishing %s transform for crash: %s",
            'successful' if processed_crash.success else 'failed',
            crash_id
        )
        return processed_crash

    def reject_raw_crash(self, crash_id, reason):
        self.logger.warning('%s rejected: %s', crash_id, reason)

    def close(self):
        self.logger.debug('closing rules')
        for rule in self.rules:
            rule.close()