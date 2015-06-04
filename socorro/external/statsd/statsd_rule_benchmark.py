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
