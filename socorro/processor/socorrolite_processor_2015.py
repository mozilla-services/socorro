from ujson import dumps

from socorro.processor.processor_2015 import Processor2015

#------------------------------------------------------------------------------
# these are the steps that define processing a crash at Mozilla.
# they are used to define the default rule configuration for the Mozilla
# crash processor based on Procesor2015

socorrolite_processor_rule_sets = [
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
        "socorro.processor.general_transform_rules.IdentifierRule, "
        "socorro.processor.breakpad_transform_rules.BreakpadStackwalkerRule, "
        "socorro.processor.mozilla_transform_rules.DatesAndTimesRule, "
    ],
    [   # post processing of the processed crash
        "processed_transform",
        "processer.processed",
        "socorro.lib.transform_rules.TransformRuleSystem",
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

    Processor2015.required_config.rule_sets.set_default(
        dumps(socorrolite_processor_rule_sets),
        force=True
    )

