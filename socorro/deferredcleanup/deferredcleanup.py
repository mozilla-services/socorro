#!/usr/bin/python

import re

try:
  from collections import defaultdict
except ImportError:
  class defaultdict(dict):
    def __init__(self, default_factory=None, *a, **kw):
      if (default_factory is not None and
        not hasattr(default_factory, '__call__')):
        raise TypeError('first argument must be callable')
      dict.__init__(self, *a, **kw)
      self.default_factory = default_factory
    def __getitem__(self, key):
      try:
        return dict.__getitem__(self, key)
      except KeyError:
        return self.__missing__(key)
    def __missing__(self, key):
      if self.default_factory is None:
        raise KeyError(key)
      self[key] = value = self.default_factory()
      return value

import datetime
import sys
import threading
import os.path
import logging
import logging.handlers
import socorro.lib.util
import socorro.lib.filesystem


deferredDailyIndexDateDirectoryRe = re.compile(r'\d\d\d\d\d\d\d\d$')

def isDeferredDailyIndexDirectory(fileTuple):
  if deferredDailyIndexDateDirectoryRe.match(fileTuple[1]):
    return True
  return False

oneDayTimeDelta = datetime.timedelta(days=1)
def isLastDayOfMonth (year, month, day):
  aDate = datetime.date(int(year), int(month), int(day))
  nextDate = aDate + oneDayTimeDelta
  return aDate.month != nextDate.month

def deferredJobStorageCleanup (config, logger):
  """ the deferredJob storage directories have two branches:
        type 1 - the dump directories of the form .../YYYY/M/D/H/bp_mm
        type 2 - the index directories of the form .../index/webheadName/YYYYMMDD
  """
  try:
    logger.info("%s - beginning deferredJobCleanup", threading.currentThread().getName())
    directoryInventory = defaultdict(list)
    # find all the type 1 and type 2 directories, descending no deeper
    for path, name, pathname in socorro.lib.filesystem.findFileGenerator(os.path.join(config.deferredStorageRoot, "index"), isDeferredDailyIndexDirectory, lambda x: not isDeferredDailyIndexDirectory(x)):
      logger.info("%s - found deferred day: %s", threading.currentThread().getName(), pathname)
      directoryInventory[name].append(pathname) # add the type 2 directory
    orderedListOfDaysInDeferredStorage = directoryInventory.keys()
    orderedListOfDaysInDeferredStorage.sort()
    #kill all older than maximumDeferredJobAge
    for aDay in orderedListOfDaysInDeferredStorage[:-config.maximumDeferredJobAge]:
      year = aDay[:4]
      month = aDay[4:6]
      if month[0] == '0':
        month = month[-1]
      day = aDay[-2:]
      if day[0] == '0':
        day = day[-1]
      directoryInventory[aDay].append(os.path.join(config.deferredStorageRoot, year, month, day)) # add the type 1 day directory
      if isLastDayOfMonth(year, month, day):
        directoryInventory[aDay].append(os.path.join(config.deferredStorageRoot, year, month)) # add the type 1 month directory
      if month == '12' and day == '31':
        directoryInventory[aDay].append(os.path.join(config.deferredStorageRoot, year)) # add the type 1 year directory
      for aPathName in directoryInventory[aDay]:
        logger.info("%s - deleting: %s", threading.currentThread().getName(), aPathName)
        shutil.rmtree(aPathName)
  except (KeyboardInterrupt, SystemExit):
    logger.debug("%s - got quit message", threading.currentThread().getName())
  except:
    socorro.lib.util.reportExceptionAndContinue(logger)
  logger.info("%s - deferredJobCleanupLoop done.", threading.currentThread().getName())

def main():
  import socorro.deferredcleanup.config as config
  import socorro.lib.ConfigurationManager as configurationManager

  try:
    configurationContext = configurationManager.newConfiguration(configurationModule=config, applicationName="Socorro Deferred Storage Cleanup 1.0")
  except configurationManager.NotAnOptionError, x:
    print >>sys.stderr, x
    print >>sys.stderr, "for usage, try --help"
    sys.exit()

  logger = logging.getLogger("deferred_storage_cleanup")
  logger.setLevel(logging.DEBUG)

  stderrLog = logging.StreamHandler()
  stderrLog.setLevel(configurationContext.stderrErrorLoggingLevel)
  stderrLogFormatter = logging.Formatter(configurationContext.stderrLineFormatString)
  stderrLog.setFormatter(stderrLogFormatter)
  logger.addHandler(stderrLog)

  rotatingFileLog = logging.handlers.RotatingFileHandler(configurationContext.logFilePathname, "a", configurationContext.logFileMaximumSize, configurationContext.logFileMaximumBackupHistory)
  rotatingFileLog.setLevel(configurationContext.logFileErrorLoggingLevel)
  rotatingFileLogFormatter = logging.Formatter(configurationContext.logFileLineFormatString)
  rotatingFileLog.setFormatter(rotatingFileLogFormatter)
  logger.addHandler(rotatingFileLog)

  logger.info("current configuration\n%s", str(configurationContext))

  try:
    deferredJobStorageCleanup(configurationContext, logger)
  finally:
    logger.info("done.")
    rotatingFileLog.flush()
    rotatingFileLog.close()

if __name__ == "__main__":
  main()

