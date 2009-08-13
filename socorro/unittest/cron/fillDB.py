#! /usr/bin/env python
"""
Just set up the database and exit. Assume we can get config details from the test config file, but allow sys.argv to override
"""
import datetime
import logging
import os
import psycopg2
import sys

import socorro.lib.ConfigurationManager as configurationManager
import socorro.database.cachedIdAccess as socorro_cia
import socorro.cron.mtbf as mtbf
import socorro.cron.topCrashesBySignature as topcrasher
import socorro.cron.topCrashesByUrl as topcrashbyurl

from socorro.unittest.testlib.testDB import TestDB
import socorro.unittest.testlib.dbtestutil as dbtestutil
import socorro.unittest.config.commonconfig as commonConfig

def rangeChecker(lower,upper,item):
  if int(item) < int(lower):
    raise IndexError("Item %s < minimum allowed: %s"%(item,lower))
  if int(item) > int(upper):
    raise IndexError("Item %s > maximum allowed: %s"%(item,upper))
  return item

def main():
  addedConfigOptions = [
    ('h','help',False,None,'print this list',None),
    ('P','product-os-count',True,12,'how many product/os pairs to use [1-56]',lambda x: rangeChecker(1,56,x) ),
    ('S','signature-count',True,83,'how many signatures to use [1-121]',lambda x: rangeChecker(1,121,x)),
    ('R','repeat-count',True,2,'how many times to loop [smallish N]',None),
    ('m','mtbf-fill',False,True,'Fill the time_before_failure table',lambda x: True),
    ('u','url-fill',False,True,'Fill the top_crashes_by_url table',lambda x: True),
    ('s','sig-fill',False,True,'Fill the top_crashes_by_signature table',lambda x: True),
    ('a','all-fill',False,True,'Fill all three matrialized view tables',[('mtbf-fill',None),('url-fill',None),('sig-fill',None)]),
    ('D','drop-all',False,True,'Drop all the database tables. Do no other work',lambda x: True),
    (None,'logFileErrorLoggingLevel',True,logging.WARNING,'logging level for the log file (10 - DEBUG, 20 - INFO, 30 - WARNING, 40 - ERROR, 50 - CRITICAL)',None),
    ]
  config = configurationManager.newConfiguration(configurationModule = commonConfig, applicationName='fillSchema.py',configurationOptionsList = addedConfigOptions)

  myDir = os.path.split(__file__)[0]
  logDir = os.path.join(myDir,'logs')
  logFile = os.path.join(logDir,'fillDB.log')
  try:
    os.makedirs(logDir)
  except OSError:
    pass
  logger = logging.getLogger("fillDB")
  fileLog = logging.FileHandler(logFile)
  fileLog.setLevel(int(config.logFileErrorLoggingLevel))
  fileLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
  fileLog.setFormatter(fileLogFormatter)

  # now add the handler for all the logs of interest
  logger.addHandler(fileLog)
  logger.setLevel(int(config.logFileErrorLoggingLevel))
  socorro_cia.logger.addHandler(fileLog)
  socorro_cia.logger.setLevel(int(config.logFileErrorLoggingLevel))
  topcrasher.logger.addHandler(fileLog)
  topcrasher.logger.setLevel(int(config.logFileErrorLoggingLevel))
  topcrashbyurl.logger.addHandler(fileLog)
  topcrashbyurl.logger.setLevel(int(config.logFileErrorLoggingLevel))
  
  logger.info("Config is\n%s",str(config))
    
  createData(config,logger)

def createData(config,logger):
  # Now do the work in several steps
  connection = psycopg2.connect("host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s"%config)
  cursor = connection.cursor()
  testDB = TestDB()
  try:
    testDB.removeDB(config,logger)
    if config.get('drop-all'):
      print "Dropped the database tables ..."
      return
    print "Creating the database tables..."
    testDB.createDB(config,logger)
    print "populating the dimensions tables..."
    processingDays,ignore = dbtestutil.fillMtbfTables(cursor,limit=int(config.get('product-os-count')))
    startDays = [x[0] for x in processingDays]
    multiplier = int(config.get('repeat-count'))
    print "populating the reports table (takes about %d seconds)..."%(int(1.7+1.2*multiplier))
    dbtestutil.fillReportsTable(cursor,createUrls=True,doFillMtbfTables=False, numUrls=100, multiplier=multiplier,signatureCount=int(config.get('signature-count')))
    connection.commit()
    extras = []
    print "All done populating the 'raw' data"
    if config.get('mtbf-fill'):
      blurb = ""
      cost = 0.20 + multiplier*0.15
      if cost > 1.0:
        blurb = ("(takes about %2.1f seconds)"%cost)
      print "Filling the time_before_failure table %s..."%blurb # R=1: .35 seconds; 2:0.49s; 3:.064s; 4:.9 ## = .20 + R*.15
      starter = None
      ender = None
      for startDay in startDays:
        if not starter: starter = startDay
        ender = startDay
        mtbf.processOneMtbfWindow(config,logger,processingDay=startDay)
      extras.append(" - Time before fail: for days in %s through %s"%(starter,ender))
    if config.get('sig-fill'):
      print "Filling the top_crashes_by_signature table (takes about %s seconds)..."%(20+11*multiplier) # R=1: 27.3 secs; 2:38.5s; 3=48.3 ##  = 20 +R*11
      tc = topcrasher.TopCrashBySignature(config)
      tc.processIntervals(startDate=startDays[0],endDate = startDays[-1])
      extras.append(" - Top crash by sig: for days in %s through %s"%(startDays[0],startDays[-1]))
    if config.get('url-fill'):
      print "Filling the top_crashes_by_url table (takes about %s seconds)..."%(4+multiplier*2) # R=1: 4 secs; 2: 5s, 3: 7.6 ## = 4+R*2
      logger.info("Filling the top_crashes_by_url table (takes about %s seconds)..."%(4+multiplier*2))
      tu = topcrashbyurl.TopCrashesByUrl(config)
      tu.processCrashesByUrlWindows(startDate=startDays[0],endDate = startDays[-1])
      extras.append(" - Top crash by url: for days in %s through %s"%(startDays[0],startDays[-1]))
    print "DONE populating the database tables"
    if extras:
      print "\n".join(extras)
  finally:
    logger.info("All done. Closing connection")
    connection.close()
    
if __name__ == '__main__':
  main()
