import socorro.lib.config as config

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

class CachingIterator(object):
  def __init__(self, anIterator):
    self.theIterator = anIterator
    self.cache = []
    
  def __iter__(self):
    for x in self.theIterator:
      self.cache.append(x)
      yield x



  

    