#
# collect.py, collector functions for mod_python collectors
#

try:
  import json
except ImportError:
  import simplejson as json

import socorro.lib.ooid as ooid
import socorro.lib.util as sutil
import socorro.lib.JsonDumpStorage as jds
import socorro.lib.ver_tools as vtl
import socorro.lib.jsonUtil as jsut

import socorro.storage.hbaseClient as hbc
from socorro.storage.hbaseClient import OoidNotFoundException

import os
import datetime as dt
import time as tm
import re
import random
import logging
import threading
#import base64
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
class OoidNotFoundException(Exception):
  pass

#=================================================================================================================
class NotImplementedException(Exception):
  pass

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
class LegacyThrottler(object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, config):
    self.config = config
    self.processedThrottleConditions = self.preprocessThrottleConditions(config.throttleConditions)
  #-----------------------------------------------------------------------------------------------------------------
  ACCEPT = 0
  DEFER = 1
  DISCARD = 2
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

  #-----------------------------------------------------------------------------------------------------------------
  def understandsRefusal (self, jsonData):
    try:
      return vtl.normalize(jsonData['Version']) >= vtl.normalize(self.config.minimalVersionForUnderstandingRefusal[jsonData['ProductName']])
    except KeyError:
      return False

  #-----------------------------------------------------------------------------------------------------------------
  def applyThrottleConditions (self, jsonData):
    """cycle through the throttle conditions until one matches or we fall off
    the end of the list.
    returns:
      True - reject
      False - accept
    """
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
          #this key is not present in the jsonData - skip
          continue
      except IndexError:
        pass
      if throttleMatch: #we've got a condition match - apply the throttle percentage
        randomRealPercent = random.random() * 100.0
        #logger.debug("throttle: %f %f %s", randomRealPercent, percentage, randomRealPercent > percentage)
        return randomRealPercent > percentage
    # nothing matched, reject
    return True

  ##-----------------------------------------------------------------------------------------------------------------
  #def throttle (self, jsonData):
    #if "Throttleable" not in jsonData or int(jsonData.Throttleable):
      #if self.applyThrottleConditions(jsonData):
        ##logger.debug('yes, throttle this one')
        #if self.understandsRefusal(jsonData) and not self.config.neverDiscard:
          #logger.debug("discarding %s %s", jsonData.ProductName, jsonData.Version)
          #return LegacyThrottler.DISCARD
        #else:
          #logger.debug("deferring %s %s", jsonData.ProductName, jsonData.Version)
          #return LegacyThrottler.DEFER
      #else:
        #logger.debug("not throttled %s %s", jsonData.ProductName, jsonData.Version)
        #return LegacyThrottler.ACCEPT
    #else:
      #logger.debug("cannot be throttled %s %s", jsonData.ProductName, jsonData.Version)
      #return LegacyThrottler.ACCEPT  
  
  #-----------------------------------------------------------------------------------------------------------------
  def throttle (self, jsonData):
    if self.applyThrottleConditions(jsonData):
      #logger.debug('yes, throttle this one')
      if self.understandsRefusal(jsonData) and not self.config.neverDiscard:
        logger.debug("discarding %s %s", jsonData.ProductName, jsonData.Version)
        return LegacyThrottler.DISCARD
      else:
        logger.debug("deferring %s %s", jsonData.ProductName, jsonData.Version)
        return LegacyThrottler.DEFER
    else:
      logger.debug("not throttled %s %s", jsonData.ProductName, jsonData.Version)
      return LegacyThrottler.ACCEPT

#=================================================================================================================
class CrashStorageSystem(object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config):
    self.config = config
    self.hostname = os.uname()[1]
    if "logger" in config and config.logger:
      self.logger = config.logger
    else:
      self.logger = logger
    try:
      if config.benchmark:
        self.save = benchmark(self.save)
    except:
      pass
  #-----------------------------------------------------------------------------------------------------------------
  def close (self):
    pass
  #-----------------------------------------------------------------------------------------------------------------
  def makeJsonDictFromForm (self, form, tm=tm):
    names = [name for name in form.keys() if name != self.config.dumpField]
    jsonDict = sutil.DotDict()
    for name in names:
      t = type(form[name])
      if t in (str, unicode):
        jsonDict[name] = form[name]
      else:
        jsonDict[name] = form[name].value
    #jsonDict.timestamp = tm.time()
    return jsonDict
  #-----------------------------------------------------------------------------------------------------------------
  NO_ACTION = 0
  OK = 1
  DISCARDED = 2
  ERROR = 3
  #-----------------------------------------------------------------------------------------------------------------
  def terminated (self, jsonData):
    return False
  #-----------------------------------------------------------------------------------------------------------------
  def save_raw (self, ooid, jsonData, dump):
    return CrashStorageSystem.NO_ACTION
  #-----------------------------------------------------------------------------------------------------------------
  def save_processed (self, ooid, jsonData):
    return CrashStorageSystem.NO_ACTION
  #-----------------------------------------------------------------------------------------------------------------
  def get_meta (self, ooid):
    raise NotImplementedException("get_meta is not implemented")
  #-----------------------------------------------------------------------------------------------------------------
  def get_raw_dump (self, ooid):
    raise NotImplementedException("get_raw_crash is not implemented")
  #-----------------------------------------------------------------------------------------------------------------
  def get_raw_dump_base64(self,ooid):
    raise NotImplementedException("get_raw_dump_base64 is not implemented")
  #-----------------------------------------------------------------------------------------------------------------
  def get_processed (self, ooid):
    raise NotImplementedException("get_processed is not implemented")
  #-----------------------------------------------------------------------------------------------------------------
  def uuidInStorage (self, ooid):
    return False
  #-----------------------------------------------------------------------------------------------------------------
  def newUuids(self):
    raise StopIteration


#=================================================================================================================
class CrashStorageSystemForHBase(CrashStorageSystem):
  def __init__ (self, config, hbaseClient=hbc, jsonDumpStorage=jds):
    super(CrashStorageSystemForHBase, self).__init__(config)
    assert "hbaseHost" in config, "hbaseHost is missing from the configuration"
    assert "hbasePort" in config, "hbasePort is missing from the configuration"
    assert "hbaseTimeout" in config, "hbaseTimeout is missing from the configuration"
    assert "hbaseRetry" in config, "hbaseRetry is missing from the configuration"
    assert "hbaseRetryDelay" in config, "hbaseRetryDelay is missing from the configuration"
    self.logger.info('connecting to hbase')
    self.hbaseRetry = config.hbaseRetry
    self.hbaseRetryDelay = config.hbaseRetryDelay
    self.logger.debug('hbase conf: %s:%s', config.hbaseHost, config.hbasePort)
    self.hbaseConnection = hbaseClient.HBaseConnectionForCrashReports(config.hbaseHost, config.hbasePort, config.hbaseTimeout, logger=self.logger)

  #-----------------------------------------------------------------------------------------------------------------
  def close (self):
    self.hbaseConnection.close()

  #-----------------------------------------------------------------------------------------------------------------
  def save_raw (self, ooid, jsonData, dump, currentTimestamp):
    try:
      jsonDataAsString = json.dumps(jsonData)
      self.hbaseConnection.put_json_dump(ooid,
                                         jsonData,
                                         #dump.read(),
                                         dump,
                                         number_of_retries=self.hbaseRetry,
                                         wait_between_retries=self.hbaseRetryDelay)
      return CrashStorageSystem.OK
    except Exception, x:
      sutil.reportExceptionAndContinue(self.logger)
      return CrashStorageSystem.ERROR

  #-----------------------------------------------------------------------------------------------------------------
  def save_processed (self, ooid, jsonData):
    try:
      self.hbaseConnection.put_processed_json(ooid,
                                              jsonData,
                                              number_of_retries=self.hbaseRetry,
                                              wait_between_retries=self.hbaseRetryDelay)
    except UnicodeDecodeError:
      jsonData = jsut.sanitizeForJson(jsonData)
      self.hbaseConnection.put_processed_json(ooid,
                                              jsonData,
                                              number_of_retries=self.hbaseRetry,
                                              wait_between_retries=self.hbaseRetryDelay)

  #-----------------------------------------------------------------------------------------------------------------
  def get_meta (self, ooid):
    return self.hbaseConnection.get_json(ooid,
                                         number_of_retries=self.hbaseRetry,
                                         wait_between_retries=self.hbaseRetryDelay)

  #-----------------------------------------------------------------------------------------------------------------
  def get_raw_dump (self, ooid):
    return self.hbaseConnection.get_dump(ooid,
                                         number_of_retries=self.hbaseRetry,
                                         wait_between_retries=self.hbaseRetryDelay)

  #-----------------------------------------------------------------------------------------------------------------
  #def get_raw_dump_base64 (self, ooid):
    #dump = self.get_raw_dump(ooid,
                             #number_of_retries=self.hbaseRetry,
                             #wait_between_retries=self.hbaseRetryDelay)
    #return base64.b64encode(dump)

  #-----------------------------------------------------------------------------------------------------------------
  def get_processed (self, ooid):
    try:
      return self.hbaseConnection.get_processed_json(ooid,
                                                     number_of_retries=self.hbaseRetry,
                                                     wait_between_retries=self.hbaseRetryDelay)
    except hbc.OoidNotFoundException, x:
      raise OoidNotFoundException(ooid)

  #-----------------------------------------------------------------------------------------------------------------
  def uuidInStorage (self, ooid):
    return self.hbaseConnection.acknowledge_ooid_as_legacy_priority_job(ooid,
                                                                        number_of_retries=self.hbaseRetry,
                                                                        wait_between_retries=self.hbaseRetryDelay)

  #-----------------------------------------------------------------------------------------------------------------
  def dumpPathForUuid(self, ooid, basePath):
    dumpPath = ("%s/%s.dump" % (basePath, ooid)).replace('//', '/')
    f = open(dumpPath, "w")
    try:
      dump = self.hbaseConnection.get_dump(ooid,
                                           number_of_retries=self.hbaseRetry,
                                           wait_between_retries=self.hbaseRetryDelay)
      f.write(dump)
    finally:
      f.close()
    return dumpPath

  #-----------------------------------------------------------------------------------------------------------------
  def cleanUpTempDumpStorage(self, ooid, basePath):
    dumpPath = ("%s/%s.dump" % (basePath, ooid)).replace('//', '/')
    os.unlink(dumpPath)

  #-----------------------------------------------------------------------------------------------------------------
  def newUuids(self):
    return self.hbaseConnection.iterator_for_all_legacy_to_be_processed()

  #-----------------------------------------------------------------------------------------------------------------
  def dbFeederStandardJobIter(self, sleepFunction=tm.sleep):
    while True:
      #self.logger.debug('invoking hbaseConnection.iterator_for_legacy_db_feeder_queue')
      for x in self.hbaseConnection.iterator_for_legacy_db_feeder_queue():
        #self.logger.debug('about to yield')
        #self.logger.debug(x)
        yield json.loads(x)
      self.logger.debug('no jobs to do.  napping for 30 seconds')
      sleepFunction(30)

  #-----------------------------------------------------------------------------------------------------------------
  def tagAsPriority(self, ooid):
    self.hbaseConnection.put_priority_flag(ooid)

  #-----------------------------------------------------------------------------------------------------------------
  def dbFeederPriorityJobIter(self, sleepFunction=tm.sleep):
    while True:
      #self.logger.debug('invoking hbaseConnection.iterator_for_legacy_db_feeder_queue')
      for x in self.hbaseConnection.iterator_for_priority_db_feeder_queue():
        #self.logger.debug('about to yield')
        yield json.loads(x)
      self.logger.debug('no jobs to do.  napping for 5 seconds')
      sleepFunction(5)

#=================================================================================================================
class CollectorCrashStorageSystemForHBase(CrashStorageSystemForHBase):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config, hbaseClient=hbc, jsonDumpStorage=jds):
    super(CollectorCrashStorageSystemForHBase, self).__init__(config, hbaseClient=hbaseClient, jsonDumpStorage=jsonDumpStorage)
    assert "hbaseFallbackFS" in config, "hbaseFallbackFS is missing from the configuration"
    assert "hbaseFallbackDumpDirCount" in config, "hbaseFallbackDumpDirCount is missing from the configuration"
    assert "hbaseFallbackDumpGID" in config, "hbaseFallbackDumpGID is missing from the configuration"
    assert "hbaseFallbackDumpPermissions" in config, "hbaseFallbackDumpPermissions is missing from the configuration"
    assert "hbaseFallbackDirPermissions" in config, "hbaseFallbackDirPermissions is missing from the configuration"
    if config.hbaseFallbackFS:
      self.fallbackCrashStorage = jsonDumpStorage.JsonDumpStorage(root=config.hbaseFallbackFS,
                                                                  maxDirectoryEntries = config.hbaseFallbackDumpDirCount,
                                                                  jsonSuffix = config.jsonFileSuffix,
                                                                  dumpSuffix = config.dumpFileSuffix,
                                                                  dumpGID = config.hbaseFallbackDumpGID,
                                                                  dumpPermissions = config.hbaseFallbackDumpPermissions,
                                                                  dirPermissions = config.hbaseFallbackDirPermissions,
                                                                  logger = config.logger,
                                                                 )
    else:
      self.fallbackCrashStorage = None

  #-----------------------------------------------------------------------------------------------------------------
  def save_raw (self, ooid, jsonData, dump, currentTimestamp):
    try:
      jsonDataAsString = json.dumps(jsonData)
      self.hbaseConnection.put_json_dump(ooid,
                                         jsonData,
                                         #dump.read(),
                                         dump,
                                         number_of_retries=self.hbaseRetry,
                                         wait_between_retries=self.hbaseRetryDelay)
      return CrashStorageSystem.OK
    except Exception, x:
      sutil.reportExceptionAndContinue(self.logger)
      if self.fallbackCrashStorage:
        self.logger.warning('cannot save %s in hbase, falling back to filesystem', ooid)
        try:
          jsonFileHandle, dumpFileHandle = self.fallbackCrashStorage.newEntry(ooid, self.hostname, currentTimestamp)
          try:
            dumpFileHandle.write(dump.read())
            json.dump(jsonData, jsonFileHandle)
          finally:
            dumpFileHandle.close()
            jsonFileHandle.close()
          return CrashStorageSystem.OK
        except Exception, x:
          sutil.reportExceptionAndContinue(self.logger)
      else:
        self.logger.warning('there is no fallback storage for hbase: dropping %s on the floor', ooid)
      return CrashStorageSystem.ERROR


#=================================================================================================================
class CrashStorageSystemForNFS(CrashStorageSystem):   # DEPRECATED
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config):
    super(CrashStorageSystemForNFS, self).__init__(config)
    assert "storageRoot" in config, "storageRoot is missing from the configuration"
    assert "deferredStorageRoot" in config, "deferredStorageRoot is missing from the configuration"
    assert "dumpPermissions" in config, "dumpPermissions is missing from the configuration"
    assert "dirPermissions" in config, "dirPermissions is missing from the configuration"
    assert "dumpGID" in config, "dumpGID is missing from the configuration"
    assert "jsonFileSuffix" in config, "jsonFileSuffix is missing from the configuration"
    assert "dumpFileSuffix" in config, "dumpFileSuffix is missing from the configuration"

    #self.throttler = LegacyThrottler(config)
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
  def save_raw (self, ooid, jsonData, dump, currentTimestamp):
    try:
      #throttleAction = self.throttler.throttle(jsonData)
      throttleAction = jsonData.legacy_processing
      if throttleAction == LegacyThrottler.DISCARD:
        self.logger.debug("discarding %s %s", jsonData.ProductName, jsonData.Version)
        return CrashStorageSystem.DISCARDED
      elif throttleAction == LegacyThrottler.DEFER:
        self.logger.debug("deferring %s %s", jsonData.ProductName, jsonData.Version)
        fileSystemStorage = self.deferredFileSystemStorage
      else:
        self.logger.debug("not throttled %s %s", jsonData.ProductName, jsonData.Version)
        fileSystemStorage = self.standardFileSystemStorage

      jsonFileHandle, dumpFileHandle = fileSystemStorage.newEntry(ooid, self.hostname, currentTimestamp)
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
      sutil.reportExceptionAndContinue(self.logger)
      return CrashStorageSystem.ERROR

  #-----------------------------------------------------------------------------------------------------------------
  def get_raw (self, ooid):
    jobPathname = self.jsonPathForUuidInJsonDumpStorage(ooid)
    jsonFile = open(jobPathname)
    try:
      jsonDocument = simplejson.load(jsonFile)
    finally:
      jsonFile.close()
    return jsonDocument

  #-----------------------------------------------------------------------------------------------------------------
  def jsonPathForUuidInJsonDumpStorage(self, ooid):
    try:
      jsonPath = self.standardJobStorage.getJson(ooid)
    except (OSError, IOError):
      try:
        jsonPath = self.deferredJobStorage.getJson(ooid)
      except (OSError, IOError):
        raise OoidNotFoundException("%s cannot be found in standard or deferred storage" % ooid)
    return jsonPath

  #-----------------------------------------------------------------------------------------------------------------
  def dumpPathForUuid(self, ooid, ignoredBasePath):
    try:
      dumpPath = self.standardJobStorage.getDump(ooid)
    except (OSError, IOError):
      try:
        dumpPath = self.deferredJobStorage.getDump(ooid)
      except (OSError, IOError):
        raise OoidNotFoundException("%s cannot be found in standard or deferred storage" % ooid)
    return dumpPath

  #-----------------------------------------------------------------------------------------------------------------
  def cleanUpTempDumpStorage(self, ooid, ignoredBasePath):
    pass

  #-----------------------------------------------------------------------------------------------------------------
  def uuidInStorage(self, ooid):
    try:
      uuidPath = self.standardJobStorage.getJson(ooid)
      self.standardJobStorage.markAsSeen(ooid)
    except (OSError, IOError):
      try:
        uuidPath = self.deferredJobStorage.getJson(ooid)
        self.deferredJobStorage.markAsSeen(ooid)
      except (OSError, IOError):
        return False
    return True

  #-----------------------------------------------------------------------------------------------------------------
  def newUuids(self):
    return self.standardJobStorage.destructiveDateWalk()


#=================================================================================================================
class CrashStoragePool(dict):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, config, storageClass=CrashStorageSystemForHBase):
    super(CrashStoragePool, self).__init__()
    self.config = config
    self.logger = config.logger
    self.storageClass = storageClass
    self.logger.debug("creating crashStorePool")

  #-----------------------------------------------------------------------------------------------------------------
  def crashStorage(self, name=None):
    if name is None:
      name = threading.currentThread().getName()
    if name not in self:
      self.logger.debug("creating crashStore for %s", name)
      self[name] = c = self.storageClass(self.config)
      return c
    return self[name]

  #-----------------------------------------------------------------------------------------------------------------
  def cleanup (self):
    for name, crashStore in self.iteritems():
      try:
        crashStore.close()
        self.logger.debug("crashStore %s closed", name)
      except:
        sutil.reportExceptionAndContinue(self.logger)

