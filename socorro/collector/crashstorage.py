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
import socorro.lib.ver_tools as vtl

import socorro.hbase.hbaseClient as hbc

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
    result = fn(*args, **kwargs)
    logger.info("%s for %s", tm.time() - before, str(fn))
    return result
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
    self.hostname = os.uname()[1]
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
  def save (self, uuid, jsonData, dump):
    return CrashStorageSystem.NO_ACTION


#=================================================================================================================
class CrashStorageSystemForHBase(CrashStorageSystem):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config, hbaseClient=hbc, jsonDumpStorage=jds):
    super(CrashStorageSystemForHBase, self).__init__(config)
    try:
      self.hbaseConnection = hbaseClient.HBaseConnectionForCrashReports(config.hbaseHost, config.hbasePort)
    except Exception:
      sutil.reportExceptionAndContinue(logger)
      self.hbaseConnection = None
    if config.hbaseFallbackFS:
      self.fallbackCrashStorage = jsonDumpStorage.JsonDumpStorage(root=config.hbaseFallbackFS,
                                                                  maxDirectoryEntries = config.dumpDirCount,
                                                                  jsonSuffix = config.jsonFileSuffix,
                                                                  dumpSuffix = config.dumpFileSuffix,
                                                                  dumpGID = config.dumpGID,
                                                                  dumpPermissions = config.dumpPermissions,
                                                                  dirPermissions = config.dirPermissions,
                                                                 )
    else:
      self.fallbackCrashStorage = None

  #-----------------------------------------------------------------------------------------------------------------
  def save (self, uuid, jsonData, dump, currentTimestamp):
    try:
      jsonData = json.dumps(jsonData)
      self.hbaseConnection.put_json_dump(uuid, jsonData, dump.read())
      return CrashStorageSystem.OK
    except Exception, x:
      if self.fallbackCrashStorage:
        logger.warning('cannot save %s in hbase, falling back to filesystem', uuid)
        try:
          jsonFileHandle, dumpFileHandle = self.fallbackCrashStorage.newEntry(uuid, self.hostname, currentTimestamp)
          try:
            dumpFileHandle.write(dump.read())
            json.dump(jsonData, jsonFileHandle)
          finally:
            dumpFileHandle.close()
            jsonFileHandle.close()
          return CrashStorageSystem.OK
        except Exception, x:
          sutil.reportExceptionAndContinue(logger)
      else:
        logger.warning('there is no fallback storage for hbase: dropping %s on the floor', uuid)
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
  def terminated (self, jsonData):
    return False

  #-----------------------------------------------------------------------------------------------------------------
  def understandsRefusal (self, jsonData):
    try:
      #logger.debug('understandsRefusal - %s, %s, %s, %s, %s', jsonData['ProductName'], jsonData['Version'], self.config.minimalVersionForUnderstandingRefusal[jsonData['ProductName']], self.normalizeVersionToInt(jsonData['Version']), self.normalizeVersionToInt(self.config.minimalVersionForUnderstandingRefusal[jsonData['ProductName']]))
      return vtl.normalize(jsonData['Version']) >= vtl.normalize(self.config.minimalVersionForUnderstandingRefusal[jsonData['ProductName']])
    except KeyError:
      return False

  #-----------------------------------------------------------------------------------------------------------------
  def throttle (self, jsonData):
    #print processedThrottleConditions
    for key, condition, percentage in self.processedThrottleConditions:
      #logger.debug("throttle testing  %s %s %d", key, condition, percentage)
      throttleMatch = False
      try:
        throttleMatch = condition(jsonData[key])
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
  def save (self, uuid, jsonData, dump, currentTimestamp):
    try:
      if "Throttleable" not in jsonData or int(jsonData.Throttleable):
        if self.throttle(jsonData):
          #logger.debug('yes, throttle this one')
          if self.understandsRefusal(jsonData) and not self.config.neverDiscard:
            logger.debug("discarding %s %s", jsonData.ProductName, jsonData.Version)
            return CrashStorageSystem.DISCARDED
          else:
            logger.debug("deferring %s %s", jsonData.ProductName, jsonData.Version)
            fileSystemStorage = self.deferredFileSystemStorage
        else:
          logger.debug("not throttled %s %s", jsonData.ProductName, jsonData.Version)
          fileSystemStorage = self.standardFileSystemStorage
      else:
        logger.debug("cannot be throttled %s %s", jsonData.ProductName, jsonData.Version)
        fileSystemStorage = self.standardFileSystemStorage

      jsonFileHandle, dumpFileHandle = fileSystemStorage.newEntry(uuid, self.hostname, currentTimestamp)
      try:
        try:
          dumpFileHandle.write(dump.read())
        except AttributeError:
          dumpFileHandle.write(dump)
        json.dump(jsonData, jsonFileHandle)
      finally:
        dumpFileHandle.close()
        jsonFileHandle.close()

      return CrashStorageSystem.OK
    except:
      sutil.reportExceptionAndContinue(logger)
      return CrashStorageSystem.ERROR

