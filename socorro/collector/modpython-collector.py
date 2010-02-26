#!/usr/bin/python
#
# A mod_python environment for the crash report collector
#

import datetime as dt
import config.collectorconfig as configModule
import socorro.collector.initializer as init
import socorro.collector.collect as collect
import socorro.lib.util as sutil
import socorro.lib.ooid as ooid

import random

#-----------------------------------------------------------------------------------------------------------------
if __name__ != "__main__":
  from mod_python import apache
  from mod_python import util
else:
  # this is a test being run from the command line
  # these objects are to provide a fake environment for testing
  from socorro.collector.modpython_testhelper import apache
  from socorro.collector.modpython_testhelper import util

#-----------------------------------------------------------------------------------------------------------------
def handler(req):
  global persistentStorage
  try:
    x = persistentStorage
  except NameError:
    persistentStorage = init.createPersistentInitialization(configModule)

  logger = persistentStorage.logger
  config = persistentStorage.config
  nfsCrashStorage = persistentStorage.nfsStorage
  try:
    hbaseCrashStorage = persistentStorage.hbaseStorage
  except KeyError:
    pass

  #logger.debug("handler invoked using subinterpreter: %s", req.interpreter)
  if req.method == "POST":
    try:
      req.content_type = "text/plain"

      theform = util.FieldStorage(req)
      dump = theform[config.dumpField]
      if not dump.file:
        return apache.HTTP_BAD_REQUEST
      dump = collect.RepeatableStreamReader(dump.file)

      currentTimestamp = dt.datetime.now()

      jsonDataDictionary = nfsCrashStorage.makeJsonDictFromForm(theform)
      jsonDataDictionary.submitted_timestamp = currentTimestamp.isoformat()

      #for future use when we start sunsetting products
      #if nfsCrashStorage.terminated(jsonDataDictionary):
        #req.write("Terminated=%s" % jsonDataDictionary.Version)
        #return apache.OK

      uuid = ooid.createNewOoid(currentTimestamp, config.storageDepth)
      logger.debug("    %s", uuid)

      nfsResult = nfsCrashStorage.save(uuid, jsonDataDictionary, dump)

      if config.hbaseSubmissionRate:
        if random.random() * 100.0 < config.hbaseSubmissionRate:
          logger.info("about to create ooid %s in hbase" % uuid)
          hbaseResult = hbaseCrashStorage.save(uuid, jsonDataDictionary, dump)
        else:
          logger.info('%s throttled and not submitted to hbase', uuid)

      if nfsResult == collect.CrashStorageSystem.DISCARDED:
        req.write("Discarded=1\n")
        return apache.OK
      elif nfsResult == collect.CrashStorageSystem.ERROR:
        return apache.HTTP_INTERNAL_SERVER_ERROR
      req.write("CrashID=%s%s\n" % (config.dumpIDPrefix, uuid))
      return apache.OK
    except:
      logger.info("mod-python subinterpreter name: %s", req.interpreter)
      sutil.reportExceptionAndContinue(logger)

      return apache.HTTP_INTERNAL_SERVER_ERROR
  else:
    return apache.HTTP_METHOD_NOT_ALLOWED

#-----------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
  from socorro.collector.modpython_testhelper import *

  req = FakeReq()
  req.method = "POST"
  req.fields = {
    "StartupTime": "1206120381",
    "Vendor": "Mozilla",
    "InstallTime": "1204828702",
    #"timestamp": "1206206829.56",
    "Add-ons": "{19503e42-ca3c-4c27-b1e2-9cdb2170ee34}:0.8.3,inspector@mozilla.org:1.9b4pre,{972ce4c6-7e08-4474-a285-3208198ce6fd}:2.0",
    "BuildID": "2008022517",
    "SecondsSinceLastCrash": "63935",
    "UserID": "d6d2b6b0-c9e0-4646-8627-0b1bdd4a92bb",
    "ProductName": "Firefox",
    "URL": "http:\/\/www.google.com.ar\/search?hl=es&defl=es&q=define:ARN&sa=X&oi=glossary_definition&ct=title",
    "Theme": "classic\/1.0",
    "Version": "3.0b4pre",
    "CrashTime": "1206120413",
    "upload_file_minidump":FakeDump(FakeFile("this is a dump"))
  }
  req.interpreter = "FakeReq interpreter"

  print handler(req)
