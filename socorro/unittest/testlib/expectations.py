class DummyObjectWithExpectations(object):
  """a class that will accept a series of method calls with arguments, but will raise assertion
     errors if the calls and arguments are not what is expected.
  """
  def __init__(self):
    self._expected = []
    self.counter = 0
  def expect (self, attribute, args, kwargs, returnValue = None):
    self._expected.append((attribute, args, kwargs, returnValue))
  def __getattr__(self, attribute):
    def f(*args, **kwargs):
      try:
        attributeExpected, argsExpected, kwargsExpected, returnValue = self._expected[self.counter]
      except IndexError:
        assert False, "expected no further calls, but got '%s' with args: %s and kwargs: %s" % (attribute, args, kwargs)
      self.counter += 1
      assert attributeExpected == attribute, "expected attribute '%s', but got '%s'" % (attributeExpected, attribute)
      assert argsExpected == args, "expected '%s' arguments %s, but got %s" % (attribute, argsExpected, args)
      assert kwargsExpected == kwargs, "expected '%s' keyword arguments %s, but got %s" % (attribute, kwargsExpected, kwargs)
      return returnValue
    return f

