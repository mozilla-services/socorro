#!/usr/bin/python

import urllib2
import simplejson
import sys

def loadpost(filename):
  dict = simplejson.load(open(filename,'r'))
  if dict:
    return dict
  else:
    print "unable to load json from",repr(options.jsonfile)
    return {}

def submitCrashReport (jsonFilePathName, binaryFilePathName, serverURL):
  data = {}
  if jsonFilePathName:
    data = loadpost(jsonFilePathName)
  if binaryFilePathName:
    data['upload_file_minidump'] = open(binaryFilePathName,'r')
  if data:
    urllib2.urlopen(serverURL,data)

def walkFileSystemSubmittingReports (fileSystemRoot, serverURL):
  for aPath, aFileName, aJsonPathName in socorro.lib.filesystem(fileSystemRoot, lambda x: x[2].endswith("json")):
    try:
      dumpfilePathName = os.path.join(aPath, "%s%s" % (aFileName[:-5], ".dump"))
      submitCrashReport(aJsonPathName, dumpfilePathName, serverURL)
    except IOError:
      pass

if __name__ == '__main__':
  import socorro.lib.ConfigurationManager
  import os.path

  commandLineOptions = [
    ('c',  'config', True, './config', "the config file"),
    ('u',  'url', True, 'http://localhost/crash-reports/submit', "The url of the server to load test"),
    ('j',  'jsonfile', True, None, 'the pathname of a json file for POST'),
    ('d',  'dumpfile', False, None, 'the pathname of a dumpfile to upload with the POST'),
    (None, 'searchRoot', True, None, 'a filesystem location to begin a search for json/dump combos'),
    ]

  config = socorro.lib.ConfigurationManager.newConfiguration(configurationOptionsList=commandLineOptions)

  if config.searchRoot:
    walkFileSystemSubmittingReports(config.searchRoot, config.url)
  else:
    submitCrashReport(config.jsonfile, config.dumpfile, config.url)




