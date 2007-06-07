""" utilities for setting cache headers """
import md5
import rfc822
import time
from datetime import datetime, timedelta
from pylons.helpers import etag_cache

def responseForKey(key, expires=None):
  """Requires a key argument that will be hashed as the value of the etag,
     and takes an optional argument, expires, that will set the header of
     that name for the given number of seconds"""
  m = md5.new()
  m.update(key)
  resp = etag_cache(m.hexdigest())
  if expires is not None:
    exp = datetime.now() + timedelta(seconds=expires) 
    resp.headers["Expires"] = rfc822.formatdate(time.mktime(exp.timetuple()))
  return resp
