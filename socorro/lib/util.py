import sys
import traceback
import datetime
import cStringIO
import threading

import logging

aLock = threading.RLock()

def report(message):
  aLock.acquire()  #make sure these multiple log entries stay together
  try:  
    logger.info("*** thread %s ***", threading.currentThread().getName())
    logger.info(message)
  finally:
    aLock.release()  

def reportExceptionAndContinue(logger, loggingLevel=logging.ERROR, ignoreFunction=None):
  try:
    exceptionType, exception, tracebackInfo = sys.exc_info()
    if ignoreFunction and ignoreFunction(exceptionType, exception, tracebackInfo):
      return
    if exceptionType in (KeyboardInterrupt, SystemExit):
      raise  exception
    aLock.acquire()   #make sure these multiple log entries stay together
    try:
      logger.log(loggingLevel, "%s Caught Error: %s", threading.currentThread().getName(), exceptionType)
      logger.log(loggingLevel, exception)
      stringStream = cStringIO.StringIO()
      try:
        print >>stringStream,  "trace back follows:"
        traceback.print_tb(tracebackInfo, None, stringStream)
        tracebackString = stringStream.getvalue()
        logger.info(tracebackString)
      finally:
        stringStream.close()
    finally:
      aLock.release()
  except Exception, x:
    print x


def reportExceptionAndAbort(logger):
  reportExceptionAndContinue(logger, logging.CRITICAL)
  logger.critical("cannot continue - quitting")
  raise SystemExit
  
def emptyFilter(x):
  return (x, None)[x==""]

def limitStringOrNone(aString, maxLength):
  try:
    return aString[:maxLength]
  except TypeError:
    return None
  
def lookupLimitedStringOrNone(aDict, aKey, maxLength):
  try:
    return limitStringOrNone(aDict[aKey], maxLength)
  except KeyError:
    return None

import collections

class CachingIterator(object):
  def __init__(self, anIterator):
    self.theIterator = anIterator
    self.cache = []
    self.secondaryLimitedSizeCache = collections.deque()
    self.secondaryCacheMaximumSize = 11
    self.secondaryCacheSize = 0
    self.useSecondary = False
    
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
      
  def useSecondaryCache(self):
    self.useSecondary = True
    
  def stopUsingSecondaryCache(self):
    self.useSecondary = False
    self.cache.extend(self.secondaryLimitedSizeCache)
    self.secondaryCacheSize = 0
    self.secondaryLimitedSizeCache = collections.deque()


  

    