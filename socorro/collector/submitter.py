#!/usr/bin/python

import simplejson
import sys
import pycurl
import socorro.lib.filesystem

def submitCrashReport (jsonFilePathName, binaryFilePathName, serverURL):
  jsonFile = open(jsonFilePathName)
  try:
    data = simplejson.load(jsonFile)
  finally:
    jsonFile.close()

  c = pycurl.Curl()
  fields = [(str(t[0]), str(t[1])) for t in data.items()]
  fields.append (("upload_file_minidump", (c.FORM_FILE, binaryFilePathName)))
  c.setopt(c.POST, 1)
  c.setopt(c.URL, serverURL)
  c.setopt(c.HTTPPOST, fields)
  c.perform()
  c.close()

def reportErrorToStderr (x):
  print >>sys.stderr, x

def walkFileSystemSubmittingReports (fileSystemRoot, serverURL, errorReporter=reportErrorToStderr):
  for aPath, aFileName, aJsonPathName in socorro.lib.filesystem.findFileGenerator(fileSystemRoot, lambda x: x[2].endswith("json")):
    try:
      dumpfilePathName = os.path.join(aPath, "%s%s" % (aFileName[:-5], ".dump"))
      submitCrashReport(aJsonPathName, dumpfilePathName, serverURL)
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
    ('u',  'url', True, 'http://localhost/crash-reports/submit', "The url of the server to load test"),
    ('j',  'jsonfile', True, None, 'the pathname of a json file for POST'),
    ('d',  'dumpfile', True, None, 'the pathname of a dumpfile to upload with the POST'),
    ('s',  'searchRoot', True, None, 'a filesystem location to begin a search for json/dump combos'),
    ]

  config = socorro.lib.ConfigurationManager.newConfiguration(configurationOptionsList=commandLineOptions)

  if config.searchRoot:
    walkFileSystemSubmittingReports(config.searchRoot, config.url, myErrorReporter)
  else:
    try:
      submitCrashReport(config.jsonfile, config.dumpfile, config.url)
    except Exception, x:
      myErrorReporter(x)




