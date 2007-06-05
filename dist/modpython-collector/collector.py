#
# A mod_python environment for the crash report collector
#

import collect
import config
from mod_python import apache
from mod_python import util

def handler(req):
  if req.method == "POST":
    try:
      theform = util.FieldStorage(req)
      dump = theform[config.dumpField]
      if not dump.file:
        return apache.HTTP_BAD_REQUEST
      (dumpID, dumpPath, dateString) = collect.storeDump(dump.file)
      collect.storeJSON(dumpID, dumpPath, theform)
      req.content_type = "text/plain"
      req.write(collect.makeResponseForClient(dumpID, dateString))
    except:
      return apache.HTTP_INTERNAL_SERVER_ERROR
    return apache.OK
  else:
    return apache.HTTP_METHOD_NOT_ALLOWED
