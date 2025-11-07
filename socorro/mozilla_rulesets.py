# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from socorro import settings
from socorro.lib.libsocorrodataschema import get_schema
from socorro.processor.rules.android import (
    AndroidCPUInfoRule,
    AndroidOSInfoRule,
)
from socorro.processor.rules.breakpad import (
    CrashInconsistenciesRule,
    CrashingThreadInfoRule,
    HasGuardPageAccessRule,
    MinidumpSha256HashRule,
    MinidumpStackwalkRule,
    PossibleBitFlipsRule,
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
from socorro.processor.rules.java import JavaStackTraceRule
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
    MajorVersionRule,
    MissingSymbolsRule,
    ModulesInStackRule,
    ModuleURLRewriteRule,
    MacBootArgsRule,
    MacCrashInfoRule,
    MozCrashReasonRule,
    OSPrettyVersionRule,
    OutOfMemoryBinaryRule,
    PHCRule,
    PluginRule,
    ReportTypeRule,
    SignatureGeneratorRule,
    SoftErrorsRule,
    SubmittedFromRule,
    ThemePrettyNameRule,
    TopMostFilesRule,
    UtilityActorsNameRule,
)


DEFAULT_RULESET = [
    # fix the raw crash removing null characters and Nones
    DeNullRule(),
    DeNoneRule(),
    # capture collector things
    CrashReportKeysRule(),
    CollectorMetadataRule(),
    # fix ModuleSignatureInfo if it needs fixing
    ConvertModuleSignatureInfoRule(),
    # rules to transform a raw crash into a processed crash
    CopyFromRawCrashRule(schema=get_schema("processed_crash.schema.yaml")),
    FenixVersionRewriteRule(),
    ESRVersionRewrite(),
    SubmittedFromRule(),
    IdentifierRule(),
    MinidumpSha256HashRule(),
    MinidumpStackwalkRule(
        dump_field=settings.STACKWALKER["dump_field"],
        symbols_urls=settings.STACKWALKER["symbols_urls"],
        command_line=settings.STACKWALKER["command_line"],
        command_path=settings.STACKWALKER["command_path"],
        kill_timeout=settings.STACKWALKER["kill_timeout"],
        symbol_cache_path=settings.STACKWALKER["symbol_cache_path"],
        symbol_tmp_path=settings.STACKWALKER["symbol_tmp_path"],
    ),
    ModuleURLRewriteRule(),
    CrashingThreadInfoRule(),
    TruncateStacksRule(),
    PossibleBitFlipsRule(),
    CrashInconsistenciesRule(),
    HasGuardPageAccessRule(),
    MajorVersionRule(),
    PluginRule(),
    AccessibilityRule(),
    AddonsRule(),
    DatesAndTimesRule(),
    OutOfMemoryBinaryRule(),
    PHCRule(),
    BreadcrumbsRule(schema=get_schema("processed_crash.schema.yaml")),
    JavaStackTraceRule(),
    MacBootArgsRule(),
    MacCrashInfoRule(),
    MozCrashReasonRule(),
    UtilityActorsNameRule(),
    ReportTypeRule(),
    # post processing of the processed crash
    CPUInfoRule(),
    AndroidCPUInfoRule(),
    DistributionIdRule(),
    OSInfoRule(),
    AndroidOSInfoRule(),
    BetaVersionRule(
        version_string_api=settings.BETAVERSIONRULE_VERSION_STRING_API,
    ),
    OSPrettyVersionRule(),
    TopMostFilesRule(),
    ModulesInStackRule(),
    MissingSymbolsRule(),
    ThemePrettyNameRule(),
    MemoryReportExtraction(),
    # generate signature now that we've done all the processing it depends on
    SignatureGeneratorRule(),
    SoftErrorsRule(),
]


REGENERATE_SIGNATURE_RULESET = [
    SignatureGeneratorRule(),
]


RULESETS = {
    # NOTE(willkg): the rulesets defined in here must match the set of rulesets in
    # webapp/crashstats/settings/base.py VALID_RULESETS for them to be available to the
    # Reprocessing API
    "default": DEFAULT_RULESET,
    "regenerate_signature": REGENERATE_SIGNATURE_RULESET,
}
