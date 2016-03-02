# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import re

from itertools import (
    product as iter_product,
    ifilter,
)
from functools import partial

from collections import defaultdict, Sequence, MutableMapping
from contextlib import contextmanager

from configman import Namespace, RequiredConfig, class_converter
from configman.dotdict import DotDict as ConfigmanDotDict
from configman.converters import list_converter, to_str

from socorro.analysis.correlations import macdebugids
from socorro.analysis.correlations import addonids

from socorro.app.fetch_transform_save_app import (
    FetchTransformSaveWithSeparateNewCrashSourceApp
)

from socorrolib.lib.transform_rules import Rule
from socorrolib.lib.util import DotDict as SocorroDotDict
from socorrolib.lib.converters import change_default
from socorro.processor.processor_2015 import rule_sets_from_string
from socorro.processor.processor_app import ProcessorApp
from socorro.external.crashstorage_base import (
    CrashIDNotFound
)

#------------------------------------------------------------------------------
correlation_rule_sets = [
    [
        "correlation_rules",
        "correlation",
        "socorrolib.lib.transform_rules.TransformRuleSystem",
        "apply_all_rules",
        "socorro.analysis.correlations.core_count_rule"
            ".CorrelationCoreCountRule, "
        "socorro.analysis.correlations.interesting_rule"
            ".CorrelationInterestingModulesRule,"
        "socorro.analysis.correlations.interesting_rule"
            ".CorrelationInterestingModulesVersionsRule,"
        "socorro.analysis.correlations.interesting_rule"
            ".CorrelationInterestingAddonsRule,"
        "socorro.analysis.correlations.interesting_rule"
            ".CorrelationInterestingAddonsVersionsRule,"
    ],
]
correlation_rule_sets_as_string = json.dumps(correlation_rule_sets)


#==============================================================================
class CorrelationsApp(FetchTransformSaveWithSeparateNewCrashSourceApp):
    """"""
    app_name = 'correlations'
    app_version = '2.0'
    app_description = """the dbaron correlations scripts evolved"""

    required_config = Namespace()
    required_config.namespace('rules')
    required_config.rules.add_option(
        name='rule_sets',
        doc="a hierarchy of rules in json form",
        default=correlation_rule_sets_as_string,
        from_string_converter=rule_sets_from_string,
        likely_to_be_changed=True,
    )

    #--------------------------------------------------------------------------
    @staticmethod
    def get_application_defaults():
        return {
            "number_of_submissions": 'all',
            "source.crashstorage_class":
                'socorro.external.boto.crashstorage.BotoS3CrashStorage',
            "destination.crashstorage_class":
                'socorro.external.crashstorage_base.NullCrashStorage',
            "new_crash_source.new_crash_source_class":
                'socorro.external.postgresql.new_crash_source'
                '.PGPVNewCrashSource',
        }

    #--------------------------------------------------------------------------
    def _transform(self, crash_id):
        """Take a raw_crash and its associated raw_dumps and return a
        processed_crash.
        """
        try:
            processed_crash = self.source.get_unredacted_processed(
                crash_id
            )
        except CrashIDNotFound:
            self.config.logger.warning('%s cannot be found - skipping')
            raise

        raw_crash = {}
        raw_dumps = {}
        meta_data = {}

        # apply transformations
        #    step through each of the rule sets to apply the rules.
        for a_rule_set_name, a_rule_set in self.rule_system.iteritems():
            # for each rule set, invoke the 'act' method - this method
            # will be the method specified in fourth element of the
            # rule set configuration list.
            a_rule_set.act(
                raw_crash,
                raw_dumps,
                processed_crash,
                meta_data
            )
            self.quit_check()
        try:
            self.destination.save_processed(processed_crash)
            self.config.logger.info('saved - %s', crash_id)
        except Exception as x:
            self.config.logger.error(
                "writing raw: %s",
                str(x),
                exc_info=True
            )

    #--------------------------------------------------------------------------
    def _setup_source_and_destination(self):
        super(CorrelationsApp, self)._setup_source_and_destination()
        self.rule_system = ConfigmanDotDict()
        for a_rule_set_name in self.config.rules.rule_sets.names:
            self.config.logger.debug(
                'setting up rule set: %s',
                a_rule_set_name
            )
            self.rule_system[a_rule_set_name] = (
                self.config.rules[a_rule_set_name].rule_system_class(
                    self.config.rules[a_rule_set_name],
                    self.quit_check
                )
            )

    #--------------------------------------------------------------------------
    def close(self):
        super(CorrelationsApp, self).close()
        self.config.logger.debug('CorrelationsApp closes')
        for a_rule_set_name, a_rule_set in self.rule_system.iteritems():
            self.config.logger.debug('closing %s', a_rule_set_name)
            try:
                a_rule_set.close()
            except AttributeError:
                # guess we don't need to close that rule
                pass
        self.config.logger.debug('done closing rules')
