#!/usr/bin/python
#
# Standalone collector
#

import os, cgi, sys, uuid, tempfile, simplejson
from datetime import datetime
from time import time
from stat import S_IRGRP, S_IROTH, S_IRUSR, S_IXOTH, S_IXUSR, S_IWUSR

# storage constants
storageRoot = "/tmp/dumps/"
dumpDirPrefix = "bp_"
jsonFileSuffix = ".json"
dumpFileSuffix = ".dump"
dumpPermissions = S_IRGRP | S_IROTH | S_IRUSR | S_IXOTH | S_IXUSR | S_IWUSR;
dumpField = "upload_file_minidump"

# the number of dumps to be stored in a single directory
dumpDirCount = 500

# returned to the client with a uuid following
dumpIDPrefix = "bp-"

def ensureDiskSpace():
  pass

def checkDumpQueue():
  pass

def backOffMessage():
  pass


def makeDumpDir(base):
  """Create a directory to hold a group of dumps, and set permissions"""
  tmpPath = tempfile.mkdtemp(dir=base, prefix=dumpDirPrefix)
  os.chmod(tmpPath, dumpPermissions)
  return tmpPath


def findLastModifiedDirInPath(path):
  names = os.listdir(path)
  breakpadDirs = [os.path.join(path, entry) for entry
                  in names if entry.startswith(dumpDirPrefix)]
  
  # This could happen if some other process or person has removed things
  # from our dated paths
  if len(breakpadDirs) == 0:
    return makeDumpDir(datePath)

  # Find the newest directory
  mtimeList = [(os.stat(path).st_mtime, fullpath) for fullpath in breakpadDirs
               if os.path.isdir(fullpath)]
  mtimeList.sort()
  latestDir = mtimeList[-1][1]
  return latestDir


#
# This will create date-partitioned paths, which the processor cronjob
# will come through and clean up in an os.walk() function.
#
# Example file stored on March 18th 2007, between 2 and 3 pm:
#
# /base/2007/03/18/14/bp_qew2f3/022c9812-bb4d-43cb-bf90-26b11f5a75d9.dump
#
# If the "bp_qew2f3" directory gets too full, another directory will
# be created by tempfile.mkdtemp, and eventually the code will move on
# to another hourly directory.
#
def getParentPathForDump():
  """Return a directory path to hold dump data, creating if necessary"""
  # First make an hourly directory if necessary
  utc = datetime.utcnow()
  datePath = os.path.join(storageRoot, str(utc.year), str(utc.month),
                          str(utc.day), str(utc.hour))

  # if it's not there yet, create the date directory and its first
  # dump directory
  if not os.path.exists(datePath):
    os.makedirs(datePath)
    os.chmod(datePath, dumpPermissions)
    return makeDumpDir(datePath)

  # return the last-modified dir if it has less than dumpCount entries,
  # otherwise make a new one
  latestDir = findLastModifiedDirInPath(datePath)
  if len(os.listdir(latestDir)) >= dumpDirCount:
    return makeDumpDir(datePath)
  
  return latestDir

def storeDump(form, dumpfile):
  """Stream the uploaded dump to a file, and store accompanying metadata.
Return uuid to client"""
  dirPath = getParentPathForDump()
  dumpID = str(uuid.uuid1())
  outfile = open(os.path.join(dirPath, dumpID + dumpFileSuffix), 'wb')

  # XXXsayrer need to peek at the first couple bytes for a sanity check
  # breakpad leading bytes: 0x504d444d  
  #
  try:
    while 1:
      data = dumpfile.read(4096)
      if not data:
        break
      outfile.write(data)
  finally:
    outfile.close()

  return (dumpID, dirPath)

def storeJSON(dumpID, dumpDir, form):
  names = [name for name in form.keys() if name != dumpField]
  fields = {}
  for name in names:
    fields[name] = form[name].value
  fields["timestamp"] = time() 
  outfile = open(os.path.join(dumpDir, dumpID + jsonFileSuffix), 'w')
  try:
    simplejson.dump(fields, outfile)
  finally:
    outfile.close()

#
# HTTP functions
#
method = os.environ['REQUEST_METHOD']
methodNotSupported = "Status: 405 Method Not Supported"
badRequest = "Status: 400 Bad Request"
internalServerError = "Status: 500 Internal Server Error"

def cgiprint(inline=''):
  sys.stdout.write(inline)
  sys.stdout.write('\r\n')
  sys.stdout.flush()

def sendHeaders(headers):
  for h in headers:
    cgiprint(h)
  cgiprint()

if __name__ == "__main__":
  if method == "POST":
    theform = cgi.FieldStorage()
    dump = theform[dumpField]
    if dump.file:
      (dumpID, dumpPath) = storeDump(theform, dump.file)
      storeJSON(dumpID, dumpPath, theform)
      cgiprint("Content-Type: text/plain")
      cgiprint()
      print dumpIDPrefix + dumpID
    else:
      sendHeaders([badRequest])
  elif method == "GET":
    cgiprint("Content-Type: text/html")
    cgiprint()
    print "<b>hmm</b>"
  else:
    sendHeaders([methodNotSupported])
