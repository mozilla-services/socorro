#!/usr/bin/python

#
# A mod_python environment for the crash report collector
#

import datetime as dt
import config.collectorconfig as configModule
import socorro.collector.initializer
import socorro.lib.util as sutil

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
    persistentStorage = socorro.collector.initializer.createPersistentInitialization(configModule)

  logger = persistentStorage["logger"]
  config = persistentStorage["config"]
  collectObject = persistentStorage["collectObject"]

  logger.debug("handler invoked using subinterpreter: %s", req.interpreter)

  if req.method == "POST":
    try:
      theform = util.FieldStorage(req)
      dump = theform[config.dumpField]
      if not dump.file:
        return apache.HTTP_BAD_REQUEST

      jsonDataDictionary = collectObject.makeJsonDictFromForm(theform)
      if collectObject.throttle(jsonDataDictionary):
        fileSystemStorage = persistentStorage["deferredFileSystemStorage"]
      else:
        fileSystemStorage = persistentStorage["standardFileSystemStorage"]
      uuid = collectObject.generateUuid(jsonDataDictionary)

      jsonFileHandle, dumpFileHandle = fileSystemStorage.newEntry(uuid, persistentStorage["hostname"], dt.datetime.now())
      try:
        collectObject.storeDump(dump.file, dumpFileHandle)
        collectObject.storeJson(jsonDataDictionary, jsonFileHandle)
      finally:
        dumpFileHandle.close()
        jsonFileHandle.close()

      req.content_type = "text/plain"
      req.write("CrashID=%s%s\n" % (config.dumpIDPrefix, uuid))
    except:
      logger.info("mod-python subinterpreter name: %s", req.interpreter)
      sutil.reportExceptionAndContinue(logger)
      #print >>sys.stderr, "Exception: %s" % sys.exc_info()[0]
      #print >>sys.stderr, sys.exc_info()[1]
      #print >>sys.stderr
      #sys.stderr.flush()
      return apache.HTTP_INTERNAL_SERVER_ERROR
    return apache.OK
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
