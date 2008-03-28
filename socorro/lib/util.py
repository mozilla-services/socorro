import socorro.lib.config as config

import sys
import traceback
import datetime

import threading

aLock = threading.RLock()

def report(message):
  aLock.acquire()
  try:  
    print >>config.statusReportStream, "*** thread %s ***" % threading.currentThread().getName()
    print >>config.statusReportStream, message
  finally:
    aLock.release()  

def reportExceptionAndContinue(ignoreFunction=None):
  try:
    exceptionType, exception, tracebackInfo = sys.exc_info()
    if ignoreFunction and ignoreFunction(exceptionType, exception, tracebackInfo):
      return
    if exceptionType in (KeyboardInterrupt, SystemExit):
      raise  exception
    aLock.acquire()
    try:
      print >>config.errorReportStream, "*** thread %s ***" % threading.currentThread().getName()
      print >>config.errorReportStream,  "%s Caught Error: %s" %  (datetime.datetime.now(), exceptionType)
      print  >>config.errorReportStream, "%s%s" % (' '*27, exception)
      traceback.print_tb(tracebackInfo, None, config.errorReportStream)
    finally:
      aLock.release()
  except Exception, x:
    print x


def reportExceptionAndAbort():
  reportExceptionAndContinue()
  sys.exit(-1)
  
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
