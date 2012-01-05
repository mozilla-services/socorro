import datetime
import exceptions
import logging
import unittest

from nose.tools import *

import socorro.lib.util as util

from socorro.unittest.testlib.loggerForTest import TestingLogger
import socorro.unittest.testlib.util as tutil
from socorro.lib.datetimeutil import utc_now, UTC, string_to_datetime

def setup_module():
  tutil.nosePrintModule(__file__)

class TestingException(exceptions.Exception):
  pass

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
    assert(4 == len(logger.levels))
    assert([logging.ERROR, logging.ERROR, logging.ERROR, logging.ERROR] == logger.levels)
    print logger.buffer
    assert("Caught Error: None" == logger.buffer[0])
    assert('None' == logger.buffer[1]), "expected 'None' but got %s" % logger.buffer[1]
    assert("trace back follows:" in logger.buffer[2])
    logger.clear()
    util.reportExceptionAndContinue(logger, loggingLevel=-39)
    assert(4 == len(logger.levels))
    assert([-39, -39, -39, -39] == logger.levels)
    assert("Caught Error: None" == logger.buffer[0])
    assert('None' == logger.buffer[1])
    assert("trace back follows:" in logger.buffer[2])
    logger.clear()
    util.reportExceptionAndContinue(logger, ignoreFunction = ignoreAlways)
    assert([] == logger.levels)
    try:
      raise TestingException("test message")
    except TestingException, e:
      util.reportExceptionAndContinue(logger, loggingLevel=-12)
    print logger.levels
    print logger.buffer
    assert(6 == len(logger.levels))
    assert([-12,-12,-12,-12,-12,-12,] == logger.levels)
    assert("TestingException" in logger.buffer[0])
    assert("test message" == str(logger.buffer[1]))
    assert("raise TestingException" in logger.buffer[4])
    assert("test message" in logger.buffer[5])
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
    assert([-23,-23,-23,-23,-23,-23,] == logger.levels)
    assert("TestingException" in logger.buffer[0])
    assert("test message" == str(logger.buffer[1]))
    assert("raise TestingException" in logger.buffer[4])
    assert("test message" in logger.buffer[5])
    logger.clear()

  def testReportExceptionAndAbort(self):
    logger = TestingLogger()
    try:
      util.reportExceptionAndAbort(logger)
      assert(False)
    except SystemExit,e:
      assert(True)
      assert(5 == len(logger.levels))
      assert([logging.CRITICAL,logging.CRITICAL,logging.CRITICAL,logging.CRITICAL,logging.CRITICAL] == logger.levels)
      assert("cannot continue - quitting" == logger.buffer[4])

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
    assert(data == ci.cache), 'expected %s but got: %s' % (data, ci.cache)
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

  def testSignalNameFromNumber(self):
    assert 'SIG_UNKNOWN' == util.signalNameFromNumberMap.get(1000,'SIG_UNKNOWN'), '...but got %s'%util.signalNameFromNumber(1000)
    assert 'SIGTERM' == util.signalNameFromNumberMap.get(15), '...but got %s'%util.signalNameFromNumber(15)
    assert 'SIGKILL' == util.signalNameFromNumberMap.get(9), '...but got %s'%util.signalNameFromNumber(9)
    assert 'SIGHUP' == util.signalNameFromNumberMap.get(1), '...but got %s'%util.signalNameFromNumber(1)
    assert 'SIG_UNKNOWN' == util.signalNameFromNumberMap.get(-1,'SIG_UNKNOWN'), '...but got %s'%util.signalNameFromNumber(-1)

if __name__ == "__main__":
  unittest.main()

