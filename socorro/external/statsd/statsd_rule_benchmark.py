# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.statsd.statsd_base import (
    StatsdBenchmarkingWrapper as StatsdRuleBenchmarkWrapper,
)

# How is this class used?
#
# This class is used by specifying it in configuration instead of directly
# in code.  For example, say we have a processor rule in config that looks
# like this:
#
##[[[BreakpadStackwalkerRule2015]]]
##
##    # the template for the command to invoke the external program
##    command_line=timeout -s KILL 600 {command_pathname} --raw-json {raw_crash_pathname} --symbols-url {public_symbols_url} --symbols-url {private_symbols_url} --symbols-cache {symbol_cache_path} {dump_file_pathname} 2>/dev/null
##
##    # url of the private symbol server
##    private_symbols_url=https://s3-us-west-2.amazonaws.com/org.mozilla.crash-stats.symbols-private/v1
##
##    # url of the public symbol server
##    public_symbols_url=https://s3-us-west-2.amazonaws.com/org.mozilla.crash-stats.symbols-public/v1
##
##    # fully qualified classname
##    rule_class=socorro.processor.breakpad_transform_rules.BreakpadStackwalkerRule2015
##
##    # the path where the symbol cache is found, this location must be readable and writeable (quote path with embedded spaces)
##    symbol_cache_path=/tmp/symbols
##
#
# We leave the Namespace name of the rule alone.  But we change the
# implementation class and then add the orignal class as the
# "wrapped_object_class":
#
##    # fully qualified classname
##    rule_class=socorro.external.statsd.statsd_rule_benchmark.StatsdRuleBenchmarkWrapper
##
##    # fully qualified Python class path for an object to an be benchmarked
##    wrapped_object_class=socorro.processor.breakpad_transform_rules.BreakpadStackwalkerRule2015
#
# Then we add the requirements of statsd
#
##    statsd_host=...  # if the default isn't correct
##    statsd_port=...  # if the default isn't correct
##    statsd_prefix=processor
##    active_list=act  # <-- very important

from socorrolib.lib.transform_rules import Rule
from socorrolib.lib.converters import change_default

from configman import Namespace, class_converter

#==============================================================================
class CountAnythingRuleBase(Rule):
    required_config = Namespace()
    required_config.add_option(
        'counter_class',
        default="socorro.external.statsd.statsd_base.StatsdCounter",
        doc="the name of the class that implements the counter object",
        from_string_converter=class_converter
    )
    required_config.add_option(
        'rule_name',
        default='target_not_named',
        doc="the name to be used for this rule",
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(CountAnythingRuleBase, self).__init__(config)
        self.counter =  self.config.counter_class(self.config)

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        # override me to check any condition within a raw, processed crash
        # or even the state of the processor itself from the proc_meta
        raise NotImplementedError()

    #--------------------------------------------------------------------------
    def _action(self, raw_crash, raw_dumps, processed_crash, processor_meta):
        self.counter._incr(self.config.rule_name)


#==============================================================================
class CountStackWalkerTimeoutKills(CountAnythingRuleBase):
    required_config = Namespace()
    required_config.rule_name = change_default(
        CountAnythingRuleBase,
        'rule_name',
        'stackwalker_timeout_kills'
    )

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        # override me to check any condition within a raw, processed crash
        # or even the state of the processor itself from the proc_meta
        return reduce(
            lambda x, y: x or "SIGKILL" in y,
            proc_meta.processor_notes,
            False
        )


#==============================================================================
class CountStackWalkerFailures(CountAnythingRuleBase):
    required_config = Namespace()
    required_config.rule_name = change_default(
        CountAnythingRuleBase,
        'rule_name',
        'stackwalker_failures'
    )

    #--------------------------------------------------------------------------
    def _predicate(self, raw_crash, raw_dumps, processed_crash, proc_meta):
        # override me to check any condition within a raw, processed crash
        # or even the state of the processor itself from the proc_meta
        return reduce(
            lambda x, y: x or "MDSW failed" in y,
            proc_meta.processor_notes,
            False
        )


