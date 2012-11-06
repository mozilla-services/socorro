# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import types
import re
import random

from configman import Namespace, RequiredConfig

from socorro.lib.ver_tools import normalize

Compiled_Regular_Expression_Type = type(re.compile(''))

#--------------------------------------------------------------------------
ACCEPT = 0    # save and process
DEFER = 1     # save but don't process
DISCARD = 2   # tell client to go away and not come back
IGNORE = 3    # ignore this submission entirely


#==============================================================================
class LegacyThrottler(RequiredConfig):
    required_config = Namespace()
    required_config.add_option(
      'throttle_conditions',
      doc='the throttling rules',
      default=[
        # 100% of crashes with comments
        ("Comments", "lambda x: x", 100),
        # 100% of nightly, aurora, beta & esr
        ("ReleaseChannel",
         "lambda x: x in ('nightly', 'aurora', 'beta', 'esr')",
         100),
        # 10% of Firefox
        ("ProductName", 'Firefox', 10),
        # 100% of Fennec
        ("ProductName", 'Fennec', 100),
        # 100% of all alpha, beta or special
        ("Version", "re.compile(r'\..*?[a-zA-Z]+')", 100),
        # 100% of Thunderbird, SeaMonkey & Camino
        ("ProductName", "lambda x: x[0] in 'TSC'", 100),
        # reject everything else
        (None, True, 0)
      ],
      from_string_converter=eval
    )
    required_config.add_option(
      'never_discard',
      doc='ignore the Thottleable protocol',
      default=True
    )
    required_config.add_option(
      'minimal_version_for_understanding_refusal',
      doc='ignore the Thottleable protocol',
      default={'Firefox': '3.5.4'},
      from_string_converter=eval
    )

    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.processed_throttle_conditions = \
          self.preprocess_throttle_conditions(
            config.throttle_conditions
          )

    #--------------------------------------------------------------------------
    @staticmethod
    def regexp_handler_factory(regexp):
        def egexp_handler(x):
            return regexp.search(x)
        return egexp_handler

    #--------------------------------------------------------------------------
    @staticmethod
    def bool_handler_factory(a_bool):
        def bool_handler(dummy):
            return a_bool
        return bool_handler

    #--------------------------------------------------------------------------
    @staticmethod
    def generic_handler_factory(an_object):
        def generic_handler(x):
            return an_object == x
        return generic_handler

    #--------------------------------------------------------------------------
    def preprocess_throttle_conditions(self, original_throttle_conditions):
        new_throttle_conditions = []
        for key, condition_str, percentage in original_throttle_conditions:
            #print "preprocessing %s %s %d" % (key, condition, percentage)
            if isinstance(condition_str, basestring):
                try:
                    condition = eval(condition_str)
                    self.config.logger.info(
                      '%s interprets "%s" as python code' %
                      (self.__class__, condition_str)
                    )
                except Exception:
                    self.config.logger.info(
                      '%s interprets "%s" as a literal for an equality test' %
                      (self.__class__, condition_str)
                    )
                    condition = condition_str
            else:
                condition = condition_str
            if isinstance(condition, Compiled_Regular_Expression_Type):
                #print "reg exp"
                new_condition = self.regexp_handler_factory(condition)
                #print newCondition
            elif isinstance(condition, bool):
                #print "bool"
                new_condition = self.bool_handler_factory(condition)
                #print newCondition
            elif isinstance(condition, types.FunctionType):
                new_condition = condition
            else:
                new_condition = self.generic_handler_factory(condition)
            new_throttle_conditions.append((key, new_condition, percentage))
        return new_throttle_conditions

    #--------------------------------------------------------------------------
    def understands_refusal(self, raw_crash):
        try:
            return normalize(raw_crash['Version']) >= normalize(
                self.config.minimal_version_for_understanding_refusal[
                  raw_crash['ProductName']
                ])
        except KeyError:
            return False

    #--------------------------------------------------------------------------
    def apply_throttle_conditions(self, raw_crash):
        """cycle through the throttle conditions until one matches or we fall
        off the end of the list.
        returns:
          True - reject
          False - accept
        """
        #print processed_throttle_conditions
        for key, condition, percentage in self.processed_throttle_conditions:
            throttle_match = False
            try:
                if key == '*':
                    throttle_match = condition(raw_crash)
                else:
                    throttle_match = condition(raw_crash[key])
            except KeyError:
                if key == None:
                    throttle_match = condition(None)
                else:
                    #this key is not present in the jsonData - skip
                    continue
            except IndexError:
                pass
            if throttle_match:  # we've got a condition match - apply percent
                if percentage is None:
                    return None
                random_real_percent = random.random() * 100.0
                return random_real_percent > percentage
        # nothing matched, reject
        return True

    #--------------------------------------------------------------------------
    def throttle(self, raw_crash):
        throttle_result = self.apply_throttle_conditions(raw_crash)
        if throttle_result is None:
            self.config.logger.debug(
              "ignoring %s %s",
              raw_crash.ProductName,
              raw_crash.Version
            )
            return IGNORE
        if throttle_result:  # we're rejecting
            #logger.debug('yes, throttle this one')
            if (self.understands_refusal(raw_crash)
                and not self.config.never_discard):
                self.config.logger.debug(
                  "discarding %s %s",
                  raw_crash.ProductName,
                  raw_crash.Version
                )
                return DISCARD
            else:
                self.config.logger.debug(
                  "deferring %s %s",
                  raw_crash.ProductName,
                  raw_crash.Version
                )
                return DEFER
        else:  # we're accepting
            self.config.logger.debug(
              "not throttled %s %s",
              raw_crash.ProductName,
              raw_crash.Version
            )
            return ACCEPT
