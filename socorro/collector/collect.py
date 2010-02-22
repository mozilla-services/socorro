#
# collect.py, collector functions for mod_python collectors
#

try:
  import socorro.lib.uuid as uuid
except ImportError:
  import uuid

try:
  import json
except ImportError:
  import simplejson as json

import socorro.lib.ooid as ooid
import socorro.lib.util as sutil
import socorro.lib.JsonDumpStorage as jds

import hbaseClient

import os
import datetime as dt
import time as tm
import re
import random
import logging
logger = logging.getLogger("collector")

compiledRegularExpressionType = type(re.compile(''))
functionType = type(lambda x: x)

pattern_str = r'(\d+)\.(\d+)\.?(\d+)?\.?(\d+)?([a|b]?)(\d*)(pre)?(\d)?'
pattern = re.compile(pattern_str)

pattern_plus = re.compile(r'((\d+)\+)')

#-----------------------------------------------------------------------------------------------------------------
def benchmark(fn):
  def t(*args, **kwargs):
    before = tm.time()
    fn(*args, **kwargs)
    logger.info("%s for %s", tm.time() - before, str(fn))
  return t


#=================================================================================================================
class RepeatableStreamReader(object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, stream):
    self.stream = stream
  #-----------------------------------------------------------------------------------------------------------------
  def read(self):
    try:
      return self.cache
    except AttributeError:
      self.cache = self.stream.read()
    return self.cache

#=================================================================================================================
class CrashStorageSystem(object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config):
    self.config = config
    try:
      if config.benchmark:
        self.save = benchmark(self.save)
    except:
      pass
  #-----------------------------------------------------------------------------------------------------------------
  def makeJsonDictFromForm (self, form, tm=tm):
    names = [name for name in form.keys() if name != self.config.dumpField]
    jsonDict = sutil.DotDict()
    for name in names:
      if type(form[name]) == str:
        jsonDict[name] = form[name]
      else:
        jsonDict[name] = form[name].value
    jsonDict.timestamp = tm.time()
    return jsonDict
  #-----------------------------------------------------------------------------------------------------------------
  NO_ACTION = 0
  OK = 1
  DISCARDED = 2
  ERROR = 3
  #-----------------------------------------------------------------------------------------------------------------
  def save (self, uuid, json, dump):
    return CrashStorageSystem.NO_ACTION


#=================================================================================================================
class CrashStorageSystemForHBase(CrashStorageSystem):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config, hbaseClient=hbaseClient):
    super(CrashStorageSystemForHBase, self).__init__(config)
    self.hbaseConnection = hbaseClient.HBaseConnectionForCrashReports(config.hbaseHost, config.hbasePort)

  #-----------------------------------------------------------------------------------------------------------------
  def save (self, uuid, jsonDataDictionary, dump):
    try:
      self.hbaseConnection.create_ooid(uuid, str(jsonDataDictionary), dump.read())
      return CrashStorageSystem.OK
    except:
      sutil.reportExceptionAndContinue(logger)
      return CrashStorageSystem.ERROR


#=================================================================================================================
class CrashStorageSystemForNFS(CrashStorageSystem):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config):
    super(CrashStorageSystemForNFS, self).__init__(config)
    self.processedThrottleConditions = self.preprocessThrottleConditions(config.throttleConditions)
    self.normalizedVersionDict = {}
    self.normalizedVersionDictEntryCounter = 0
    self.standardFileSystemStorage = jds.JsonDumpStorage(root = config.storageRoot,
                                                         maxDirectoryEntries = config.dumpDirCount,
                                                         jsonSuffix = config.jsonFileSuffix,
                                                         dumpSuffix = config.dumpFileSuffix,
                                                         dumpGID = config.dumpGID,
                                                         dumpPermissions = config.dumpPermissions,
                                                         dirPermissions = config.dirPermissions,
                                                        )
    self.deferredFileSystemStorage = jds.JsonDumpStorage(root = config.deferredStorageRoot,
                                                         maxDirectoryEntries = config.dumpDirCount,
                                                         jsonSuffix = config.jsonFileSuffix,
                                                         dumpSuffix = config.dumpFileSuffix,
                                                         dumpGID = config.dumpGID,
                                                         dumpPermissions = config.dumpPermissions,
                                                         dirPermissions = config.dirPermissions,
                                                        )
    self.hostname = os.uname()[1]


  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def regexpHandlerFactory(regexp):
    def egexpHandler(x):
      return regexp.search(x)
    return egexpHandler

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def boolHandlerFactory(aBool):
    def boolHandler(dummy):
      return aBool
    return boolHandler

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def genericHandlerFactory(anObject):
    def genericHandler(x):
      return anObject == x
    return genericHandler

  #-----------------------------------------------------------------------------------------------------------------
  def preprocessThrottleConditions(self, originalThrottleConditions):
    newThrottleConditions = []
    for key, condition, percentage in originalThrottleConditions:
      #print "preprocessing %s %s %d" % (key, condition, percentage)
      conditionType = type(condition)
      if conditionType == compiledRegularExpressionType:
        #print "reg exp"
        newCondition = CrashStorageSystemForNFS.regexpHandlerFactory(condition)
        #print newCondition
      elif conditionType == bool:
        #print "bool"
        newCondition = CrashStorageSystemForNFS.boolHandlerFactory(condition)
        #print newCondition
      elif conditionType == functionType:
        newCondition = condition
      else:
        newCondition = CrashStorageSystemForNFS.genericHandlerFactory(condition)
      newThrottleConditions.append((key, newCondition, percentage))
    return newThrottleConditions

  #-----------------------------------------------------------------------------------------------------------------
  def terminated (self, json):
    return False

  #-----------------------------------------------------------------------------------------------------------------
  def normalizeVersionToInt(self, version_string):
    try:
      return self.normalizedVersionDict[version_string]
    except KeyError:
      # replace \d+\+ with $1++
      match = re.search(pattern_plus, version_string)
      if match:
        (old, ver) = match.groups()
        replacement = "%dpre0"%(int(ver)+1)
        version_string = version_string.replace(old, replacement)

      # version_string.replace()
      match = re.match(pattern, version_string)
      if match:
        (major, minor1, minor2, minor3, alpha, alpha_n, pre, pre_n) = match.groups()

        # normalize data
        major  = int(major)
        minor1 = int(minor1)
        if not minor2:
          minor2 = 0
        else:
          minor2 = int(minor2)

        if not minor3:
          minor3 = 0
        else:
          minor3 = int(minor3)

        if alpha == 'a':
          alpha = 0
        elif alpha == 'b':
          alpha = 1
        else:
          alpha = 2

        if alpha_n:
          alpha_n  = int(alpha_n)
        else:
          alpha_n = 0

        if pre == 'pre':
          pre = 0
        else:
          pre = 1

        if pre_n:
          pre_n = int(pre_n)
        else:
          pre_n = 0

        int_str = "%02d%02d%02d%02d%d%02d%d%02d"  % (major, minor1, minor2, minor3, alpha, alpha_n, pre, pre_n)
        self.normalizedVersionDict[version_string] = normalizedVersion = int(int_str)
        self.normalizedVersionDictEntryCounter += 1
        if self.normalizedVersionDictEntryCounter > 1000:
          logger.warning("we've seem more than 1000 different version strings.  This is really suspicous")
          self.normalizedVersionDict = {}  #reset to avoid eating up all the memory
        return normalizedVersion

  #-----------------------------------------------------------------------------------------------------------------
  def understandsRefusal (self, json):
    try:
      #logger.debug('understandsRefusal - %s, %s, %s, %s, %s', json['ProductName'], json['Version'], self.config.minimalVersionForUnderstandingRefusal[json['ProductName']], self.normalizeVersionToInt(json['Version']), self.normalizeVersionToInt(self.config.minimalVersionForUnderstandingRefusal[json['ProductName']]))
      return self.normalizeVersionToInt(json['Version']) >= self.normalizeVersionToInt(self.config.minimalVersionForUnderstandingRefusal[json['ProductName']])
    except KeyError:
      return False

  #-----------------------------------------------------------------------------------------------------------------
  def throttle (self, json):
    #print processedThrottleConditions
    for key, condition, percentage in self.processedThrottleConditions:
      #logger.debug("throttle testing  %s %s %d", key, condition, percentage)
      throttleMatch = False
      try:
        throttleMatch = condition(json[key])
      except KeyError:
        if key == None:
          throttleMatch = condition(None)
        else:
          #print "bad key"
          continue
      except IndexError:
        pass
      if throttleMatch:
        #randint = random.randint(0, 100)
        #print "throttle: %d %d %s" % (randint, percentage, randint > percentage)
        #return randint > percentage
        randomRealPercent = random.random() * 100.0
        #logger.debug("throttle: %f %f %s", randomRealPercent, percentage, randomRealPercent > percentage)
        return randomRealPercent > percentage
    return True

  #-----------------------------------------------------------------------------------------------------------------
  def save (self, uuid, jsonDataDictionary, dump):
    try:
      if "Throttleable" not in jsonDataDictionary or int(jsonDataDictionary.Throttleable):
        if self.throttle(jsonDataDictionary):
          #logger.debug('yes, throttle this one')
          if self.understandsRefusal(jsonDataDictionary) and not config.neverDiscard:
            logger.debug("discarding %s %s", jsonDataDictionary.ProductName, jsonDataDictionary.Version)
            return CrashStorageSystem.DISCARDED
          else:
            logger.debug("deferring %s %s", jsonDataDictionary.ProductName, jsonDataDictionary.Version)
            fileSystemStorage = self.deferredFileSystemStorage
        else:
          logger.debug("not throttled %s %s", jsonDataDictionary.ProductName, jsonDataDictionary.Version)
          fileSystemStorage = self.standardFileSystemStorage
      else:
        logger.debug("cannot be throttled %s %s", jsonDataDictionary.ProductName, jsonDataDictionary.Version)
        fileSystemStorage = self.standardFileSystemStorage

      jsonFileHandle, dumpFileHandle = fileSystemStorage.newEntry(uuid, self.hostname, dt.datetime.now())
      try:
        dumpFileHandle.write(dump.read())
        json.dump(jsonDataDictionary, jsonFileHandle)
      finally:
        dumpFileHandle.close()
        jsonFileHandle.close()

      return CrashStorageSystem.OK
    except:
      sutil.reportExceptionAndContinue(logger)
      return CrashStorageSystem.ERROR

