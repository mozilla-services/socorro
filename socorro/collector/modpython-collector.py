#!/usr/bin/python
#
# A mod_python environment for the crash report collector
#

import datetime as dt
import config.collectorconfig as configModule
import socorro.collector.initializer
import socorro.lib.util as sutil
import socorro.lib.ooid as ooid

#profiling, remove me soon
import time
def mprofile(message, before, logger):
  logger.info("%s %s" % (time.time() - before, message))

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
  beforeHandler = time.time()
  global persistentStorage
  try:
    x = persistentStorage
  except NameError:
    persistentStorage = socorro.collector.initializer.createPersistentInitialization(configModule)

  logger = persistentStorage["logger"]
  config = persistentStorage["config"]
  collectObject = persistentStorage["collectObject"]

  #logger.debug("handler invoked using subinterpreter: %s", req.interpreter)
  if req.method == "POST":
    try:
      req.content_type = "text/plain"

      theform = util.FieldStorage(req)
      dump = theform[config.dumpField]
      if not dump.file:
        return apache.HTTP_BAD_REQUEST

      currentTimestamp = dt.datetime.now()

      jsonDataDictionary = collectObject.makeJsonDictFromForm(theform)
      jsonDataDictionary["submitted_timestamp"] = currentTimestamp.isoformat()

      #for future use when we start sunsetting products
      #if collectObject.terminated(jsonDataDictionary):
        #req.write("Terminated=%s" % jsonDataDictionary['version'])
        #return apache.OK

      if "Throttleable" not in jsonDataDictionary or int(jsonDataDictionary["Throttleable"]):
        if collectObject.throttle(jsonDataDictionary):
          #logger.debug('yes, throttle this one')
          if collectObject.understandsRefusal(jsonDataDictionary) and not config.neverDiscard:
            logger.debug("discarding %s %s", jsonDataDictionary["ProductName"], jsonDataDictionary["Version"])
            req.write("Discarded=1\n")
            return apache.OK
          else:
            logger.debug("deferring %s %s", jsonDataDictionary["ProductName"], jsonDataDictionary["Version"])
            fileSystemStorage = persistentStorage["deferredFileSystemStorage"]
        else:
          logger.debug("not throttled %s %s", jsonDataDictionary["ProductName"], jsonDataDictionary["Version"])
          fileSystemStorage = persistentStorage["standardFileSystemStorage"]
      else:
        logger.debug("cannot be throttled %s %s", jsonDataDictionary["ProductName"], jsonDataDictionary["Version"])
        fileSystemStorage = persistentStorage["standardFileSystemStorage"]

      uuid = ooid.createNewOoid(currentTimestamp, persistentStorage["config"].storageDepth)
      logger.debug("    %s", uuid)

      jsonFileHandle, dumpFileHandle = fileSystemStorage.newEntry(uuid, persistentStorage["hostname"], dt.datetime.now())
      try:

        beforeDisk = time.time()
        collectObject.storeDump(dump.file, dumpFileHandle)
        collectObject.storeJson(jsonDataDictionary, jsonFileHandle)
        mprofile("Wrote to disk", beforeDisk, logger) 
      finally:
        dumpFileHandle.close()
        jsonFileHandle.close()

      try:
        logger.info("about to create ooid %s" % str(jsonDataDictionary))
        beforeHbase = time.time()
        persistentStorage["hbaseConnection"].create_ooid(uuid, str(jsonDataDictionary), dumpData)
        mprofile("Wrote to hbase", beforeHbase, logger)
      except:
        sutil.reportExceptionAndContinue(logger)

      req.write("CrashID=%s%s\n" % (config.dumpIDPrefix, uuid))
      mprofile("Finished Handler", beforeHandler, logger)
      return apache.OK
    except:
      logger.info("mod-python subinterpreter name: %s", req.interpreter)
      sutil.reportExceptionAndContinue(logger)
      #print >>sys.stderr, "Exception: %s" % sys.exc_info()[0]
      #print >>sys.stderr, sys.exc_info()[1]
      #print >>sys.stderr
      #sys.stderr.flush()
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
