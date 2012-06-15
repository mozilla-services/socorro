import web
import logging

logger = logging.getLogger("collector")

import socorro.lib.ooid as sooid
import socorro.storage.crashstorage as cstore

from socorro.lib.datetimeutil import utc_now

#===============================================================================
class Collector(object):
  #-----------------------------------------------------------------------------
  def __init__(self, context):
    self.context = context
    self.logger = self.context.setdefault('logger', logger)
    #self.logger.debug('Collector __init__')
    self.legacyThrottler = context.legacyThrottler # save 1 level of lookup later
    self.dumpIDPrefix = context.dumpIDPrefix # save 1 level of lookup later

  #-----------------------------------------------------------------------------
  uri = '/submit'
  #-----------------------------------------------------------------------------
  def POST(self, *args):
    crashStorage = self.context.crashStoragePool.crashStorage()
    theform = web.input()

    dump = theform[self.context.dumpField]
    currentTimestamp = utc_now()
    jsonDataDictionary = crashStorage.makeJsonDictFromForm(theform)
    jsonDataDictionary.submitted_timestamp = currentTimestamp.isoformat()
    #for future use when we start sunsetting products
    #if crashStorage.terminated(jsonDataDictionary):
      #return "Terminated=%s" % jsonDataDictionary.Version
    ooid = sooid.createNewOoid(currentTimestamp)
    jsonDataDictionary.legacy_processing = \
        self.legacyThrottler.throttle(jsonDataDictionary)
    self.logger.info('%s received', ooid)
    result = crashStorage.save_raw(ooid,
                                   jsonDataDictionary,
                                   dump,
                                   currentTimestamp)
    if result == cstore.CrashStorageSystem.DISCARDED:
      return "Discarded=1\n"
    elif result == cstore.CrashStorageSystem.ERROR:
      raise Exception("CrashStorageSystem ERROR")
    return "CrashID=%s%s\n" % (self.dumpIDPrefix, ooid)
