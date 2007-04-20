#!/usr/bin/python
#
# A CGI environment for the crash report collector
#

import standalone_collector
import config
import os
import sys
import cgi

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
    try:
      theform = cgi.FieldStorage()
      dump = theform[config.dumpField]
      if dump.file:
        (dumpID, dumpPath) = standalone_collector.storeDump(theform, dump.file)
        standalone_collector.storeJSON(dumpID, dumpPath, theform)
        cgiprint("Content-Type: text/plain")
        cgiprint()
        print standalone_collector.makeResponseForClient(dumpID)
      else:
        sendHeaders([badRequest])
    except:
      sendHeaders([internalServerError])
  else:
    sendHeaders([methodNotSupported])
