#!/usr/bin/python

import simplejson
import sys
import pycurl
import socorro.lib.filesystem
import socorro.lib.uuid as uuid

existingHangIdCache = {}

def submitCrashReport (jsonFilePathName, binaryFilePathName, serverURL, uniqueHang):
  jsonFile = open(jsonFilePathName)
  try:
    data = simplejson.load(jsonFile)
  finally:
    jsonFile.close()

  if uniqueHang:
    try:
      if data['HangId'] in existingHangIdCache:
        data['HangId'] = existingHangIdCache
      else:
        data['HangId'] = existingHangIdCache[data['HangId']] = uuid.uuid4()
    except:
      pass

  c = pycurl.Curl()
  fields = [(str(t[0]), str(t[1])) for t in data.items()]
  fields.append (("upload_file_minidump", (c.FORM_FILE, binaryFilePathName)))
  c.setopt(c.TIMEOUT, 10)
  c.setopt(c.POST, 1)
  c.setopt(c.URL, serverURL)
  c.setopt(c.HTTPPOST, fields)
  c.perform()
  c.close()

def reportErrorToStderr (x):
  print >>sys.stderr, x

def walkFileSystemSubmittingReports (fileSystemRoot, serverURL, errorReporter=reportErrorToStderr, uniqueHang=False):
  for aPath, aFileName, aJsonPathName in socorro.lib.filesystem.findFileGenerator(fileSystemRoot, lambda x: x[2].endswith("json")):
    try:
      dumpfilePathName = os.path.join(aPath, "%s%s" % (aFileName[:-5], ".dump"))
      submitCrashReport(aJsonPathName, dumpfilePathName, serverURL, uniqueHang)
    except KeyboardInterrupt:
      break
    except Exception, x:
      errorReporter(x)

if __name__ == '__main__':
  import socorro.lib.ConfigurationManager

  import os.path
  import traceback

  def myErrorReporter (anException):
    print >>sys.stderr, type(anException), anException
    exceptionType, exception, tracebackInfo = sys.exc_info()
    traceback.print_tb(tracebackInfo, None, sys.stderr)

  commandLineOptions = [
    ('c',  'config', True, './config', "the config file"),
    ('u',  'url', True, 'https://crash-reports.stage.mozilla.com/submit', "The url of the server to load test"),
    ('j',  'jsonfile', True, None, 'the pathname of a json file for POST'),
    ('d',  'dumpfile', True, None, 'the pathname of a dumpfile to upload with the POST'),
    ('s',  'searchRoot', True, None, 'a filesystem location to begin a search for json/dump combos'),
    ('i',  'uniqueHangId', False, None, 'coche and uniquify hangids'),
    ]

  config = socorro.lib.ConfigurationManager.newConfiguration(configurationOptionsList=commandLineOptions)

  uniqueHang = 'uniqueHangId' in config

  if config.searchRoot:
    walkFileSystemSubmittingReports(config.searchRoot, config.url, myErrorReporter, uniqueHang)
  else:
    try:
      submitCrashReport(config.jsonfile, config.dumpfile, config.url, uniqueHang)
    except Exception, x:
      myErrorReporter(x)

