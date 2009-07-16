#! /usr/bin/env python
"""
Just set up the database and exit. Assume we can get config details from the test config file, but allow sys.argv to override
"""
import datetime
import psycopg2
import logging
import sys
import socorro.lib.ConfigurationManager as configurationManager

import socorro.cron.mtbf as mtbf
import socorro.cron.topcrasher as topcrasher
import socorro.cron.topcrashbyurl as topcrashbyurl

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
  logger = logging.getLogger("fillDB")
  logger.setLevel(logging.WARNING)
  fileLog = logging.FileHandler('./fillDB.log')
  fileLog.setLevel(logging.WARNING)
  fileLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
  fileLog.setFormatter(fileLogFormatter)
  logger.addHandler(fileLog)
  topcrasher.logger.addHandler(fileLog)
  topcrashbyurl.logger.addHandler(fileLog)
  
  addedConfigOptions = [
    ('h','help',False,None,'print this list',None),
    ('P','product-os-count',True,12,'how many product/os pairs to use [1-56]',lambda x: rangeChecker(1,56,x) ),
    ('S','signature-count',True,83,'how many signatures to use [1-97]',lambda x: rangeChecker(1,97,x)),
    ('R','repeat-count',True,2,'how many times to loop [smallish N]',None),
    ('m','mtbf-fill',False,True,'Fill the time_before_failure table',lambda x: True),
    ('u','url-fill',False,True,'Fill the top_crashes_by_url table',lambda x: True),
    ('s','sig-fill',False,True,'Fill the top_crashes_by_signature table',lambda x: True),
    ('a','all-fill',False,True,'Fill all three matrialized view tables',[('mtbf-fill',None),('url-fill',None),('sig-fill',None)]),
    ]
  config = configurationManager.newConfiguration(configurationModule = commonConfig, applicationName='fillSchema.py',configurationOptionsList = addedConfigOptions)

  connection = psycopg2.connect("host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s"%config)
  cursor = connection.cursor()
  testDB = TestDB()
  # Now do the work in several steps
  print "Creating the database tables..."
  testDB.removeDB(config,logger)
  testDB.createDB(config,logger)
  print "populating the dimensions tables..."
  processingDays,ignore = dbtestutil.fillMtbfTables(cursor,limit=int(config.get('product-os-count')))
  startDays = [x[0] for x in processingDays]
  print "populating the reports table (takes a few seconds)..."
  dbtestutil.fillReportsTable(cursor,createUrls=True,doFillMtbfTables=False, multiplier=int(config.get('repeat-count')),signatureCount=int(config.get('signature-count')))
  connection.commit()
  extras = []
  print "All done populating the 'raw' data"
  if config.get('mtbf-fill'):
    print "Filling the time_before_failure table..."
    starter = None
    ender = None
    for startDay in startDays:
      if not starter: starter = startDay
      ender = startDay
      mtbf.calculateMtbf(config,logger,processingDay=startDay)
    extras.append(" - Time before fail: for days in %s through %s"%(starter,ender))
  if config.get('sig-fill'):
    print "Filling the top_crashes_by_signature table (takes almost a minute)..."
    tc = topcrasher.TopCrashBySignature(config)
    tc.processIntervals(startDate=startDays[0],endDate = startDays[-1])
    extras.append(" - Top crash by sig: for days in %s through %s"%(startDays[0],startDays[-1]))
  if config.get('url-fill'):
    print "Filling the top_crashes_by_url table (takes about 20 seconds)..."
    tu = topcrashbyurl.TopCrashesByUrl(config)
    tu.processIntervals(windowStart=startDays[0],windowEnd=startDays[-1])
    extras.append(" - Top crash by url: for days in %s through %s"%(startDays[0],startDays[-1]))
  print "DONE populating the database tables"
  if extras:
    print "\n".join(extras)

if __name__ == '__main__':
  main(
)
