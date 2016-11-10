# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import sys
import traceback
import datetime
import cStringIO
import threading
import collections

import logging
l = logging.getLogger('webapi')

#=================================================================================================================
class FakeLogger(object):
  loggingLevelNames = { logging.DEBUG: "DEBUG",
                        logging.INFO: "INFO",
                        logging.WARNING: "WARNING",
                        logging.ERROR: "ERROR",
                        logging.CRITICAL: "CRITICAL",
                        logging.FATAL: "FATAL"
                      }
  def createLogMessage(self,*x):
    try:
      loggingLevelString = FakeLogger.loggingLevelNames[x[0]]
    except KeyError:
      loggingLevelString = "Level[%s]" % str(x[0])
    message = x[1] % x[2:]
    return '%s %s' % (loggingLevelString, message)
  def log(self,*x,**kwargs):
    print >>sys.stderr, self.createLogMessage(*x)
  def debug(self,*x,**kwargs): self.log(logging.DEBUG, *x)
  def info(self,*x,**kwargs): self.log(logging.INFO, *x)
  def warning(self,*x,**kwargs): self.log(logging.WARNING, *x)
  warn = warning
  def error(self,*x,**kwargs): self.log(logging.ERROR, *x)
  def critical(self,*x,**kwargs): self.log(logging.CRITICAL, *x)
  fatal = critical


#=================================================================================================================
class SilentFakeLogger(object):
  def log(self,*x,**kwargs): pass
  def debug(self,*x,**kwargs): pass
  def info(self,*x,**kwargs): pass
  def warning(self,*x,**kwargs): pass
  def error(self,*x,**kwargs): pass
  def critical(self,*x,**kwargs): pass
  def fatal(self,*x,**kwargs):pass

#=================================================================================================================
class StringLogger(FakeLogger):
  def __init__(self):
    super(StringLogger, self).__init__()
    self.messages = []
  def log(self,*x,**kwargs):
    message = self.createLogMessage(*x)
    self.messages.append(message)
  def getMessages(self):
    log = '\n'.join(self.messages)
    self.messages = []
    return log


#=================================================================================================================
# logging routines

#-----------------------------------------------------------------------------------------------------------------
def setupLoggingHandlers(logger, config):
  stderrLog = logging.StreamHandler()
  stderrLog.setLevel(config.stderrErrorLoggingLevel)
  stderrLogFormatter = logging.Formatter(config.stderrLineFormatString)
  stderrLog.setFormatter(stderrLogFormatter)
  logger.addHandler(stderrLog)

  syslog = logging.handlers.SysLogHandler(facility=config.syslogFacilityString)
  syslog.setLevel(config.syslogErrorLoggingLevel)
  syslogFormatter = logging.Formatter(config.syslogLineFormatString)
  syslog.setFormatter(syslogFormatter)
  logger.addHandler(syslog)

#-----------------------------------------------------------------------------------------------------------------
def echoConfig(logger, config):
  logger.info("current configuration:")
  for value in str(config).split('\n'):
    logger.info('%s', value)

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
      logger.log(loggingLevel, "Caught Error: %s", exceptionType)
      logger.log(loggingLevel, str(exception))
      if showTraceback:
        logger.log(loggingLevel, "trace back follows:")
        for aLine in traceback.format_exception(exceptionType, exception, tracebackInfo):
          logger.log(loggingLevel, aLine.strip())
    finally:
      loggingReportLock.release()
  except Exception, x:
    print >>sys.stderr, x

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

#-----------------------------------------------------------------------------------------------------------------
def lookupStringOrEmptyString(aDict, aKey):
  try:
    return aDict[aKey]
  except KeyError:
    return ''

#-----------------------------------------------------------------------------------------------------------------
def backoffSecondsGenerator():
  seconds = [10, 30, 60, 120, 300]
  for x in seconds:
    yield x
  while True:
    yield seconds[-1]

#=================================================================================================================
class DotDict(dict):
  __getattr__= dict.__getitem__
  __setattr__= dict.__setitem__
  __delattr__= dict.__delitem__

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
  def close(self):
    self.theIterator.close()
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

#=================================================================================================================
class StrCachingIterator(CachingIterator):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, anIterator):
    super(StrCachingIterator, self).__init__(anIterator)
  #-----------------------------------------------------------------------------------------------------------------
  def __iter__(self):
    #try:  #to be used in Python 2.5 or greater
      for x in self.theIterator:
        y = repr(x)[1:-3]  #warning expecting a '\n' on the end of every line
        if self.useSecondary:
          if self.secondaryCacheSize == self.secondaryCacheMaximumSize:
            self.secondaryLimitedSizeCache.popleft()
            self.secondaryLimitedSizeCache.append(y)
          else:
            self.secondaryLimitedSizeCache.append(y)
            self.secondaryCacheSize += 1
        else:
          self.cache.append(y)
        yield y
    #finally:
    #  self.stopUsingSecondaryCache()

#-----------------------------------------------------------------------------------------------------------------
import signal
# Don't know why this isn't available by importing signal, but not.
signalNameFromNumberMap = dict( ( (getattr(signal,x),x) for x in dir(signal) if (x.startswith('SIG') and not x.startswith('SIG_')) ) )

