#!/usr/bin/python

import urllib2
import simplejson
import sys
import socorro.lib.filesystem

def submitCrashReport (jsonFilePathName, binaryFilePathName, serverURL):
  jsonFile = open(jsonFilePathName)
  try:
    data = simplejson.load(jsonFile)
  finally:
    jsonFile.close()
  binaryFile = open(binaryFilePathName)
  try:
    data['upload_file_minidump'] = binaryFile
    urllib2.urlopen(serverURL,data)
  finally:
    binaryFile.close()

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

  commandLineOptions = [
    ('c',  'config', True, './config', "the config file"),
    ('u',  'url', True, 'http://localhost/crash-reports/submit', "The url of the server to load test"),
    ('j',  'jsonfile', True, None, 'the pathname of a json file for POST'),
    ('d',  'dumpfile', False, None, 'the pathname of a dumpfile to upload with the POST'),
    ('s',  'searchRoot', True, None, 'a filesystem location to begin a search for json/dump combos'),
    ]

  config = socorro.lib.ConfigurationManager.newConfiguration(configurationOptionsList=commandLineOptions)

  if config.searchRoot:
    walkFileSystemSubmittingReports(config.searchRoot, config.url)
  else:
    try:
      submitCrashReport(config.jsonfile, config.dumpfile, config.url)
    except Exception, x:
      print >>sys.sterr, x




