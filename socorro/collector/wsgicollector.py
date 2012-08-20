# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

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

    # Remove other submitted files from the input form, which are an indication
    # of a multi-dump hang submission we aren't yet prepared to handle.
    for (key, value) in web.webapi.rawinput().iteritems():
      if hasattr(value, 'file') and hasattr(value, 'value'):
        del theform[key]

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
