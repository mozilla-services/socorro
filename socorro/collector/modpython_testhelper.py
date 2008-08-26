# this is a test being run from the command line
# these objects are to provide a fake environment for testing
class FakeApache(object):
  def __init__(self):
    self.HTTP_BAD_REQUEST = "HTTP_BAD_REQUEST"
    self.HTTP_INTERNAL_SERVER_ERROR = "HTTP_INTERNAL_SERVER_ERROR"
    self.OK = "OK"
    self.HTTP_METHOD_NOT_ALLOWED = "HTTP_METHOD_NOT_ALLOWED"
apache = FakeApache()
class FakeUtil(object):
  @staticmethod
  def FieldStorage(req):
    return req.fields
util = FakeUtil()
class FakeReq(object):
  def write(self, x):
    print x
class FakeDump(object):
  def __init__(self, anObject):
    self.file = anObject
class FakeFile(object):
  def __init__(self, data):
    self.data = data
    self.numberOfReadCalls = 0
  def read(self, x):
    if self.numberOfReadCalls > 0:
      return None
    else:
      self.numberOfReadCalls += 1
      return self.data