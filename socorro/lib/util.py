import sys
import traceback
import datetime
import cStringIO
import threading
import collections

import logging

#=================================================================================================================
class FakeLogger(object):
  loggingLevelNames = { logging.DEBUG: "DEBUG",
                        logging.INFO: "INFO",
                        logging.WARNING: "WARNING",
                        logging.ERROR: "ERROR",
                        logging.CRITICAL: "CRITICAL"
                      }
  def log(self,*x):
    try:
      loggingLevelString = FakeLogger.loggingLevelNames[x[0]]
    except KeyError:
      loggingLevelString = "Level[%s]" % str(x[0])
    print >>sys.stderr, loggingLevelString, x[1] % x[2:]
  def debug(self,*x): self.log(logging.DEBUG, *x)
  def info(self,*x): self.log(logging.INFO, *x)
  def warning(self,*x): self.log(logging.WARNING, *x)
  def error(self,*x): self.log(logging.ERROR, *x)
  def critical(self,*x): self.log(logging.CRITICAL, *x)

#=================================================================================================================
class SilentFakeLogger(object):
  def log(self,*x): pass
  def debug(self,*x): pass
  def info(self,*x): pass
  def warning(self,*x): pass
  def error(self,*x): pass
  def critical(self,*x): pass

#=================================================================================================================
# logging routines
#-----------------------------------------------------------------------------------------------------------------

loggingReportLock = threading.RLock()

#-----------------------------------------------------------------------------------------------------------------
def reportExceptionAndContinue(logger=FakeLogger(), loggingLevel=logging.ERROR, ignoreFunction=None, showTraceback=True):
  try:
    exceptionType, exception, tracebackInfo = sys.exc_info()
    if ignoreFunction and ignoreFunction(exceptionType, exception, tracebackInfo):
      return
    if exceptionType in (KeyboardInterrupt, SystemExit):
      raise  exception
    loggingReportLock.acquire()   #make sure these multiple log entries stay together
    try:
      logger.log(loggingLevel, "%s Caught Error: %s", threading.currentThread().getName(), exceptionType)
      logger.log(loggingLevel, exception)
      if showTraceback:
        stringStream = cStringIO.StringIO()
        try:
          print >>stringStream,  "trace back follows:"
          traceback.print_tb(tracebackInfo, None, stringStream)
          tracebackString = stringStream.getvalue()
          logger.info(tracebackString)
        finally:
          stringStream.close()
    finally:
      loggingReportLock.release()
  except Exception, x:
    print x

#-----------------------------------------------------------------------------------------------------------------
def reportExceptionAndAbort(logger, showTraceback=True):
  reportExceptionAndContinue(logger, logging.CRITICAL, showTraceback=showTraceback)
  logger.critical("cannot continue - quitting")
  raise SystemExit

#=================================================================================================================
# utilities
#-----------------------------------------------------------------------------------------------------------------
def emptyFilter(x):
  return (x, None)[x==""]

#-----------------------------------------------------------------------------------------------------------------
def limitStringOrNone(aString, maxLength):
  try:
    return aString[:maxLength]
  except TypeError:
    return None

#-----------------------------------------------------------------------------------------------------------------
def lookupLimitedStringOrNone(aDict, aKey, maxLength):
  try:
    return limitStringOrNone(aDict[aKey], maxLength)
  except KeyError:
    return None


#=================================================================================================================
class CachingIterator(object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, anIterator):
    self.theIterator = anIterator
    self.cache = []
    self.secondaryLimitedSizeCache = collections.deque()
    self.secondaryCacheMaximumSize = 11
    self.secondaryCacheSize = 0
    self.useSecondary = False
  #-----------------------------------------------------------------------------------------------------------------
  def __iter__(self):
    #try:  #to be used in Python 2.5 or greater
      for x in self.theIterator:
        if self.useSecondary:
          if self.secondaryCacheSize == self.secondaryCacheMaximumSize:
            self.secondaryLimitedSizeCache.popleft()
            self.secondaryLimitedSizeCache.append(x)
          else:
            self.secondaryLimitedSizeCache.append(x)
            self.secondaryCacheSize += 1
        else:
          self.cache.append(x)
        yield x
    #finally:
    #  self.stopUsingSecondaryCache()
  #-----------------------------------------------------------------------------------------------------------------
  def useSecondaryCache(self):
    self.useSecondary = True
  #-----------------------------------------------------------------------------------------------------------------
  def stopUsingSecondaryCache(self):
    self.useSecondary = False
    self.cache.extend(self.secondaryLimitedSizeCache)
    self.secondaryCacheSize = 0
    self.secondaryLimitedSizeCache = collections.deque()

#-----------------------------------------------------------------------------------------------------------------
import signal
# Don't know why this isn't available by importing signal, but not.
signalNameFromNumberMap = dict( ( (eval('signal.%s'%x),x) for x in dir(signal) if (x.startswith('SIG') and not x.startswith('SIG_')) ) )
