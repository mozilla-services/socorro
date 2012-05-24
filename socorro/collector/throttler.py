import types
import re
import random

from socorro.lib.ver_tools import normalize

Compiled_Regular_Expression_Type = type(re.compile(''))


#==============================================================================
class LegacyThrottler(object):
    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.processed_throttle_conditions = \
          self.preprocess_throttle_conditions(
            config.throttleConditions
          )

    #--------------------------------------------------------------------------
    ACCEPT = 0
    DEFER = 1
    DISCARD = 2

    #--------------------------------------------------------------------------
    @staticmethod
    def regexp_handler_factory(regexp):
        def egexp_handler(x):
            return regexp.search(x)
        return egexp_handler

    #--------------------------------------------------------------------------
    @staticmethod
    def bool_handler_factory(aBool):
        def bool_handler(dummy):
            return aBool
        return bool_handler

    #--------------------------------------------------------------------------
    @staticmethod
    def generic_handler_factory(anObject):
        def generic_handler(x):
            return anObject == x
        return generic_handler

    #--------------------------------------------------------------------------
    def preprocess_throttle_conditions(self, original_throttle_conditions):
        new_throttle_conditions = []
        for key, condition, percentage in original_throttle_conditions:
            #print "preprocessing %s %s %d" % (key, condition, percentage)
            condition_type = type(condition)
            if condition_type == Compiled_Regular_Expression_Type:
                #print "reg exp"
                new_condition = \
                  LegacyThrottler.regexp_handler_factory(condition)
                #print newCondition
            elif condition_type == bool:
                #print "bool"
                new_condition = LegacyThrottler.bool_handler_factory(condition)
                #print newCondition
            elif condition_type == types.FunctionType:
                new_condition = condition
            else:
                new_condition = \
                  LegacyThrottler.generic_handler_factory(condition)
            new_throttle_conditions.append((key, new_condition, percentage))
        return new_throttle_conditions

    #--------------------------------------------------------------------------
    def understands_refusal (self, jsonData):
        try:
            print
            return normalize(jsonData['Version']) >= normalize(
                self.config.minimalVersionForUnderstandingRefusal[
                  jsonData['ProductName']
                ])
        except KeyError:
            return False

    #--------------------------------------------------------------------------
    def apply_throttle_conditions (self, jsonData):
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
                throttle_match = condition(jsonData[key])
            except KeyError:
                if key == None:
                    throttle_match = condition(None)
                else:
                    #this key is not present in the jsonData - skip
                    continue
            except IndexError:
                pass
            if throttle_match: #we've got a condition match - apply percent
                random_real_percent = random.random() * 100.0
                return random_real_percent > percentage
        # nothing matched, reject
        return True

    #--------------------------------------------------------------------------
    def throttle (self, raw_crash):
        if self.apply_throttle_conditions(raw_crash):
            #logger.debug('yes, throttle this one')
            if (self.understands_refusal(raw_crash)
                and not self.config.neverDiscard):
                self.config.logger.debug(
                  "discarding %s %s",
                  raw_crash.ProductName,
                  raw_crash.Version
                )
                return LegacyThrottler.DISCARD
            else:
                self.config.logger.debug(
                  "deferring %s %s",
                  raw_crash.ProductName,
                  raw_crash.Version
                )
                return LegacyThrottler.DEFER
        else:
            self.config.logger.debug(
              "not throttled %s %s",
              raw_crash.ProductName,
              raw_crash.Version
            )
            return LegacyThrottler.ACCEPT
