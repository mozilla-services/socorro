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
from typing import List

from attrs import define, field
from configman import Namespace, RequiredConfig
from configman.converters import str_to_list
import sentry_sdk

from socorro.lib.libdatetime import date_to_string, utc_now
from socorro.lib.libsocorrodataschema import get_schema
from socorro.processor.rules.breakpad import (
    CrashingThreadInfoRule,
    MinidumpSha256HashRule,
    MinidumpStackwalkRule,
    TruncateStacksRule,
)
from socorro.processor.rules.general import (
    CollectorMetadataRule,
    CPUInfoRule,
    CrashReportKeysRule,
    DeNoneRule,
    DeNullRule,
    IdentifierRule,
    OSInfoRule,
)
from socorro.processor.rules.memory_report_extraction import MemoryReportExtraction
from socorro.processor.rules.mozilla import (
    AccessibilityRule,
    AddonsRule,
    BetaVersionRule,
    BreadcrumbsRule,
    ConvertModuleSignatureInfoRule,
    CopyFromRawCrashRule,
    DatesAndTimesRule,
    DistributionIdRule,
    ESRVersionRewrite,
    FenixVersionRewriteRule,
    JavaProcessRule,
    MajorVersionRule,
    ModulesInStackRule,
    ModuleURLRewriteRule,
    MacCrashInfoRule,
    MozCrashReasonRule,
    OSPrettyVersionRule,
    OutOfMemoryBinaryRule,
    PHCRule,
    PluginRule,
    SignatureGeneratorRule,
    SubmittedFromRule,
    ThemePrettyNameRule,
    TopMostFilesRule,
    UtilityActorsNameRule,
)


@define
class Status:
    notes: List[str] = field(factory=list)

    def add_note(self, note):
        self.notes.append(note)

    def add_notes(self, notes):
        self.notes.extend(notes)


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
            "--no-color "
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
                DeNullRule(),
                DeNoneRule(),
                # capture collector things
                CrashReportKeysRule(),
                CollectorMetadataRule(),
                # fix ModuleSignatureInfo if it needs fixing
                ConvertModuleSignatureInfoRule(),
                # rules to change the internals of the raw crash
                FenixVersionRewriteRule(),
                ESRVersionRewrite(),
                # rules to transform a raw crash into a processed crash
                CopyFromRawCrashRule(schema=get_schema("processed_crash.schema.yaml")),
                SubmittedFromRule(),
                IdentifierRule(),
                MinidumpSha256HashRule(),
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
                TruncateStacksRule(),
                MajorVersionRule(),
                PluginRule(),
                AccessibilityRule(),
                AddonsRule(),
                DatesAndTimesRule(),
                OutOfMemoryBinaryRule(),
                PHCRule(),
                BreadcrumbsRule(schema=get_schema("processed_crash.schema.yaml")),
                JavaProcessRule(),
                MacCrashInfoRule(),
                MozCrashReasonRule(),
                UtilityActorsNameRule(),
                # post processing of the processed crash
                CPUInfoRule(),
                DistributionIdRule(),
                OSInfoRule(),
                BetaVersionRule(
                    version_string_api=config.betaversion.version_string_api
                ),
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
        # Used for keeping track of processing notes we should save later
        status = Status()

        processed_crash["success"] = False
        start_time = utc_now()
        processed_crash["started_datetime"] = date_to_string(start_time)

        status.add_note(f">>> Start processing: {start_time} ({self.host_id})")

        processed_crash["signature"] = "EMPTY: crash failed to process"

        crash_id = raw_crash["uuid"]

        ruleset = self.rulesets.get(ruleset_name)
        if ruleset is None:
            status.add_note(f"error: no ruleset: {ruleset_name}")
            return processed_crash

        self.logger.info(f"starting transform {ruleset_name} for crash: {crash_id}")

        # Apply rules; if a rule fails, capture the error and continue onward
        for rule in ruleset:
            with sentry_sdk.push_scope() as scope:
                scope.set_extra("rule", rule.name)

                try:
                    rule.act(
                        raw_crash=raw_crash,
                        dumps=dumps,
                        processed_crash=processed_crash,
                        status=status,
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
                    status.add_note(
                        f"ruleset {ruleset_name!r} rule {rule.name!r} failed: "
                        f"{exc.__class__.__name__}"
                    )

        # The crash made it through the processor rules with no exceptions raised, call
        # it a success
        processed_crash["success"] = True

        # Add previous notes to processor history
        processor_history = processed_crash.get("processor_history", [])
        if processed_crash.get("processor_notes"):
            previous_notes = processed_crash["processor_notes"]
            processor_history.insert(0, previous_notes)
        processed_crash["processor_history"] = processor_history

        # Set notes to this processing pass' notes
        processed_crash["processor_notes"] = "\n".join(status.notes)

        # Set completed_datetime
        completed_datetime = utc_now()
        processed_crash["completed_datetime"] = date_to_string(completed_datetime)

        self.logger.info(
            "finishing %s transform for crash: %s",
            "successful" if processed_crash["success"] else "failed",
            crash_id,
        )
        return processed_crash

    def reject_raw_crash(self, crash_id, reason):
        self.logger.warning("%s rejected: %s", crash_id, reason)

    def close(self):
        self.logger.debug("closing rules")
        for rule in self.rules:
            rule.close()
