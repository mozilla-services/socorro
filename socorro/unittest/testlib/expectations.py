class DummyObjectWithExpectations(object):
  """a class that will accept a series of method calls with arguments, but will raise assertion
     errors if the calls and arguments are not what is expected.
  """
  def __init__(self, name=''):
    self._expected = []
    self.counter = 0
    self.name = name
  def expect (self, attribute, args, kwargs, returnValue=None, exceptionToRaise=None):
    self._expected.append((attribute, args, kwargs, returnValue, exceptionToRaise))
  def __getattr__(self, attribute):
    def f(*args, **kwargs):
      try:
        attributeExpected, argsExpected, kwargsExpected, returnValue, exceptionToRaise = self._expected[self.counter]
      except IndexError:
        assert False, "%s expected no further calls, but got '%s' with args: %s and kwargs: %s" % (self.name, attribute, args, kwargs)
      self.counter += 1
      assert attributeExpected == attribute, "%s expected attribute '%s', but got '%s'" % (self.name, attributeExpected, attribute)
      assert argsExpected == args, "%s expected '%s' arguments %s, but got %s" % (self.name, attribute, argsExpected, args)
      assert kwargsExpected == kwargs, "%s expected '%s' keyword arguments %s, but got %s" % (self.name, attribute, kwargsExpected, kwargs)
      if exceptionToRaise:
        raise exceptionToRaise
      return returnValue
    return f

