# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""this file defines the method of converting a raw crash into a processed
crash.  In this latest version, all transformations have been reimplemented
as sets of loadable rules.  The rules are applied one at a time, each doing
some small part of the transformation process."""

import logging
import os
import tempfile

from configman import Namespace, RequiredConfig
from configman.converters import str_to_list
from configman.dotdict import DotDict
import sentry_sdk

from socorro.lib.libdatetime import utc_now
from socorro.processor.rules.breakpad import (
    CrashingThreadInfoRule,
    MinidumpSha256Rule,
    MinidumpStackwalkRule,
)
from socorro.processor.rules.general import (
    CPUInfoRule,
    CrashReportKeysRule,
    DeNoneRule,
    DeNullRule,
    IdentifierRule,
    OSInfoRule,
)
from socorro.processor.rules.memory_report_extraction import MemoryReportExtraction
from socorro.processor.rules.mozilla import (
    AddonsRule,
    BetaVersionRule,
    BreadcrumbsRule,
    ConvertModuleSignatureInfoRule,
    CopyFromRawCrashRule,
    DatesAndTimesRule,
    DistributionIdRule,
    ESRVersionRewrite,
    ExploitablityRule,
    FenixVersionRewriteRule,
    FlashVersionRule,
    JavaProcessRule,
    MajorVersionRule,
    ModulesInStackRule,
    ModuleURLRewriteRule,
    MacCrashInfoRule,
    MozCrashReasonRule,
    OSPrettyVersionRule,
    OutOfMemoryBinaryRule,
    PHCRule,
    ProcessTypeRule,
    PluginContentURL,
    PluginRule,
    PluginUserComment,
    ProductRule,
    SignatureGeneratorRule,
    SubmittedFromRule,
    ThemePrettyNameRule,
    TopMostFilesRule,
)
from socorro.schemas import PROCESSED_CRASH_SCHEMA


class ProcessorPipeline(RequiredConfig):
    """Processor pipeline for Mozilla crash ingestion."""

    required_config = Namespace("transform_rules")

    # MinidumpStackwalkRule configuration
    required_config.minidumpstackwalk = Namespace()
    required_config.minidumpstackwalk.add_option(
        "dump_field", doc="the default name of a dump", default="upload_file_minidump"
    )
    required_config.minidumpstackwalk.add_option(
        "command_path",
        doc="absolute path to rust-minidump minidump-stackwalk binary",
        default="/stackwalk-rust/minidump-stackwalk",
    )
    required_config.minidumpstackwalk.add_option(
        name="symbols_urls",
        doc="comma-delimited ordered list of urls for symbol lookup",
        default="https://symbols.mozilla.org/",
        from_string_converter=str_to_list,
        likely_to_be_changed=True,
    )
    required_config.minidumpstackwalk.add_option(
        "command_line",
        doc=(
            "template for the command to invoke the external program; uses Python "
            "format syntax"
        ),
        default=(
            "timeout --signal KILL {kill_timeout} "
            "{command_path} "
            "--evil-json={raw_crash_path} "
            "--symbols-cache={symbol_cache_path} "
            "--symbols-tmp={symbol_tmp_path} "
            "{symbols_urls} "
            "--json "
            "--verbose=error "
            "{dump_file_path}"
        ),
    )
    required_config.minidumpstackwalk.add_option(
        "kill_timeout",
        doc="time in seconds to let minidump-stackwalk run before killing it",
        default=600,
    )
    required_config.minidumpstackwalk.add_option(
        "symbol_tmp_path",
        doc=(
            "absolute path to temp space for downloading symbols--must be on the same "
            "filesystem as symbol_cache_path"
        ),
        default=os.path.join(tempfile.gettempdir(), "symbols-tmp"),
    ),
    required_config.minidumpstackwalk.add_option(
        "symbol_cache_path",
        doc="absolute path to symbol cache",
        default=os.path.join(tempfile.gettempdir(), "symbols"),
    )
    required_config.minidumpstackwalk.add_option(
        "tmp_path",
        doc="a path where temporary files may be written",
        default=tempfile.gettempdir(),
    )

    # BetaVersionRule configuration
    required_config.betaversion = Namespace()
    required_config.betaversion.add_option(
        "version_string_api",
        doc="url for the version string api endpoint in the webapp",
        default="https://crash-stats.mozilla.org/api/VersionString",
    )

    def __init__(self, config, rules=None, host_id=None):
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(__name__ + "." + self.__class__.__name__)
        self.host_id = host_id or "unknown"
        self.rulesets = rules or self.get_rulesets(config)
        for ruleset_name, ruleset in self.rulesets.items():
            self.logger.info(f"Loading ruleset: {ruleset_name}")
            for rule in ruleset:
                self.logger.info(f"Loaded rule: {rule!r}")

    def get_rulesets(self, config):
        """Generate rule sets for Mozilla crash processing.

        :arg config: configman DotDict config instance

        :returns: dict of rulesets

        """
        # NOTE(willkg): the rulesets defined in here must match the set of
        # rulesets in webapp-django/crashstats/settings/base.py VALID_RULESETS
        # for them to be available to the Reprocessing API
        rulesets = {
            # The default processing pipeline
            "default": [
                # fix the raw crash removing null characters and Nones
                CrashReportKeysRule(),
                DeNullRule(),
                DeNoneRule(),
                # fix ModuleSignatureInfo if it needs fixing
                ConvertModuleSignatureInfoRule(),
                # rules to change the internals of the raw crash
                FenixVersionRewriteRule(),
                ESRVersionRewrite(),
                PluginContentURL(),
                PluginUserComment(),
                # rules to transform a raw crash into a processed crash
                CopyFromRawCrashRule(schema=PROCESSED_CRASH_SCHEMA),
                SubmittedFromRule(),
                ProcessTypeRule(),
                IdentifierRule(),
                MinidumpSha256Rule(),
                MinidumpStackwalkRule(
                    dump_field=config.minidumpstackwalk.dump_field,
                    symbols_urls=config.minidumpstackwalk.symbols_urls,
                    command_line=config.minidumpstackwalk.command_line,
                    command_path=config.minidumpstackwalk.command_path,
                    kill_timeout=config.minidumpstackwalk.kill_timeout,
                    symbol_tmp_path=config.minidumpstackwalk.symbol_tmp_path,
                    symbol_cache_path=config.minidumpstackwalk.symbol_cache_path,
                    tmp_path=config.minidumpstackwalk.tmp_path,
                ),
                ModuleURLRewriteRule(),
                CrashingThreadInfoRule(),
                ProductRule(),
                MajorVersionRule(),
                PluginRule(),
                AddonsRule(),
                DatesAndTimesRule(),
                OutOfMemoryBinaryRule(),
                PHCRule(),
                BreadcrumbsRule(),
                JavaProcessRule(),
                MacCrashInfoRule(),
                MozCrashReasonRule(),
                # post processing of the processed crash
                CPUInfoRule(),
                DistributionIdRule(),
                OSInfoRule(),
                BetaVersionRule(
                    version_string_api=config.betaversion.version_string_api
                ),
                ExploitablityRule(),
                FlashVersionRule(),
                OSPrettyVersionRule(),
                TopMostFilesRule(),
                ModulesInStackRule(),
                ThemePrettyNameRule(),
                MemoryReportExtraction(),
                # generate signature now that we've done all the processing it depends on
                SignatureGeneratorRule(),
            ],
            # Regenerate signatures
            "regenerate_signature": [
                SignatureGeneratorRule(),
            ],
        }

        return rulesets

    def process_crash(self, ruleset_name, raw_crash, dumps, processed_crash):
        """Process a crash

        This takes a raw_crash, associated minidump files, and a pre-existing
        processed_crash if there is one, and processed the crash into a new
        processed_crash.

        If this throws an exception, the crash was not processed correctly.

        """
        # processor_meta_data will be used to ferry "inside information" to
        # transformation rules. Sometimes rules need a bit more extra
        # information about the transformation process itself.
        processor_meta_data = DotDict()
        processor_meta_data.processor = self
        processor_meta_data.config = self.config
        processor_meta_data.processor_notes = []

        processed_crash.success = False
        start_time = utc_now()
        processed_crash.started_datetime = start_time

        processor_meta_data.processor_notes.append(
            f">>> Start processing: {start_time:%Y-%m-%d %H:%M:%S} ({self.host_id})"
        )

        processed_crash.signature = "EMPTY: crash failed to process"

        crash_id = raw_crash["uuid"]

        ruleset = self.rulesets.get(ruleset_name)
        if ruleset is None:
            processor_meta_data.processor_notes.append(
                f"error: no ruleset: {ruleset_name}"
            )
            return processed_crash

        self.logger.info(f"starting transform {ruleset_name} for crash: {crash_id}")
        processor_meta_data.started_timestamp = utc_now()

        # Apply rules; if a rule fails, capture the error and continue onward
        for rule in ruleset:
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("rule", rule.name)

                try:
                    rule.act(
                        raw_crash=raw_crash,
                        dumps=dumps,
                        processed_crash=processed_crash,
                        processor_meta_data=processor_meta_data,
                    )

                except Exception as exc:
                    sentry_sdk.capture_exception(exc)

                    self.logger.exception(
                        "error: crash id %s: rule %s: %r",
                        crash_id,
                        rule.name,
                        exc,
                    )

                    # NOTE(willkg): notes are public, so we can't put exception
                    # messages in them
                    processor_meta_data.processor_notes.append(
                        f"ruleset {ruleset_name!r} rule {rule.name!r} failed: "
                        f"{exc.__class__.__name__}"
                    )

        # The crash made it through the processor rules with no exceptions
        # raised, call it a success
        processed_crash.success = True

        # Join notes into a single string
        if processed_crash.get("processor_notes"):
            previous_notes = processed_crash["processor_notes"]
            previous_notes = [line.strip() for line in previous_notes.split("\n")]
            processor_meta_data.processor_notes.extend(previous_notes)

        processed_crash["processor_notes"] = "\n".join(
            processor_meta_data.processor_notes
        )
        completed_datetime = utc_now()
        processed_crash["completed_datetime"] = completed_datetime

        self.logger.info(
            "finishing %s transform for crash: %s",
            "successful" if processed_crash.success else "failed",
            crash_id,
        )
        return processed_crash

    def reject_raw_crash(self, crash_id, reason):
        self.logger.warning("%s rejected: %s", crash_id, reason)

    def close(self):
        self.logger.debug("closing rules")
        for rule in self.rules:
            rule.close()
