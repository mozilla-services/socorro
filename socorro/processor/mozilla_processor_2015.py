import ujson
from configman import Namespace

from socorro.processor.processor_2015 import Processor2015
from socorrolib.lib.converters import change_default

#------------------------------------------------------------------------------
# these are the steps that define processing a crash at Mozilla.
# they are used to define the default rule configuration for the Mozilla
# crash processor based on Procesor2015

mozilla_processor_rule_sets = [
    [   # rules to change the internals of the raw crash
        "raw_transform",
        "processor.json_rewrite",
        "socorrolib.lib.transform_rules.TransformRuleSystem",
        "apply_all_rules",
        "socorro.processor.mozilla_transform_rules.ProductRewrite,"
        "socorro.processor.mozilla_transform_rules.ESRVersionRewrite,"
        "socorro.processor.mozilla_transform_rules.PluginContentURL,"
        "socorro.processor.mozilla_transform_rules.PluginUserComment,"
        "socorro.processor.mozilla_transform_rules.FennecBetaError20150430"

    ],
    [   # rules to transform a raw crash into a processed crash
        "raw_to_processed_transform",
        "processer.raw_to_processed",
        "socorrolib.lib.transform_rules.TransformRuleSystem",
        "apply_all_rules",
        "socorro.processor.general_transform_rules.IdentifierRule, "
        "socorro.processor.breakpad_transform_rules"
            ".BreakpadStackwalkerRule2015, "
        "socorro.processor.mozilla_transform_rules.ProductRule, "
        "socorro.processor.mozilla_transform_rules.UserDataRule, "
        "socorro.processor.mozilla_transform_rules.EnvironmentRule, "
        "socorro.processor.mozilla_transform_rules.PluginRule, "
        "socorro.processor.mozilla_transform_rules.AddonsRule, "
        "socorro.processor.mozilla_transform_rules.DatesAndTimesRule, "
        "socorro.processor.mozilla_transform_rules.OutOfMemoryBinaryRule, "
        "socorro.processor.mozilla_transform_rules.JavaProcessRule, "
        "socorro.processor.mozilla_transform_rules.Winsock_LSPRule, "
    ],
    [   # post processing of the processed crash
        "processed_transform",
        "processer.processed",
        "socorrolib.lib.transform_rules.TransformRuleSystem",
        "apply_all_rules",
        "socorro.processor.breakpad_transform_rules.CrashingThreadRule, "
        "socorro.processor.general_transform_rules.CPUInfoRule, "
        "socorro.processor.general_transform_rules.OSInfoRule, "
        "socorro.processor.mozilla_transform_rules.BetaVersionRule, "
        "socorro.processor.mozilla_transform_rules.ExploitablityRule, "
        "socorro.processor.mozilla_transform_rules.FlashVersionRule, "
        "socorro.processor.mozilla_transform_rules.OSPrettyVersionRule, "
        "socorro.processor.mozilla_transform_rules.TopMostFilesRule, "
        "socorro.processor.mozilla_transform_rules.MissingSymbolsRule, "
        "socorro.processor.mozilla_transform_rules.ThemePrettyNameRule, "
        "socorro.processor.signature_utilities.SignatureGenerationRule,"
        "socorro.processor.signature_utilities.StackwalkerErrorSignatureRule, "
        "socorro.processor.signature_utilities.OOMSignature, "
        "socorro.processor.signature_utilities.AbortSignature, "
        "socorro.processor.signature_utilities.SignatureShutdownTimeout, "
        "socorro.processor.signature_utilities.SignatureRunWatchDog, "
        "socorro.processor.signature_utilities.SignatureIPCChannelError, "
        "socorro.processor.signature_utilities.SignatureIPCMessageName, "
        "socorro.processor.signature_utilities.SigTrunc, "
    ],
    [   # a set of classifiers for support
        "support_classifiers",
        "processor.support_classifiers",
        "socorrolib.lib.transform_rules.TransformRuleSystem",
        "apply_until_action_succeeds",
        "socorro.processor.support_classifiers.BitguardClassifier, "
        "socorro.processor.support_classifiers.OutOfDateClassifier"
    ],
    [   # a set of classifiers to help with jit crashes
        "jit_classifiers",
        "processor.jit_classifiers",
        "socorrolib.lib.transform_rules.TransformRuleSystem",
        "apply_all_rules",
        "socorro.processor.breakpad_transform_rules.JitCrashCategorizeRule, "
        "socorro.processor.signature_utilities.SignatureJitCategory, "
    ],
    [   # a set of special request classifiers
        "skunk_classifiers",
        "processor.skunk_classifiers",
        "socorrolib.lib.transform_rules.TransformRuleSystem",
        "apply_until_action_succeeds",
        "socorro.processor.skunk_classifiers.DontConsiderTheseFilter, "
        # currently not in use, anticipated to be re-enabled in the future
        #"socorro.processor.skunk_classifiers.UpdateWindowAttributes, "
        "socorro.processor.skunk_classifiers.SetWindowPos, "
        # currently not in use, anticipated to be re-enabled in the future
        #"socorro.processor.skunk_classifiers.SendWaitReceivePort, "
        # currently not in use, anticipated to be re-enabled in the future
        #"socorro.processor.skunk_classifiers.Bug811804, "
        # currently not in use, anticipated to be re-enabled in the future
        #"socorro.processor.skunk_classifiers.Bug812318, "
        "socorro.processor.skunk_classifiers.NullClassification"
    ]
]


#==============================================================================
class MozillaProcessorAlgorithm2015(Processor2015):
    """this is the class that processor uses to transform """

    required_config = Namespace()
    required_config.rule_sets = change_default(
        Processor2015,
        'rule_sets',
        ujson.dumps(mozilla_processor_rule_sets)
    )
