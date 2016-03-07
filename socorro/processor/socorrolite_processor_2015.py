import ujson

from socorro.processor.processor_2015 import Processor2015
from socorrolib.lib.converters import change_default

from configman import Namespace

#------------------------------------------------------------------------------
# these are the steps that define minimal processing of a crash.
# they are used to define the default rule configuration a
# crash processor based on Procesor2015

socorrolite_processor_rule_sets = [
    [   # rules to change the internals of the raw crash
        "raw_transform",
        "processor.json_rewrite",
        "socorrolib.lib.transform_rules.TransformRuleSystem",
        "apply_all_rules",
        ""
    ],
    [   # rules to transform a raw crash into a processed crash
        "raw_to_processed_transform",
        "processer.raw_to_processed",
        "socorrolib.lib.transform_rules.TransformRuleSystem",
        "apply_all_rules",
        "socorro.processor.general_transform_rules.IdentifierRule, "
        "socorro.processor.breakpad_transform_rules.BreakpadStackwalkerRule, "
        "socorro.processor.mozilla_transform_rules.DatesAndTimesRule, "
    ],
    [   # post processing of the processed crash
        "processed_transform",
        "processer.processed",
        "socorrolib.lib.transform_rules.TransformRuleSystem",
        "apply_all_rules",
        "socorro.processor.breakpad_transform_rules.CrashingThreadRule, "
        "socorro.processor.signature_utilities.SignatureGenerationRule,"
        "socorro.processor.signature_utilities.StackwalkerErrorSignatureRule, "
        "socorro.processor.signature_utilities.OOMSignature, "
        "socorro.processor.signature_utilities.SigTrunc, "
    ]
]


#==============================================================================
class SocorroLiteProcessorAlgorithm2015(Processor2015):
    """this is the class that processor uses to transform """

    required_config = Namespace()
    required_config.rule_sets = change_default(
        Processor2015,
        'rule_sets',
        ujson.dumps(socorrolite_processor_rule_sets)
    )
