from socorro.unittest.testlib.loggerForTest import TestingLogger

import logging

import socorro.unittest.testlib.util as tutil

def setup_module():
  tutil.nosePrintModule(__file__)

class BogusLogger:
  def __init__(self):
    self.item = None
  def log(self,level,message,*args):
    self.item = (level,message,args)

def testConstructor():
  tl = TestingLogger()
  bl = BogusLogger()
  assert None == tl.logger
  assert 6 == len(tl.levelcode)
  expected = {0:'NOTSET',10:'DEBUG',20:'INFO',30:'WARNING',40:'ERROR',50:'FATAL'}
  for c in expected.keys():
    assert expected[c] == tl.levelcode[c], 'But at %s expected %s got %s'%(c,expected[c],lc.levelcode[c])

  tl = TestingLogger(bl)
  assert bl is tl.logger
  assert None == bl.item

def testLog():
  bl = BogusLogger()
  tl = TestingLogger()
  tlb = TestingLogger(bl)
  for level in range(0,60,10):
    tl.log(level,'message')
    tlb.log(level,'message')
    assert 'message' == tl.buffer[-1]
    assert level == tl.levels[-1]
    assert (level,'message',()) == bl.item
  tl = TestingLogger()
  tlb = TestingLogger(bl)
  for level in range(0,60,10):
    tl.log(level,'message %s %s','one','two')
    tlb.log(level,'message %s %s','one','two')
    assert 'message one two' == tl.buffer[-1]
    assert (level,'message %s %s',('one','two')) == bl.item

def testDebug():
  bl = BogusLogger()
  tl = TestingLogger()
  tlb = TestingLogger(bl)
  tl.debug("bug")
  tlb.debug("bug")
  assert (logging.DEBUG,'bug',()) == bl.item
  assert logging.DEBUG == tl.levels[0]
  assert logging.DEBUG == tlb.levels[0]
  assert 'bug' == tl.buffer[0]
  assert 'bug' == tlb.buffer[0]

def testInfo():
  bl = BogusLogger()
  tl = TestingLogger()
  tlb = TestingLogger(bl)
  tl.info("info")
  tlb.info("info")
  assert (logging.INFO,'info',()) == bl.item
  assert logging.INFO == tl.levels[0]
  assert logging.INFO == tlb.levels[0]
  assert 'info' == tl.buffer[0]
  assert 'info' == tlb.buffer[0]

def testWarning():
  bl = BogusLogger()
  tl = TestingLogger()
  tlb = TestingLogger(bl)
  tl.warning("warning")
  tlb.warning("warning")
  assert (logging.WARNING,'warning',()) == bl.item
  assert logging.WARNING == tl.levels[0]
  assert logging.WARNING == tlb.levels[0]
  assert 'warning' == tl.buffer[0]
  assert 'warning' == tlb.buffer[0]

def testWarn():
  bl = BogusLogger()
  tl = TestingLogger()
  tlb = TestingLogger(bl)
  tl.warn("warn")
  tlb.warn("warn")
  assert (logging.WARN,'warn',()) == bl.item
  assert logging.WARN == tl.levels[0]
  assert logging.WARN == tlb.levels[0]
  assert 'warn' == tl.buffer[0]
  assert 'warn' == tlb.buffer[0]

def testError():
  bl = BogusLogger()
  tl = TestingLogger()
  tlb = TestingLogger(bl)
  tl.error("error")
  tlb.error("error")
  assert (logging.ERROR,'error',()) == bl.item
  assert logging.ERROR == tl.levels[0]
  assert logging.ERROR == tlb.levels[0]
  assert 'error' == tl.buffer[0]
  assert 'error' == tlb.buffer[0]

def testCritical():
  bl = BogusLogger()
  tl = TestingLogger()
  tlb = TestingLogger(bl)
  tl.critical("critical")
  tlb.critical("critical")
  assert (logging.CRITICAL,'critical',()) == bl.item
  assert logging.CRITICAL == tl.levels[0]
  assert logging.CRITICAL == tlb.levels[0]
  assert 'critical' == tl.buffer[0]
  assert 'critical' == tlb.buffer[0]

def testFatal():
  bl = BogusLogger()
  tl = TestingLogger()
  tlb = TestingLogger(bl)
  tl.fatal("fatal")
  tlb.fatal("fatal")
  assert (logging.FATAL,'fatal',()) == bl.item
  assert logging.FATAL == tl.levels[0]
  assert logging.FATAL == tlb.levels[0]
  assert 'fatal' == tl.buffer[0]
  assert 'fatal' == tlb.buffer[0]

def testStrFunction():
  tl = TestingLogger()
  assert '' == str(tl)
  tl.debug('debug')
  expLines = ['DEBUG   (10): debug']
  tl.info('info')
  expLines.append('INFO    (20): info')
  tl.warn('warn')
  expLines.append('WARNING (30): warn')
  tl.warning('warning')
  expLines.append('WARNING (30): warning')
  tl.error('error')
  expLines.append('ERROR   (40): error')
  tl.critical('critical')
  expLines.append('FATAL   (50): critical')
  tl.fatal('fatal')
  expLines.append('FATAL   (50): fatal')
  expected = "\n".join(expLines)
  assert expected == str(tl)

def testLenFunction():
  tl = TestingLogger()
  exp = 0
  assert exp == len(tl)
  tl.debug('woo')
  exp += 1
  assert exp == len(tl)
  tl.info('woo')
  exp += 1
  assert exp == len(tl)
  tl.warning('woo')
  exp += 1
  assert exp == len(tl)
  tl.warn('woo')
  exp += 1
  assert exp == len(tl)
  tl.error('woo')
  exp += 1
  assert exp == len(tl)
  tl.critical('woo')
  exp += 1
  assert exp == len(tl)
  tl.fatal('woo')
  exp += 1
  assert exp == len(tl)

def testClear():
  tl = TestingLogger()
  tl.clear()
  assert 0 == len(tl)
  assert 0 == len(tl.levels)
  assert 0 == len(tl.buffer)

  tl.debug('woo')
  tl.info('woo')
  tl.warning('woo')
  tl.warn('woo')
  tl.error('woo')
  tl.critical('woo')
  tl.fatal('woo')

  assert 7 == len(tl)
  assert 7 == len(tl.levels)
  assert 7 == len(tl.buffer)

  tl.clear()
  assert 0 == len(tl)
  assert 0 == len(tl.levels)
  assert 0 == len(tl.buffer)

#def testFormatOne(): handled by testStrFunction()
