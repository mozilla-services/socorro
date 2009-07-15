import copy
import datetime as dt
import errno
import logging
import os
import psycopg2
import time
import unittest
from operator import itemgetter
from nose.tools import *

import socorro.lib.ConfigurationManager as configurationManager

import socorro.cron.topcrasher as topcrasher

from   socorro.unittest.testlib.testDB import TestDB
import socorro.unittest.testlib.dbtestutil as dbtestutil
import cronTestconfig as testConfig

testBaseDate = dt.datetime(2008,1,1,1,1,1,1)
testFirstIntervalBegin = dt.datetime(2008,1,1)


class Me:
  pass
me = None

def addReportData(cursor,dataToAdd):
  sql = """INSERT INTO crash_reports
     (uuid, client_crash_date,install_age, last_crash, uptime, date_processed, user_comments, signaturedims_id, productdims_id, osdims_id, urldims_id) VALUES
     ( %(uuid)s, %(client_crash_date)s, %(install_age)s, %(last_crash)s, %(uptime)s, %(date_processed)s, %(user_comments)s, %(signaturedims_id)s, %(productdims_id)s, %(osdims_id)s, %(urldims_id)s)
    """
  cursor.executemany(sql,dataToAdd)
  
def addCrashData(cursor,dataToAdd):
  # dataToAdd is [{},...] for dictionaries of values as shown in sql below
  sql = """INSERT INTO topcrashfacts
    (  count,    rank,    uptime,    last_updated,    productdims_id,    osdims_id,    signaturedims_id) VALUES
    (%(count)s,%(rank)s,%(uptime)s,%(last_updated)s,%(productdims_id)s,%(osdims_id)s,%(signaturedims_id)s) """
  cursor.executemany(sql,dataToAdd)
  cursor.connection.commit()

dataForStartDateTest = [
  {'count':18,'rank':1,'uptime':64.5,'last_updated':dt.datetime(2009,3,3,3,3,3), 'productdims_id':1,'osdims_id':1,'signaturedims_id':1},
  {'count':10,'rank':2,'uptime':56.4,'last_updated':dt.datetime(2009,3,3,3,3,5), 'productdims_id':2,'osdims_id':1,'signaturedims_id':3},
  {'count':1, 'rank':3,'uptime':45.6,'last_updated':dt.datetime(2009,3,3,3,3,7), 'productdims_id':3,'osdims_id':2,'signaturedims_id':4},
  ]

def genOsId(cursor):
  # the test rather naively weights the osDims. 11 is a prime number that isn't 5 or 7
  osDimsData = dbtestutil.dimsData['osdims']
  assert 7 == len(osDimsData), 'So we can correctly create weightedList below'
  weightedList = [0,1,1,2,2,2,3,4,4,5,6] # len 11 is a nice prime number, different than all the others
  cursor.execute("select id from osdims order by id")
  ids = [x[0] for x in cursor.fetchall()]
  cursor.connection.commit()
  while True:
    for o in weightedList:
      yield ids[o] # the actual id column
      
def genProdId(cursor):
  productDimsData = dbtestutil.dimsData['productdims']
  assert 8 == len(productDimsData), 'So we can correctly create weightedList below'
  weightedList = [0,0,1,1,2,2,2,3,3,4,4,5,5,6,6,7,7] # len 17 is a nice prime number, different than all the others
  cursor.execute("select id from productdims order by id")
  ids = [x[0] for x in cursor.fetchall()]
  cursor.connection.commit()
  while True:
    for p in weightedList:
      yield ids[p]

def genSigId(cursor):
  cursor.execute("select id from signaturedims order by id")
  ids = [x[0] for x in cursor.fetchall()]
  cursor.connection.commit()
  assert 7 == len(ids), 'but %s: %s'%(len(ids),ids) # 7 is a nice prime number, different than all the others
  while True:
    for s in ids:
      yield s

def genUrlId(cursor):
  cursor.execute("select id from urldims order by id")
  cursor.connection.commit()
  ids = [x[0] for x in cursor.fetchall()]
  assert 13 == len(ids) # 13 is a nice prime number, different than all the others
  while True:
    for u in ids:
      yield u

def genBump(numberPerDay):
  musPerInDayBump1 = (8*60*60*1000*1000 / numberPerDay) - 10000 # the -10 milliseconds leaves a little leeway
  musPerInDayBump2 = (8*60*60*1000*1000 / numberPerDay)  - 2000 # the -2 millisecondsleaves a little leeway
  if musPerInDayBump1 < 0: millisPerInDayBump1 = 10   # but if we overflow, so be it.
  if musPerInDayBump2 < 0: millisPerInDayBump2 = 5    # but if we overflow, so be it.
  bumps = [
    dt.timedelta(microseconds=musPerInDayBump1),
    dt.timedelta(microseconds=0),
    dt.timedelta(microseconds=musPerInDayBump2),
    dt.timedelta(microseconds=0),
    ]
  while True:
    for bump in bumps:
      yield bump

def genBuild():
  builds = [('200712312355',dt.datetime(2007,12,31,23,55)),('200712302355',dt.datetime(2007,12,30,23,55)),('200712292355',dt.datetime(2007,12,29,23,55)),]
  while True:
    for b in builds:
      yield b

def makeReportData(sizePerDay,numDays, cursor):
  idGen = dbtestutil.moreUuid()
  osGen = genOsId(cursor)
  prodGen = genProdId(cursor)
  sigGen = genSigId(cursor)
  urlGen = genUrlId(cursor)
  bumpGen = genBump(sizePerDay)
  buildGen = genBuild()
  baseDate = testBaseDate
  procOffset = dt.timedelta(days=1,milliseconds=1903)
  insData = []
  for dummyDays in range(numDays):
    currentDate = baseDate
    count = 0
    while count < sizePerDay:
      data = {
        'uuid':idGen.next(),
        'client_crash_date':currentDate,
        'install_age':1100,
        'last_crash':0,
        'uptime':1000,
        'date_processed': currentDate+procOffset,
        'user_comments': 'oh help',
        'app_notes':"",
        'signaturedims_id':sigGen.next(),
        'productdims_id':prodGen.next(),
        'osdims_id':osGen.next(),
        'urldims_id':urlGen.next(),
        }
      insData.append(data)
      currentDate += bumpGen.next()
      count += 1
    baseDate = baseDate+dt.timedelta(days=1)
  #print "client_crash_date          | date_processed             | uptm | uuid                                 | inst |  u, o, p, s"
  #for j in insData:
  #  print "%(client_crash_date)s | %(date_processed)s | %(uptime)s | %(uuid)s | %(install_age)s | %(urldims_id)2s,%(osdims_id)2s,%(productdims_id)2s,%(signaturedims_id)2s"%j
  return insData

def createMe():
  global me
  if not me:
    me = Me()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName = "Testing TopCrashers")
  topcrasher.logger.setLevel(logging.DEBUG)
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass
  me.logFilePathname = me.config.logFilePathname
  logfileDir = os.path.split(me.config.logFilePathname)[0]
  try:
    os.makedirs(logfileDir)
  except OSError,x:
    if errno.EEXIST != x.errno: raise
  f = open(me.config.logFilePathname,'w')
  f.close()

  fileLog = logging.FileHandler(me.logFilePathname, 'a')
  fileLog.setLevel(logging.DEBUG)
  fileLogFormatter = logging.Formatter(me.config.get('logFileLineFormatString','%(asctime)s %(levelname)s - %(message)s'))
  fileLog.setFormatter(fileLogFormatter)
  topcrasher.logger.addHandler(fileLog)
  me.logger = topcrasher.logger
  me.dsn = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % (me.config)

class TestTopCrashers(unittest.TestCase):
  def setUp(self):
    global me
    if not me:
      createMe()
    self.connection = psycopg2.connect(me.dsn)
    self.testDB = TestDB()
    self.testDB.removeDB(me.config, me.logger)
    self.testDB.createDB(me.config, me.logger)
    dbtestutil.fillDimsTables(self.connection.cursor())
    self.connection.commit()

  def tearDown(self):
    global me
    self.testDB.removeDB(me.config,me.logger)
    self.connection.close()
    
  def prepareConfigForPeriod(self,idkeys,startDate,endDate):
   """enter a row for each idkey, start and end date. Do it repeatedly if you need different ones"""
   cfgdata = [[x[0],x[1],startDate,endDate] for x in idkeys]
   sql = "INSERT INTO tcbysignatureconfig (productdims_id,osdims_id,start_dt,end_dt) VALUES (%s,%s,%s,%s)"
   self.connection.cursor().executemany(sql,cfgdata)
   self.connection.commit()

  def prepareExtractDataForPeriod(self, columnName, sizePerDay=2, numDays=5):
    """Put some crash data into reports table, return their extrema for the columnName specified"""
    global me
    cursor = self.connection.cursor()
    data = makeReportData(sizePerDay,numDays,cursor)
    self.connection.commit()
    # find the actual min and max dates
    minStamp = dt.datetime(2100,11,11)
    maxStamp = dt.datetime(1900,11,11)
    for d in data:
      ds = d[columnName]
      if ds < minStamp: minStamp = ds
      if ds > maxStamp: maxStamp = ds
    addReportData(cursor,data)
    self.connection.commit()
    return minStamp,maxStamp,data
    
  def testConstructor(self):
    global me
    for reqd in ["databaseHost","databaseName","databaseUserName","databasePassword",]:
      cc = copy.copy(me.config)
      del(cc[reqd])
      assert_raises(SystemExit,topcrasher.TopCrasher,cc)
    bogusMap = {'databaseHost':me.config.databaseHost,'databaseName':me.config.databaseName,'databaseUserName':'JoeLuser','databasePassword':me.config.databasePassword}
    assert_raises(SystemExit,topcrasher.TopCrasher,bogusMap)

    #check without a specified processingInterval, initialIntervalDays, startDate or endDate
    now = dt.datetime.now()
    tc = topcrasher.TopCrasher(me.config)
    expectedStart = now.replace(hour=0,minute=0,second=0,microsecond=0) - dt.timedelta(days=tc.initialIntervalDays)
    expectedEnd = now.replace(hour=0,minute=0,second=0,microsecond=0)
    mark = now - tc.processingIntervalDelta
    while expectedEnd < mark:
      expectedEnd += tc.processingIntervalDelta
    after = now
    assert expectedStart == tc.startDate
    assert expectedEnd == tc.endDate and tc.endDate <= now, 'But NOT %s == %s <= %s'%(expectedEnd,tc.endDate,now)
    # Check for defaults. If the defaults are hard-code changed, this block needs equivalent changes
    assert 12 == tc.processingInterval
    assert 4 == tc.initialIntervalDays
    assert 512 == tc.dbFetchChunkSize
    assert 'date_processed' == tc.dateColumnName
    # end Check for defaults

    # check with some illegal and some legal processingIntervals
    config = copy.copy(me.config)
    for ipi in [-3,7]:
      config['processingInterval'] = ipi
      try:
        tc = topcrasher.TopCrasher(config)
        raise Exception, "Can't assert here, because we expect to catch AssertionError in next line"
      except AssertionError,x:
        pass
      except:
        assert False,'Expected AssertionError with processingInterval %s'%ipi
    for pi in [0,1,12,720]:
      config['processingInterval'] = pi
      try:
        tc = topcrasher.TopCrasher(config)
        assert tc.processingInterval==pi or (0==pi and tc.processingInterval == 12) , 'but pi=%s and got %s'%(pi,tc.processingInterval)
      except:
        assert False,'Expected success with processingInterval %s'%pi

    # check with illegal startDates
    config = copy.copy(me.config)
    config['startDate'] = dt.datetime(2009,01,01,0,0,1)
    assert_raises(AssertionError,topcrasher.TopCrasher,config)
    config['startDate'] = dt.datetime(2009,01,01,0,12,1)
    assert_raises(AssertionError,topcrasher.TopCrasher,config)
    config['startDate'] = dt.datetime(2009,01,01,2,11)
    assert_raises(AssertionError,topcrasher.TopCrasher,config)
    config['startDate'] = dt.datetime(2009,01,01,23,59)
    assert_raises(AssertionError,topcrasher.TopCrasher,config)

    # check with midnight startDate
    config = copy.copy(me.config)
    config['startDate'] = dt.datetime(2009,01,01)
    tc = topcrasher.TopCrasher(config)
    assert config['startDate'] == tc.startDate

    # check with very late legal startDate
    config['startDate'] = dt.datetime(2009,01,01,23,48)
    tc = topcrasher.TopCrasher(config)
    assert config['startDate'] == tc.startDate
    
    # check with a specified processingInterval, initialIntervalDays, startDate and endDate
    config = copy.copy(me.config)
    config['processingInterval'] = 20
    config['startDate']= specifiedStartDate = dt.datetime(2009,01,01,12,20)
    config['endDate'] = specifiedEndDate =    dt.datetime(2009,01,01,12,59)
    config['initialIntervalDays'] = 3
    tc = topcrasher.TopCrasher(config)
    assert specifiedStartDate == tc.startDate
    assert 3 == tc.initialIntervalDays
    assert 20 == tc.processingInterval
    expectedEndDate = specifiedEndDate.replace(hour=0,minute=0,second=0,microsecond=0)
    while expectedEndDate < specifiedEndDate - tc.processingIntervalDelta:
      expectedEndDate += tc.processingIntervalDelta
    assert expectedEndDate == tc.endDate, "%s:%s"%(expectedEndDate,tc.endDate)

  def testGetStartDate(self):
    cursor = self.connection.cursor()
    tc = topcrasher.TopCrasher(me.config)
    midNow = dt.datetime.now().replace(hour=0,minute=0,second=0,microsecond=0)
    expectedDefault = midNow - dt.timedelta(days=tc.initialIntervalDays)
    tryDate = dt.datetime(2009,3,4,5,24,0,39)
    expectedTry = tryDate.replace(microsecond=0)
    assert expectedDefault==tc.getStartDate(), "Expected %s, got %s"%(expectedDefault,tc.getStartDate())
    assert expectedTry == tc.getStartDate(tryDate), "Expected %s, got %s"%(expectedTry,tc.getStartDate(tryDate))
    dbTryDate = dt.datetime(2009,1,2,12,12)
    dbExpectDate = dbTryDate + dt.timedelta(seconds=60*12)
    cursor.execute("""INSERT INTO topcrashfacts
                      (productdims_id,osdims_id,signaturedims_id,interval_start,interval_minutes)
               VALUES (1,1,1,%s,12)""",(dbTryDate,))
    self.connection.commit()
    # need new TopCrash since it reads the db on construction
    tc = topcrasher.TopCrasher(me.config)
    cursor.execute("SELECT interval_start,interval_minutes from topcrashfacts order by interval_start DESC LIMIT 1")
    self.connection.commit()
    assert dbExpectDate==tc.getStartDate(),"But %s != %s"%(dbExpectDate,tc.getStartDate())
    result = tc.getStartDate(tryDate)
    assert expectedTry == tc.getStartDate(tryDate),"But %s != %s"%(expectedTry,tc.getStartDate(tryDate))

  def testGetEndDate(self):
    now = dt.datetime.now()
    tc = topcrasher.TopCrasher(me.config)
    assert tc.endDate == tc.getEndDate()
    assert now - tc.processingIntervalDelta <= tc.endDate and tc.endDate <= now
    tneg = tc.startDate - dt.timedelta(microseconds=1)
    assert tc.startDate == tc.getEndDate(tneg)
    startDate = tc.getStartDate(dt.datetime(2009,1,2,3,12))
    tc.startDate = startDate
    tryDate = expectedEndDate = dt.datetime(2009,1,2,3,48)
    endDate = tc.getEndDate(tryDate)
    assert expectedEndDate == endDate, 'Got %s != %s'%(expectedEndDate,endDate)
    minusEps = tryDate - dt.timedelta(microseconds=1)
    endDate = tc.getEndDate(minusEps)
    assert expectedEndDate -tc.processingIntervalDelta == endDate, 'Got %s != %s'%(expectedEndDate -tc.processingIntervalDelta,endDate)
    plusEps = tryDate + dt.timedelta(microseconds=1)
    endDate = tc.getEndDate(plusEps)
    assert expectedEndDate == endDate, 'Got %s != %s'%(expectedEndDate,endDate)
    endDate = tc.getEndDate(dt.datetime(2009,1,2,3,52))
    assert expectedEndDate == endDate, 'Got %s != %s'%(expectedEndDate,endDate)
    #try with explicit startDate
    sDate = dt.datetime(2007,12,25,12,24)
    eDate = dt.datetime(2007,12,25,12,23,55)
    tc.setProcessingInterval(12)
    gotDate = tc.getEndDate(endDate=eDate, startDate=sDate)
    assert sDate == gotDate, "expected %s, got %s"%(sDate,gotDate)
    eDate = dt.datetime(2007,12,25,12,24,5)
    gotDate = tc.getEndDate(endDate=eDate, startDate=sDate)
    assert sDate == gotDate, "expected %s, got %s"%(sDate,gotDate)
    eDate = dt.datetime(2007,12,25,12,37)
    expectDate = dt.datetime(2007,12,25,12,36)
    gotDate = tc.getEndDate(endDate=eDate, startDate=sDate)
    assert expectDate == gotDate, "expected %s, got %s"%(sDate,gotDate)

  def testGetLegalProcessingInterval(self):
    cursor = self.connection.cursor()
    tc = topcrasher.TopCrasher(me.config)
    illegals = [-3.0,-0.0000001,0.0000001,0.999999,11,13,14,17,19,21,22,23,123]
    for ipi in illegals:
      try:
        tc.getLegalProcessingInterval(ipi)
        raise Exception, "Can't assert here because next line catches assertionError"
      except AssertionError,x:
        pass
      except:
        assert False, "Expected assertion error trying a processingInterval of %s"%ipi
    legals = [0,1,2.0,3,4,5,6,8,9,10,12,15,16,18,20,24,30,32,36,40,45,48,240,360,720]
    for pi in legals:
      try:
        ans = tc.getLegalProcessingInterval(pi)
        assert ans==pi or (0==pi and ans == 12) , 'but pi=%s and got %s'%(pi,ans)
      except:
        pass
    cursor.execute("""INSERT INTO topcrashfacts
                      (productdims_id,osdims_id,signaturedims_id,interval_start,interval_minutes)
               VALUES (1,1,1,'2009-1-2 3:00',90)""")
    self.connection.commit()
    tc = topcrasher.TopCrasher(me.config)
    assert 90 == tc.getLegalProcessingInterval(), 'but got %s'%(tc.getLegalProcessingInterval())

  def testExtractDataForPeriod_ByDateProcessed(self):
    """
    testExtractDataForPeriod_ByDateProcessed(self):
     - Check that we get nothing for a period outside our data
     - Check that we get expected count for period inside our data
     - Check that we get half-open interval (don't get data exactly at last moment)
     - Check that we get all for period that surrounds our data
     - Check that we get nothing for start == end
     - Check that we get one moment for end = start+microsecond
     - Check that we raise ValueError for period with dates reversed
    """
    global me
    minStamp,maxStamp,data = self.prepareExtractDataForPeriod('date_processed')
    keySet = set([(d['productdims_id'],d['osdims_id']) for d in data])
    mminStamp = minStamp - dt.timedelta(days=1)
    mmaxStamp = maxStamp + dt.timedelta(days=1)
    self.prepareConfigForPeriod(keySet,mminStamp,mmaxStamp)

    tc = topcrasher.TopCrasher(me.config)
    tc.dateColumnName = 'date_processed'

    # we should get nothing if we are outside our data
    start = minStamp - dt.timedelta(days=10)
    end = start + dt.timedelta(days=1)
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    assert {} == crashData,'Expected {}, got %s'%crashData

    # We should get exactly one day's worth
    start = minStamp
    end = start + dt.timedelta(days=1)
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount = 0
    allCrashDataCount = 0
    allCrashDataCount0 = 0
    allCrashDataCount1 = 0
    for k,d in crashData.items():
      if (None,None) == k[:2]:
        allCrashDataCount += d['count']
      elif(None) == k[0]:
        allCrashDataCount0 += d['count']
      elif(None) == k[1]:
        allCrashDataCount1 += d['count']
      else:
        crashDataCount += d['count']
    assert 2 == allCrashDataCount, 'Expected 2, got %d'%allCrashDataCount
    assert 2 == allCrashDataCount0, 'Expected 2, got %d'%allCrashDataCount0
    assert 2 == allCrashDataCount1, 'Expected 2, got %d'%allCrashDataCount1
    assert 2 == crashDataCount, 'Expected 2, got %d'%crashDataCount

    # we should get all but the last 2 (or one) item: Half-open interval
    start = minStamp
    end = maxStamp
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount = 0
    allCrashDataCount = 0
    allCrashDataCount0 = 0
    allCrashDataCount1 = 0
    for k,d in crashData.items():
      if (None,None) == k[:2]:
        allCrashDataCount += d['count']
      elif(None) == k[0]:
        allCrashDataCount0 += d['count']
      elif(None) == k[1]:
        allCrashDataCount1 += d['count']
      else:
        crashDataCount += d['count']
    assert crashDataCount == 9, 'Expected 9 Got %s'%crashDataCount
    assert allCrashDataCount == 9, 'Expected 9 Got %s'%allCrashDataCount
    assert allCrashDataCount0 == 9, 'Expected 9 Got %s'%allCrashDataCount0
    assert allCrashDataCount1 == 9, 'Expected 9 Got %s'%allCrashDataCount1

    # we should get all the data
    start = minStamp
    end = maxStamp+dt.timedelta(milliseconds=1)
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount = 0
    allCrashDataCount = 0
    allCrashDataCount0 = 0
    allCrashDataCount1 = 0
    for k,d in crashData.items():
      if (None,None) == k[:2]:
        allCrashDataCount += d['count']
      elif(None) == k[0]:
        allCrashDataCount0 += d['count']
      elif(None) == k[1]:
        allCrashDataCount1 += d['count']
      else:
        crashDataCount += d['count']
    assert crashDataCount == 10, 'Expected 10. Got %s'%crashDataCount
    assert allCrashDataCount == 10, 'Expected 10. Got %s'%allCrashDataCount
    assert allCrashDataCount0 == 10, 'Expected 10. Got %s'%allCrashDataCount0
    assert allCrashDataCount1 == 10, 'Expected 10. Got %s'%allCrashDataCount1

    # we should get nothing if start == end (half open interval that stops juuuust before the start)
    start = minStamp
    end = minStamp
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    assert crashData == {}, 'But got %s'%crashData

    # we should get precise stamp's data if end = start+teeny-tiny-epsilon
    start = minStamp
    end = start+dt.timedelta(microseconds=1)
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount = 0
    allCrashDataCount = 0
    allCrashDataCount0 = 0
    allCrashDataCount1 = 0
    for k,d in crashData.items():
      if (None,None) == k[:2]:
        allCrashDataCount += d['count']
      elif(None) == k[0]:
        allCrashDataCount0 += d['count']
      elif(None) == k[1]:
        allCrashDataCount1 += d['count']
      else:
        crashDataCount += d['count']
    assert crashDataCount == 1, 'Expected 1. Got %s'%crashDataCount
    assert allCrashDataCount == 1, 'Expected 1. Got %s'%allCrashDataCount
    assert allCrashDataCount0 == 1, 'Expected 1. Got %s'%allCrashDataCount0
    assert allCrashDataCount1 == 1, 'Expected 1. Got %s'%allCrashDataCount1

    # We should throw if start > end
    assert_raises(ValueError,tc.extractDataForPeriod,maxStamp,minStamp,crashData)

  def testExtractDataForPeriod_ByClientCrashDate(self):
    """
    testExtractDataForPeriod_ByClientCrashDate(self):
     - Check that we get nothing for a period outside our data
     - Check that we get expected count for period inside our data
     - Check that we get half-open interval (don't get data exactly at last moment)
     - Check that we get all for period that surrounds our data
     - Check that we raise ValueError for period with dates reversed
    """
    global me
    minStamp,maxStamp,data = self.prepareExtractDataForPeriod('client_crash_date')
    keySet = set([(d['productdims_id'],d['osdims_id']) for d in data])
    mminStamp = minStamp - dt.timedelta(days=1)
    mmaxStamp = maxStamp + dt.timedelta(days=1)
    self.prepareConfigForPeriod(keySet,mminStamp,mmaxStamp)
    tc = topcrasher.TopCrasher(me.config)
    tc.dateColumnName = 'client_crash_date'
    # we should get nothing if we are outside our data
    start = minStamp - dt.timedelta(days=10)
    end = start + dt.timedelta(days=1)
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    assert {} == crashData,'Expected {}, got %s'%crashData

    # We should get exactly one day's worth
    start = minStamp
    end = start + dt.timedelta(days=1)
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount = 0
    allCrashDataCount = 0
    allCrashDataCount0 = 0
    allCrashDataCount1 = 0
    for k,d in crashData.items():
      if (None,None) == k[:2]:
        allCrashDataCount += d['count']
      elif(None) == k[0]:
        allCrashDataCount0 += d['count']
      elif(None) == k[1]:
        allCrashDataCount1 += d['count']
      else:
        crashDataCount += d['count']
    assert 2 == allCrashDataCount, 'Expected 2, got %d'%allCrashDataCount
    assert 2 == allCrashDataCount0, 'Expected 2, got %d'%allCrashDataCount0
    assert 2 == allCrashDataCount1, 'Expected 2, got %d'%allCrashDataCount1
    assert 2 == crashDataCount, 'Expected 2, got %d'%crashDataCount

    # we should get all but the last 2 (or one) item: Half-open interval
    start = minStamp
    end = maxStamp
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount = 0
    allCrashDataCount = 0
    allCrashDataCount0 = 0
    allCrashDataCount1 = 0
    for k,d in crashData.items():
      if (None,None) == k[:2]:
        allCrashDataCount += d['count']
      elif(None) == k[0]:
        allCrashDataCount0 += d['count']
      elif(None) == k[1]:
        allCrashDataCount1 += d['count']
      else:
        crashDataCount += d['count']
    assert crashDataCount == 9, 'Expected 9. Got %s'%allCrashDataCount
    assert allCrashDataCount == 9, 'Expected 9. Got %s'%allCrashDataCount
    assert allCrashDataCount0 == 9, 'Expected 9. Got %s'%allCrashDataCount
    assert allCrashDataCount1 == 9, 'Expected 9. Got %s'%allCrashDataCount

    # we should get all the data
    start = minStamp
    end = maxStamp+dt.timedelta(milliseconds=1)
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount = 0
    allCrashDataCount = 0
    allCrashDataCount0 = 0
    allCrashDataCount1 = 0
    for k,d in crashData.items():
      if (None,None) == k[:2]:
        allCrashDataCount += d['count']
      elif(None) == k[0]:
        allCrashDataCount0 += d['count']
      elif(None) == k[1]:
        allCrashDataCount1 += d['count']
      else:
        crashDataCount += d['count']
    assert allCrashDataCount == 10, 'Expected 10. Got %s'%allCrashDataCount
    assert allCrashDataCount0 == 10, 'Expected 10. Got %s'%allCrashDataCount0
    assert allCrashDataCount1 == 10, 'Expected 10. Got %s'%allCrashDataCount1
    assert crashDataCount == 10, 'Expected 10. Got %s'%crashDataCount

    # we should get nothing if start == end (half open interval that stops juuuust before the start)
    start = minStamp
    end = minStamp
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    assert crashData == {}, 'But got %s'%crashData

    # we should get precise stamp's data if end = start+teeny-tiny-epsilon
    start = minStamp
    end = start+dt.timedelta(microseconds=1)
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount = 0
    allCrashDataCount = 0
    allCrashDataCount0 = 0
    allCrashDataCount1 = 0
    for k,d in crashData.items():
      if (None,None) == k[:2]:
        allCrashDataCount += d['count']
      elif(None) == k[0]:
        allCrashDataCount0 += d['count']
      elif(None) == k[1]:
        allCrashDataCount1 += d['count']
      else:
        crashDataCount += d['count']
    assert crashDataCount == 1, 'Expected 1. Got %s'%crashDataCount
    assert allCrashDataCount == 1, 'Expected 1. Got %s'%allCrashDataCount
    assert allCrashDataCount0 == 1, 'Expected 1. Got %s'%allCrashDataCount0
    assert allCrashDataCount1 == 1, 'Expected 1. Got %s'%allCrashDataCount1

    # We should throw if start > end
    assert_raises(ValueError,tc.extractDataForPeriod,maxStamp,minStamp,crashData)

  def testFixupCrashData(self):
    """
    testFixupCrashData(self):(slow=1)
      - create a bunch of data, count it in the test, put it into the reports table, then 
        let TopCrasher get it back out, and assert that fixup gets the same count
    """
    global me
    cursor = self.connection.cursor()
    data = makeReportData(211,5,cursor) # 211 is prime, which means we should get a nice spread of data
    keySet = set([(d['productdims_id'],d['osdims_id']) for d in data])
    expect = {}
    for d in data:
      key = (d['productdims_id'],d['osdims_id'],d['signaturedims_id'])
      akey = (None,None,d['signaturedims_id'])
      akeyp = (None,d['osdims_id'],d['signaturedims_id'])
      akeyo = (d['productdims_id'],None,d['signaturedims_id'])
      keys = [key,akey,akeyp,akeyo]
      for k in keys:
        try:
          expect[k]['count'] += 1
          expect[k]['uptime'] += d['uptime']
        except:
          expect[k] = {}
          expect[k]['count'] = 1
          expect[k]['uptime'] = d['uptime']
    addReportData(cursor,data)
    self.connection.commit()
    tc = topcrasher.TopCrasher(me.config)
    tc.dateColumnName = 'date_processed'
    baseDate = testBaseDate 
    start = baseDate - dt.timedelta(days=1)
    end = baseDate + dt.timedelta(days=6)
    self.prepareConfigForPeriod(keySet,start,end)
    
    summaryCrashes = {}
    tc.extractDataForPeriod(start,end,summaryCrashes)
    assert expect == summaryCrashes, 'Oops. You will need to debug on this. Sorry. Try commenting this line and un-commenting the next bunch'
#     # the next few lines amount to "assert expect == summaryCrashes" but with more useful error detail
#     # check that we have a chance of equality
#     assert len(expect) == len(summaryCrashes), 'Expected equal lengths but expected:%s versus got:%s'%(len(expect),len(summaryCrashes))
#     getter = itemgetter('count','uptime')
#     # check that everything in what we got is expected
#     for k,v in summaryCrashes.items():
#       assert getter(expect[k]) == getter(v), 'for key %s: Expected %s but got %s'%(k,getter(expect[k]),getter(v))
#     # check that everything we expect is in what we got
#     for k,v in expect.items():
#       assert getter(v) == getter(summaryCrashes[k]),  'for key %s: Expected %s but got %s'%(k,getter(v), getter(summaryCrashes[k]))
    result = tc.fixupCrashData(summaryCrashes)
    resultx = tc.fixupCrashData(expect)
    assert result == resultx
    expectedLen = [376,56,49,7]
    expectedAll0 = set([1,2,3,4,5])
    expectedAll1 = set([6,7])
    gotAll0 = set([ x['signaturedims_id'] for x in result[-1][:5]])
    gotAll1 = set([ x['signaturedims_id'] for x in result[-1][-2:]])
    assert expectedAll0 == gotAll0 , 'But got %s'%gotAll0
    assert expectedAll1 == gotAll1 , 'But got %s'%gotAll1
    countsAP = set([42,41,28,27,14,13])
    for index in range(len(result)):
      chain = result[index]
      assert expectedLen[index] == len(chain)
      ranks = [x['rank'] for x in chain]
      counts = [x['count'] for x in chain]
      assert ranks == sorted(ranks)
      assert counts == sorted(counts, reverse=True)
      if index == 2:
        for r in chain:
          assert r['count'] in countsAP, 'but found %s'%r['count']

  def testExtractDataForPeriod_ConfigLimitedDates(self):
    global me
    minStamp,maxStamp,data = self.prepareExtractDataForPeriod('date_processed',23,5)
    keySet = set([(d['productdims_id'],d['osdims_id']) for d in data])
    keySSet = set([(d['productdims_id'],d['osdims_id']) for d in data if 5 != d['osdims_id']])
    mminStamp = minStamp - dt.timedelta(days=1)
    mmaxStamp = maxStamp + dt.timedelta(days=1)
    self.prepareConfigForPeriod(keySet,mminStamp,mmaxStamp)
    tc = topcrasher.TopCrasher(me.config)
    tc.dateColumnName = 'date_processed'

    summaryData = {}
    tc.extractDataForPeriod(minStamp,maxStamp,summaryData)
    assert 222 == len(summaryData), 'Regression test only, value not calculated. Expect 222, got %s'%(len(summaryData))

    cursor = self.connection.cursor()
    cursor.execute("DELETE from tcbysignatureconfig")
    self.connection.commit()

    mminStamp = minStamp + dt.timedelta(days=1)
    mmaxStamp = maxStamp + dt.timedelta(days=1)
    self.prepareConfigForPeriod(keySet,mminStamp,mmaxStamp)
    summaryData = {}
    tc.extractDataForPeriod(minStamp,maxStamp,summaryData)
    assert 199 == len(summaryData), 'Regression test only, value not calculated. Expect 199, got %s'%(len(summaryData))


  def testExtractDataForPeriod_ConfigLimitedIds(self):
    global me
    minStamp,maxStamp,data = self.prepareExtractDataForPeriod('date_processed',23,5)
    keySet = set([(d['productdims_id'],d['osdims_id']) for d in data])
    keySSet = set([(d['productdims_id'],d['osdims_id']) for d in data if 5 != d['osdims_id']])
    mminStamp = minStamp - dt.timedelta(days=1)
    mmaxStamp = maxStamp + dt.timedelta(days=1)
    self.prepareConfigForPeriod(keySet,mminStamp,mmaxStamp)
    tc = topcrasher.TopCrasher(me.config)
    tc.dateColumnName = 'date_processed'

    summaryData = {}
    tc.extractDataForPeriod(minStamp,maxStamp,summaryData)
    assert 222 == len(summaryData), 'Regression test only, value not calculated. Expect 222, got %s'%(len(summaryData))

    cursor = self.connection.cursor()
    cursor.execute("DELETE from tcbysignatureconfig")
    self.connection.commit()

    self.prepareConfigForPeriod(keySSet,mminStamp,mmaxStamp)
    summaryData = {}
    tc.extractDataForPeriod(minStamp,maxStamp,summaryData)
    assert 194 == len(summaryData), 'Regression test only, value not calculated. Expect 194, got %s'%(len(summaryData))

  def testStoreFacts(self):
    global me
    cursor = self.connection.cursor()
    minStamp, maxStamp, data = self.prepareExtractDataForPeriod('date_processed',31,5) # full set of keys
    self.connection.commit()
    keySet = set([(d['productdims_id'],d['osdims_id']) for d in data])
    tc = topcrasher.TopCrasher(me.config)
    tc.dateColumnName = 'date_processed'
    beforeDate = minStamp-dt.timedelta(minutes=30)
    afterDate = maxStamp+dt.timedelta(minutes=60)
    self.prepareConfigForPeriod(keySet,beforeDate,afterDate)
    summaryCrashes = {}
    summaryCrashes = tc.extractDataForPeriod(beforeDate,afterDate,summaryCrashes)

    countSql = "SELECT count(*) from topcrashfacts"
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    assert 0 == gotCount, 'but got a count of %s'%gotCount

    #Try with none
    tc.storeFacts([[],[],[],[]],testFirstIntervalBegin,tc.processingInterval)
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    assert 0 == gotCount, 'but got %s'%gotCount

    #Try with three
    smKeys = summaryCrashes.keys()[:3]
    sum = dict((k,summaryCrashes[k]) for k in smKeys)
    cd = tc.fixupCrashData(sum)
    stime = dt.datetime(2009,9,8,7,15)
    tc.storeFacts(cd,stime,15);
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    assert 3 == gotCount, 'but got %s'%gotCount
    cursor.execute("SELECT interval_start,interval_minutes from topcrashfacts")
    got = cursor.fetchall()
    self.connection.commit()
    expect = [(stime,15),] * gotCount
    assert expect == got, 'but got %s'%(got)

    cursor.execute("DELETE FROM topcrashfacts")
    self.connection.commit()

    #Try with about half
    smKeys = summaryCrashes.keys()[-130:]
    sum = dict((k,summaryCrashes[k]) for k in smKeys)
    cd = tc.fixupCrashData(sum)
    tc.storeFacts(cd,dt.datetime(2009,9,8,7,15),15)
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    assert 130 == gotCount, 'but got %s'%gotCount    
    cursor.execute("SELECT interval_start,interval_minutes from topcrashfacts")
    got = cursor.fetchall()
    self.connection.commit()
    expect = [(stime,15),] * gotCount
    assert expect == got, 'but got %s'%(got)

    cursor.execute("DELETE FROM topcrashfacts")
    self.connection.commit()

    #Try with all of them
    cd = tc.fixupCrashData(summaryCrashes)
    tc.storeFacts(cd,dt.datetime(2009,9,8,7,15),15)
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    assert len(summaryCrashes) == gotCount, 'but got %s'%gotCount    
    cursor.execute("SELECT interval_start,interval_minutes from topcrashfacts")
    got = cursor.fetchall()
    self.connection.commit()
    expect = [(stime,15),] * gotCount
    assert expect == got, 'but got %s'%(got)

  def testProcessIntervals(self):
    global me
    cursor = self.connection.cursor()

    # test a small full set of keys. Since we have already tested each component, that should be enough 
    minStamp, maxStamp, data = self.prepareExtractDataForPeriod('date_processed',31,5) # full set of keys
    configBegin = minStamp - dt.timedelta(hours=1)
    configEnd = maxStamp + dt.timedelta(hours=1)
    keySet = set([(d['productdims_id'],d['osdims_id']) for d in data])
    self.prepareConfigForPeriod(keySet,configBegin,configEnd)
    tc = topcrasher.TopCrasher(me.config)

    # first assure that we have a clean playing field
    countSql = "SELECT count(*) from topcrashfacts"
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    assert 0 == gotCount, "but topcrashfacts isn't empty. Had %s rows"%gotCount

    sDate = minStamp.replace(hour=0,minute=0,second=0,microsecond=0)
    maxMin = 30
    dHour = dt.timedelta(hours=0)
    if maxStamp.minute >= 30:
      maxMin = 0
      dHour = dt.timedelta(hours=1)
    eDate = maxStamp.replace(minute=maxMin,second=0,microsecond=0)+dHour
    tc.setProcessingInterval(15)
    tc.dateColumnName= 'client_crash_date'
    tc.processIntervals(startDate=sDate, endDate=eDate, dateColumnName='date_processed',processingInterval=30)
    assert 15 == tc.processingInterval
    assert 'client_crash_date' == tc.dateColumnName

    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    me.logger.debug("DEBUG testProcessIntervals after count topcrashfacts = %s",gotCount)
    assert 496 == gotCount, 'Expect 496 rows (this is only a regression test, 620 was not calculated but found). Got %s'%gotCount

if __name__ == "__main__":
  unittest.main()
