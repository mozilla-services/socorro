# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Temporary adaptors from old code to new code

import re
import random
import threading

import socorro.lib.ver_tools as vtl

from socorro.external.crashstorage_base import FallbackCrashStorage
from socorro.external.filesystem.crashstorage import FileSystemRawCrashStorage

from configman.dotdict import DotDict

compiledRegularExpressionType = type(re.compile(''))
functionType = type(lambda x: x)

pattern_str = r'(\d+)\.(\d+)\.?(\d+)?\.?(\d+)?([a|b]?)(\d*)(pre)?(\d)?'
pattern = re.compile(pattern_str)

pattern_plus = re.compile(r'((\d+)\+)')


#==============================================================================
class CrashStorageSystemForLocalFS(FallbackCrashStorage):
    def __init__(self, config):
        # new_config is an adapter to allow the modern configman enabled
        # file system crash storage classes to use the old style configuration.
        new_config = DotDict()
        new_config.logger = config.logger

        new_config.primary = DotDict()
        new_config.primary.storage_class = FileSystemRawCrashStorage
        new_config.primary.std_fs_root = config.localFS
        new_config.primary.dump_dir_count = config.localFSDumpDirCount
        new_config.primary.dump_gid = config.localFSDumpGID
        new_config.primary.dump_permissions = config.localFSDumpPermissions
        new_config.primary.dir_permissions = config.localFSDirPermissions
        new_config.primary.json_file_suffix = config.jsonFileSuffix
        new_config.primary.dump_file_suffix = config.dumpFileSuffix
        new_config.primary.logger = config.logger

        new_config.fallback = DotDict()
        new_config.fallback.storage_class = FileSystemRawCrashStorage
        new_config.fallback.std_fs_root = config.fallbackFS
        new_config.fallback.dump_dir_count = config.fallbackDumpDirCount
        new_config.fallback.dump_gid = config.fallbackDumpGID
        new_config.fallback.dump_permissions = config.fallbackDumpPermissions
        new_config.fallback.dir_permissions = config.fallbackDirPermissions
        new_config.fallback.json_file_suffix = config.jsonFileSuffix
        new_config.fallback.dump_file_suffix = config.dumpFileSuffix
        new_config.fallback.logger = config.logger

        super(CrashStorageSystemForLocalFS, self).__init__(new_config)


#==============================================================================
class CrashStorageSystemForHBase(FileSystemRawCrashStorage):
    pass


#==============================================================================
class LegacyThrottler(object):
    #--------------------------------------------------------------------------
    def __init__(self, config):
        self.config = config
        self.processedThrottleConditions = \
          self.preprocessThrottleConditions(config.throttleConditions)
    #--------------------------------------------------------------------------
    ACCEPT = 0
    DEFER = 1
    DISCARD = 2
    IGNORE = 3

    #--------------------------------------------------------------------------
    @staticmethod
    def regexpHandlerFactory(regexp):
        def egexpHandler(x):
            return regexp.search(x)
        return egexpHandler

    #--------------------------------------------------------------------------
    @staticmethod
    def boolHandlerFactory(aBool):
        def boolHandler(dummy):
            return aBool
        return boolHandler

    #--------------------------------------------------------------------------
    @staticmethod
    def genericHandlerFactory(anObject):
        def genericHandler(x):
            return anObject == x
        return genericHandler

    #--------------------------------------------------------------------------
    def preprocessThrottleConditions(self, originalThrottleConditions):
        newThrottleConditions = []
        for key, condition, percentage in originalThrottleConditions:
            #print "preprocessing %s %s %d" % (key, condition, percentage)
            conditionType = type(condition)
            if conditionType == compiledRegularExpressionType:
                #print "reg exp"
                newCondition = LegacyThrottler.regexpHandlerFactory(condition)
                #print newCondition
            elif conditionType == bool:
                #print "bool"
                newCondition = LegacyThrottler.boolHandlerFactory(condition)
                #print newCondition
            elif conditionType == functionType:
                newCondition = condition
            else:
                newCondition = LegacyThrottler.genericHandlerFactory(condition)
            newThrottleConditions.append((key, newCondition, percentage))
        return newThrottleConditions

    #--------------------------------------------------------------------------
    def understandsRefusal(self, raw_crash):
        try:
            return (vtl.normalize(raw_crash['Version']) >= vtl.normalize(
              self.config.minimalVersionForUnderstandingRefusal[
                raw_crash['ProductName']
              ])
            )
        except KeyError:
            return False

    #--------------------------------------------------------------------------
    def applyThrottleConditions(self, raw_crash):
        """cycle through the throttle conditions until one matches or we fall
        off the end of the list.
        returns:
          True - reject
          False - accept
        """
        #print processedThrottleConditions
        for key, condition, percentage in self.processedThrottleConditions:
            throttleMatch = False
            try:
                if key == '*':
                    throttleMatch = condition(raw_crash)
                else:
                    throttleMatch = condition(raw_crash[key])
            except KeyError:
                if key == None:
                    throttleMatch = condition(None)
                else:
                    #this key is not present in the jsonData - skip
                    continue
            except IndexError:
                pass
            if throttleMatch:  # condition match, apply the throttle percentage
                if percentage is None:
                    return None
                randomRealPercent = random.random() * 100.0
                return randomRealPercent > percentage
        # nothing matched, reject
        return True

    #--------------------------------------------------------------------------
    def throttle(self, raw_crash):
        result = self.applyThrottleConditions(raw_crash)
        if result is None:
            self.config.logger.debug("ignoring %s %s", raw_crash.ProductName,
                                     raw_crash.Version)
            return LegacyThrottler.IGNORE
        if result:
            #self.config.logger.debug('yes, throttle this one')
            if (self.understandsRefusal(raw_crash) and
                not self.config.neverDiscard):
                self.config.logger.debug("discarding %s %s",
                                         raw_crash.ProductName,
                                         raw_crash.Version)
                return LegacyThrottler.DISCARD
            else:
                self.config.logger.debug("deferring %s %s",
                                         raw_crash.ProductName,
                                         raw_crash.Version)
            return LegacyThrottler.DEFER
        else:
            self.config.logger.debug("not throttled %s %s",
                                     raw_crash.ProductName,
                                     raw_crash.Version)
            return LegacyThrottler.ACCEPT


#==============================================================================
class CrashStoragePool(dict):
    #--------------------------------------------------------------------------
    def __init__(self, config, storageClass=CrashStorageSystemForHBase):
        super(CrashStoragePool, self).__init__()
        self.config = config
        self.logger = config.logger
        self.storageClass = storageClass
        self.logger.debug("creating crashStorePool")

    #--------------------------------------------------------------------------
    def crashStorage(self, name=None):
        """Like connecionCursorPairNoTest, but test that the specified
        connection actually works"""
        if name is None:
            name = threading.currentThread().getName()
        if name not in self:
            self.logger.debug("creating crashStore for %s", name)
            self[name] = c = self.storageClass(self.config)
            return c
        return self[name]

    #--------------------------------------------------------------------------
    def cleanup(self):
        for name, crashStore in self.iteritems():
            try:
                crashStore.close()
                self.logger.debug("crashStore for %s closed", name)
            except Exception:
                self.logger.warning('could not close %s', name,
                                    exc_info=True)

    #--------------------------------------------------------------------------
    def remove(self, name):
        self[name].close()
        del self[name]
