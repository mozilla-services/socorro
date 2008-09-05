import unittest
import logging
import util
import exceptions

class TestingException(exceptions.Exception):
  pass
    
class TestingLogger:
  def __init__(self):
    self.levels = []
    self.buffer = []
    
  def log(self, loggingLevel, message, *args):
    self.levels.append(loggingLevel)
    if not message: message = ''
    if args:
      self.buffer.append(message % args)
    else:
      self.buffer.append(message)
  def info(self, message):
    self.log(logging.INFO,message)
  def critical(self, message):
    self.log(logging.CRITICAL,message)

  def clear(self):
    self.levels = []
    self.buffer = []

def ignoreAlways(*args, **kwargs):
  return True
def ignoreNever(*args,**kwargs):
  return False
    
class TestUtil(unittest.TestCase):
  def setUp(self):
    pass
    
  def tearDown(self):
    pass

  def testReportExceptionAndContinue(self):
    logger = TestingLogger()
    util.reportExceptionAndContinue(logger)
    assert(3 == len(logger.levels))
    assert([logging.ERROR, logging.ERROR, logging.INFO] == logger.levels)
    assert("MainThread Caught Error: None" == logger.buffer[0])
    assert('' == logger.buffer[1])
    assert("trace back follows:" in logger.buffer[2])
    logger.clear()
    util.reportExceptionAndContinue(logger, loggingLevel=-39)
    assert(3 == len(logger.levels))
    assert([-39, -39, logging.INFO] == logger.levels)
    assert("MainThread Caught Error: None" == logger.buffer[0])
    assert('' == logger.buffer[1])
    assert("trace back follows:" in logger.buffer[2])
    logger.clear()
    util.reportExceptionAndContinue(logger, ignoreFunction = ignoreAlways)
    assert([] == logger.levels)
    try:
      raise TestingException("test message")
    except TestingException, e:
      util.reportExceptionAndContinue(logger, loggingLevel=-12)
    assert(3 == len(logger.levels))
    assert([-12,-12,logging.INFO] == logger.levels)
    assert("TestingException" in logger.buffer[0])
    assert("test message" == str(logger.buffer[1]))
    assert("raise TestingException" in logger.buffer[2])
    assert("test message" in logger.buffer[2])
    logger.clear()
    try:
      raise TestingException("test message")
    except TestingException, e:
      util.reportExceptionAndContinue(logger, loggingLevel=-23, ignoreFunction=ignoreAlways)
    assert([] == logger.buffer)
    logger.clear()
    try:
      raise TestingException("test message")
    except TestingException, e:
      util.reportExceptionAndContinue(logger, loggingLevel=-23, ignoreFunction=ignoreNever)
    assert([-23,-23,logging.INFO] == logger.levels)
    assert("TestingException" in logger.buffer[0])
    assert("test message" == str(logger.buffer[1]))
    assert("raise TestingException" in logger.buffer[2])
    assert("test message" in logger.buffer[2])
    logger.clear()

  def testReportExceptionAndAbort(self):
    logger = TestingLogger()
    try:
      util.reportExceptionAndAbort(logger)
      assert(False)
    except SystemExit,e:
      assert(True)
      assert(4 == len(logger.levels))
      assert([logging.CRITICAL,logging.CRITICAL,logging.INFO,logging.CRITICAL] == logger.levels)
      assert("cannot continue - quitting" == logger.buffer[3])

  def testLimitedStringOrNone(self):
    assert("key" == util.limitStringOrNone("key",8))
    assert("key" == util.limitStringOrNone("keyway",3))
    assert(None == util.limitStringOrNone(14,2))
    
  def testLookupLimitedStringOrNone(self):
    dict = {"key":"value"}
    assert("value" == util.lookupLimitedStringOrNone(dict,"key",8))
    assert("val" == util.lookupLimitedStringOrNone(dict,"key",3))
    assert(None == util.lookupLimitedStringOrNone(dict,"not",33))
  
  def testCachingIterator(self):
    max = 25
    data = [ x for x in range(0,max)]
    ci = util.CachingIterator(iter(data))
    citer = iter(ci)
    expected = 0
    while True:
      assert(expected == citer.next())
      expected += 1
      if expected == max: break
    assert(data == ci.cache)
    assert(0 == len(ci.secondaryLimitedSizeCache))

    # start over, using secondary cache instead
    ci = util.CachingIterator(iter(data))
    ci.useSecondaryCache()
    citer = iter(ci)
    expected = 0
    while True:
      assert(expected == citer.next())
      expected += 1
      if expected == max: break
    assert(0 == len(ci.cache))
    assert(ci.secondaryCacheMaximumSize == len(ci.secondaryLimitedSizeCache))
    assert(ci.secondaryLimitedSizeCache[-1] == max - 1)

if __name__ == "__main__":
  unittest.main()
  
