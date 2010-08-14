class SpaceAgnosticString(str):
    """This specialized string class is just for equality comparisons.  It keeps
    a copy of itself without spaces.  On comparison, it takes the other string
    and makes a copy of it without spaces.  The equality comparison then takes
    place between the two space-free strings.  This is useful for comparing
    SQL strings that might span multiple lines.  When used in connection with
    the DummyObjectWithExpectations below, SQL strings can match even thought
    they are formatted differently."""
    def __init__(self, string=''):
        super(SpaceAgnosticString, self).__init__(string)
        self.noSpaceSelf = string.replace(' ', '').replace('\n','')
    def __eq__(self, other):
        noSpaceOther = other.replace(' ','').replace('\n','')
        return self.noSpaceSelf == noSpaceOther

class DummyObjectWithExpectations(object):
    """This class is a type of mock object.  It can simulate classes, class
    instances, modules or functions.  It is setup with a series of expected
    method calls with parameters.  When used in place of a real object, it
    responds with the return values or exceptions that it was programmed with.
    If the input or method call is not what is expected, an assertion error
    is raised. """
    def __init__(self, name=''):
        self._expected = []
        self.counter = 0
        self.name = name
    def expect (self, attribute, args, kwargs, returnValue=None,
                exceptionToRaise=None):
        self._expected.append((attribute,
                               args,
                               kwargs,
                               returnValue,
                               exceptionToRaise))
    def __getattr__(self, attribute):
        try:
            attributeExpected, argsExpected, kwargsExpected, returnValue, \
            exceptionToRaise = self._expected[self.counter]
        except IndexError:
            assert False, "%s expected no further references, but got '%s'" % \
                   (self.name, attribute)
        self.counter += 1
        if argsExpected is not None and kwargsExpected is not None:
            def f(*args, **kwargs):
                assert attributeExpected == attribute,  \
                       "%s expected attribute '%s', but got '%s'" % \
                       (self.name, attributeExpected, attribute)
                assert argsExpected == args, \
                       "%s expected '%s' arguments %s, but got %s" % \
                       (self.name, attribute, argsExpected, args)
                assert kwargsExpected == kwargs, \
                       "%s expected '%s' keyword arguments %s, but got %s" % \
                       (self.name, attribute, kwargsExpected, kwargs)
                if exceptionToRaise:
                    raise exceptionToRaise
                return returnValue
            return f
        else:
            assert attributeExpected == attribute, \
                   "%s expected attribute '%s', but got '%s'" % \
                   (self.name, attributeExpected, attribute)
            return returnValue
    def __call__(self, *args, **kwargs):
        attribute = '__call__'
        try:
            attributeExpected, argsExpected, kwargsExpected, returnValue, \
            exceptionToRaise = self._expected[self.counter]
        except IndexError:
            assert False, "%s expected no further references, but got '%s'" % \
                   (self.name, attribute)
        self.counter += 1
        assert attributeExpected == '__call__', \
               "%s expected attribute '%s', but got '%s'" % \
               (self.name, attributeExpected, attribute)
        assert argsExpected == args, \
               "%s expected '%s' arguments %s, but got %s" % \
               (self.name, attribute, argsExpected, args)
        assert kwargsExpected == kwargs, \
               "%s expected '%s' keyword arguments %s, but got %s" % \
               (self.name, attribute, kwargsExpected, kwargs)
        if exceptionToRaise:
            raise exceptionToRaise
        return returnValue
