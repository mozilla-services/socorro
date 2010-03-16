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
import socorro.database.cachedIdAccess as cia

import socorro.cron.topCrashesBySignature as topcrasher

from   socorro.unittest.testlib.testDB import TestDB
import socorro.unittest.testlib.dbtestutil as dbtestutil
import socorro.unittest.testlib.util as tutil
import cronTestconfig as testConfig

testBaseDate = dt.datetime(2008,1,1,1,1,1,1)
testFirstIntervalBegin = dt.datetime(2008,1,1)

class Me:
  pass
me = None

def setup_module():
  tutil.nosePrintModule(__file__)

def addReportData(cursor,dataToAdd):
  sql = """INSERT INTO reports
     (uuid, client_crash_date, date_processed, product, version, url, install_age, last_crash, uptime, os_name, os_version, user_comments, signature) VALUES
     ( %(uuid)s, %(client_crash_date)s, %(date_processed)s, %(product)s, %(version)s, %(url)s, %(install_age)s, %(last_crash)s, %(uptime)s, %(os_name)s, %(os_version)s, %(user_comments)s, %(signature)s)
    """
  cursor.executemany(sql,dataToAdd)

def addCrashData(cursor,dataToAdd):
  # dataToAdd is [{},...] for dictionaries of values as shown in sql below
  sql = """INSERT INTO top_crash_by_signature
    (  count,    uptime,    last_updated,    signature,    productdims_id,    osdims_id) VALUES
    (%(count)s,%(uptime)s,%(last_updated)s,%(signature)s,%(productdims_id)s,%(osdims_id)s) """
  cursor.executemany(sql,dataToAdd)
  cursor.connection.commit()

dataForStartDateTest = [
  {'count':18,'uptime':64.5,'last_updated':dt.datetime(2009,3,3,3,3,3), 'productdims_id':1,'osdims_id':1,'signature':'_PR_MD_SEND'},
  {'count':10,'uptime':56.4,'last_updated':dt.datetime(2009,3,3,3,3,5), 'productdims_id':2,'osdims_id':1,'signature':'nsAutoCompleteController::ClosePopup'},
  {'count':1, 'uptime':45.6,'last_updated':dt.datetime(2009,3,3,3,3,7), 'productdims_id':3,'osdims_id':2,'signature':'nsFormFillController::SetPopupOpen'},
  ]

def genOs():
  data = dbtestutil.dimsData['osdims']
  assert 7 == len(data), 'So we can correctly create weightedList below'
  pairs = [(x['os_name'],x['os_version']) for x in data]
  weightedList = [0,1,1,2,2,2,3,4,4,5,6] # len 11 is a nice prime number, different than all the others
  while True:
    for o in weightedList:
      yield pairs[o]

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

def genProd():
  data =  dbtestutil.dimsData['productdims']
  assert 8 == len(data), 'So we can correctly create weightedList below'
  pairs = [(x['product'],x['version']) for x in data]
  weightedList = [0,0,1,1,2,2,2,3,3,4,4,5,5,6,6,7,7] # len 17 is a nice prime number, different than all the others
  while True:
    for o in weightedList:
      yield pairs[o]

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

signatureData = ['js_Interpret',
                 '_PR_MD_SEND',
                 'nsAutoCompleteController::ClosePopup',
                 'nsFormFillController::SetPopupOpen',
                 'xpcom_core.dll@0x31b7a',
                 'morkRowObject::CloseRowObject(morkEnv*)',
                 'nsContainerFrame::ReflowChild(nsIFrame*, nsPresContext*, nsHTMLReflowMetrics&, nsHTMLReflowState const&, int, int, unsigned int, unsigned int&, nsOverflowContinuationTracker*)',
                 ]
def genSig():
  global signatureData
  assert 7 == len(signatureData), 'Better be 7!, but was %s'%(len(signatureData))
  while True:
    for s in signatureData:
      yield s

def genUrl():
  data = dbtestutil.dimsData['urldims']
  assert 13 == len(data) # a nice prime number
  pairs = [(x['domain'],x['url']) for x in data]
  while True:
    for p in pairs:
      yield p

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

def makeReportData(sizePerDay,numDays):
  idGen = dbtestutil.moreUuid()
  osGen = genOs()
  prodGen = genProd()
  sigGen = genSig()
  urlGen = genUrl()
  bumpGen = genBump(sizePerDay)
  buildGen = genBuild()
  baseDate = testBaseDate
  procOffset = dt.timedelta(days=1,milliseconds=1903)
  insData = []
  for dummyDays in range(numDays):
    currentDate = baseDate
    count = 0
    while count < sizePerDay:
      product,version = prodGen.next()
      os_name,os_version = osGen.next()
      data = {
        'uuid':idGen.next(),
        'client_crash_date':currentDate,
        'install_age':1100,
        'last_crash':0,
        'uptime':1000,
        'date_processed': currentDate+procOffset,
        'user_comments': 'oh help',
        'app_notes':"",
        'signature':sigGen.next(),
        'product':product,
        'version':version,
        'os_name':os_name,
        'os_version':os_version,
        'url':urlGen.next()[1],
        }
      insData.append(data)
      currentDate += bumpGen.next()
      count += 1
    baseDate = baseDate+dt.timedelta(days=1)
  #print "client_crash_date          | date_processed             | uptm | uuid                                 | inst |  u, o, p, s"
  #for j in insData:
  #  print "%(client_crash_date)s | %(date_processed)s | %(uptime)s | %(uuid)s | %(install_age)s | %(urldims_id)2s,%(osdims_id)2s,%(productdims_id)2s,%(signature)s"%j
  return insData

def createMe():
  global me
  if not me:
    me = Me()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName = "Testing TopCrashesBySignature")
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

class TestTopCrashesBySignature(unittest.TestCase):
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
    cia.clearCache()
    self.connection.close()

  def prepareConfigForPeriod(self,idkeys,startDate,endDate):
    """enter a row for each idkey, start and end date. Do it repeatedly if you need different ones"""
    cfgKeys = set([x[0] for x in idkeys])
    cfgdata = [[x,startDate,endDate] for x in cfgKeys]
    self.connection.cursor().execute("delete from product_visibility")
    sql = "INSERT INTO product_visibility (productdims_id,start_date,end_date) VALUES (%s,%s,%s)"
    self.connection.cursor().executemany(sql,cfgdata)
    self.connection.commit()

  def prepareExtractDataForPeriod(self, columnName, sizePerDay=2, numDays=5):
    """Put some crash data into reports table, return their extrema for the columnName specified"""
    global me
    cursor = self.connection.cursor()
    data = makeReportData(sizePerDay,numDays)
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
    """
    TestTopCrashesBySignature.testConstructor
    """
    global me
    for reqd in ["databaseHost","databaseName","databaseUserName","databasePassword",]:
      cc = copy.copy(me.config)
      del(cc[reqd])
      assert_raises(SystemExit,topcrasher.TopCrashesBySignature,cc)
    bogusMap = {'databaseHost':me.config.databaseHost,'databaseName':me.config.databaseName,'databaseUserName':'JoeLuser','databasePassword':me.config.databasePassword}
    assert_raises(SystemExit,topcrasher.TopCrashesBySignature,bogusMap)

    #check without specific config items
    now = dt.datetime.now()
    tc = topcrasher.TopCrashesBySignature(me.config)
    expectedStart = now.replace(hour=0,minute=0,second=0,microsecond=0) - tc.configContext.get('initialDeltaDate',dt.timedelta(days=4))
    expectedEnd = now.replace(hour=0,minute=0,second=0,microsecond=0)
    assert expectedStart == tc.startDate
    assert tc.endDate <= now, 'But NOT %s <= %s'%(tc.endDate,now)
    assert dt.timedelta(days=4) <= tc.deltaDate, 'But got %s'%(tc.deltaDate)
    # Check for defaults. If the defaults are hard-code changed, this block needs equivalent changes
    assert 'date_processed' == tc.dateColumnName
    # end Check for defaults

    # check with solo startDate, endDate or deltaDate. Now should work
    config = copy.copy(me.config)
    config['startDate'] = dt.datetime(2009,01,01,0,0,1)

    config = copy.copy(me.config)
    config['endDate'] = dt.datetime(2009,01,01,0,0,1)

    config = copy.copy(me.config)
    config['deltaDate'] = dt.timedelta(days=3)

  def testExtractDataForPeriod_ByDateProcessed(self):
    """
    TestTopCrashesBySignature.testExtractDataForPeriod_ByDateProcessed(self):
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
    cursor = self.connection.cursor()
    idCache = cia.IdCache(cursor)
    keySet = set([(idCache.getProductId(d['product'],d['version']),idCache.getOsId(d['os_name'],d['os_version'])) for d in data])
    mminStamp = minStamp - dt.timedelta(days=1)
    mmaxStamp = maxStamp + dt.timedelta(days=1)
    self.prepareConfigForPeriod(keySet,mminStamp,mmaxStamp)

    tc = topcrasher.TopCrashesBySignature(me.config)
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
    crashDataCount = 0 # all three known
    for k,d in crashData.items():
      crashDataCount += d['count']
    assert 2 == crashDataCount, 'Expected 2, got %d'%crashDataCount

    # we should get all but the last 2 (or one) item: Half-open interval
    start = minStamp
    end = maxStamp
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount = 0 # all three known
    for k,d in crashData.items():
      crashDataCount += d['count']
    assert crashDataCount == 9, 'Expected 9. Got %s'%crashDataCount

    # we should get all the data
    start = minStamp
    end = maxStamp+dt.timedelta(milliseconds=1)
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount = 0 # all three known
    for k,d in crashData.items():
      crashDataCount += d['count']
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
    crashDataCount = 0 # all three known
    for k,d in crashData.items():
      crashDataCount += d['count']
    assert crashDataCount == 1, 'Expected 1. Got %s'%crashDataCount

    # We should throw if start > end
    assert_raises(ValueError,tc.extractDataForPeriod,maxStamp,minStamp,crashData)

  def testExtractDataForPeriod_ByClientCrashDate(self):
    """
    TestTopCrashesBySignature.testExtractDataForPeriod_ByClientCrashDate(self):
     - Check that we get nothing for a period outside our data
     - Check that we get expected count for period inside our data
     - Check that we get half-open interval (don't get data exactly at last moment)
     - Check that we get all for period that surrounds our data
     - Check that we raise ValueError for period with dates reversed
    """
    global me
    minStamp,maxStamp,data = self.prepareExtractDataForPeriod('client_crash_date')
    cursor = self.connection.cursor()
    idCache = cia.IdCache(cursor)
    keySet = set([(idCache.getProductId(d['product'],d['version']),idCache.getOsId(d['os_name'],d['os_version'])) for d in data])
    mminStamp = minStamp - dt.timedelta(days=1)
    mmaxStamp = maxStamp + dt.timedelta(days=1)
    self.prepareConfigForPeriod(keySet,mminStamp,mmaxStamp)
    tc = topcrasher.TopCrashesBySignature(me.config)
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
    crashDataCount0 = 0 # all three known
    for k,d in crashData.items():
      crashDataCount0 += d['count']
    assert 2 == crashDataCount0, 'Expected 2, got %d'%crashDataCount0

    # we should get all but the last 2 (or one) item: Half-open interval
    start = minStamp
    end = maxStamp
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount0 = 0 # all three known
    for k,d in crashData.items():
      crashDataCount0 += d['count']
    assert crashDataCount0 == 9, 'Expected 9. Got %s'%crashDataCount0

    # we should get all the data
    start = minStamp
    end = maxStamp+dt.timedelta(milliseconds=1)
    crashData = {}
    tc.extractDataForPeriod(start,end,crashData)
    crashDataCount0 = 0 # all three known
    for k,d in crashData.items():
      crashDataCount0 += d['count']
    assert crashDataCount0 == 10, 'Expected 10. Got %s'%crashDataCount0

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
    crashDataCount0 = 0 # all three known
    for k,d in crashData.items():
      crashDataCount0 += d['count']
    assert crashDataCount0 == 1, 'Expected 1. Got %s'%crashDataCount0

    # We should throw if start > end
    assert_raises(ValueError,tc.extractDataForPeriod,maxStamp,minStamp,crashData)

  def testFixupCrashData(self):
    """
    TestTopCrashesBySignature.testFixupCrashData(self):(slow=1)
      - create a bunch of data, count it in the test, put it into the reports table, then
        let TopCrashesBySignature get it back out, and assert that fixup gets the same count
    """
    global me
    cursor = self.connection.cursor()
    idCache = cia.IdCache(cursor)
    data = makeReportData(211,5) # 211 is prime, which means we should get a nice spread of data
    keySet = set([(idCache.getProductId(d['product'],d['version']),idCache.getOsId(d['os_name'],d['os_version'])) for d in data])
    #keySet = set([(d['productdims_id'],d['osdims_id']) for d in data])
    expect = {}
    newCount = 0
    oldCount = 0
    for d in data:
      # Keys are always signature,product,os
      key =   (d['signature'],idCache.getProductId(d['product'],d['version']),idCache.getOsId(d['os_name'],d['os_version']))
      if d['version'][-3:] == 'pre': continue    # Lars buildid
      try:
        expect[key]['count'] += 1
        expect[key]['uptime'] += d['uptime']
        oldCount += 1
      except:
        expect[key] = {}
        expect[key]['count'] = 1
        expect[key]['uptime'] = d['uptime']
        newCount += 1
    addReportData(cursor,data)
    self.connection.commit()
    tc = topcrasher.TopCrashesBySignature(me.config)
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

    result = tc.fixupCrashData(summaryCrashes,baseDate,dt.timedelta(minutes=19))
    result.sort(key=itemgetter('count'),reverse=True)
    resultx = tc.fixupCrashData(expect,baseDate,dt.timedelta(minutes=19))
    resultx.sort(key=itemgetter('count'),reverse=True)
    assert result == resultx
#    ## The next few lines show more detail if there's a problem. Comment above, uncomment below
#    misscount = fullcount = 0
#     if result != resultx:
#       assert len(result) == len(resultx), 'expected len: %s, got %s'%(len(result), len(resultx))
#       for i in range(len(result)):
#         r = result[i]
#         rx = resultx[i]
#         assert len(r) == len(rx), 'at loop %s: expected len: %s got %s'(i,len(r),len(rx))
#         for j in range(len(r)):
#           fullcount += 1
#           if r[j] != rx[j]:
#             print "unequal at loop %s, item %s:\n  %s\n  %s"%(i,j,r[j],rx[j])
#             misscount += 1
#       print "Unequal for %s of %s (%3.1f%%) rows"%(misscount,fullcount,100.0*(1.0*misscount/fullcount))
#     assert 0 == misscount, "They weren't equal. Look nearby for details"
    expectedAll = set(['xpcom_core.dll@0x31b7a', 'js_Interpret', '_PR_MD_SEND', 'nsFormFillController::SetPopupOpen', 'nsAutoCompleteController::ClosePopup','morkRowObject::CloseRowObject(morkEnv*)', 'nsContainerFrame::ReflowChild(nsIFrame*, nsPresContext*, nsHTMLReflowMetrics&, nsHTMLReflowState const&, int, int, unsigned int, unsigned int&, nsOverflowContinuationTracker*)'])

    gotAll = set([ x['signature'] for x in result])
    assert expectedAll == gotAll , 'ex-got:%s\ngot-ex:%s'%(expectedAll-gotAll,gotAll-expectedAll)

  def testExtractDataForPeriod_ConfigLimitedDates(self):
    """
    TestTopCrashesBySignature.testExtractDataForPeriod_ConfigLimitedDates(self)
    """
    global me
    minStamp,maxStamp,data = self.prepareExtractDataForPeriod('date_processed',23,5)
    cursor = self.connection.cursor()
    idCache = cia.IdCache(cursor)
    keySet = set([(idCache.getProductId(d['product'],d['version']),idCache.getOsId(d['os_name'],d['os_version'])) for d in data])
    keySSet = set([x for x in keySet if 5 != x[0]])
    mminStamp = minStamp - dt.timedelta(days=1)
    mmaxStamp = maxStamp + dt.timedelta(days=1)
    self.prepareConfigForPeriod(keySet,mminStamp,mmaxStamp)
    tc = topcrasher.TopCrashesBySignature(me.config)
    tc.dateColumnName = 'date_processed'

    summaryData = {}
    tc.extractDataForPeriod(minStamp,maxStamp,summaryData)
    #assert 110 == len(summaryData), 'Regression test only, value not calculated. Expect 110, got %s'%(len(summaryData)) #Lars buildid
    assert 99 == len(summaryData), 'Regression test only, value not calculated. Expect 99, got %s'%(len(summaryData))

    cursor.execute("DELETE from product_visibility")
    self.connection.commit()

    mminStamp = minStamp + dt.timedelta(days=1)
    mmaxStamp = maxStamp + dt.timedelta(days=1)
    self.prepareConfigForPeriod(keySet,mminStamp,mmaxStamp)
    summaryData = {}
    tc.extractDataForPeriod(minStamp,maxStamp,summaryData)
    #assert 87 == len(summaryData), 'Regression test only, value not calculated. Expect 87, got %s'%(len(summaryData)) #Lars buildid
    assert 78 == len(summaryData), 'Regression test only, value not calculated. Expect 78, got %s'%(len(summaryData))


  def testExtractDataForPeriod_ConfigLimitedIds(self):
    """
    TestTopCrashesBySignature.testExtractDataForPeriod_ConfigLimitedIds
    """
    global me
    cursor = self.connection.cursor()
    idCache = cia.IdCache(cursor)
    minStamp,maxStamp,data = self.prepareExtractDataForPeriod('date_processed',23,5)
    keySet = set([(idCache.getProductId(d['product'],d['version']),idCache.getOsId(d['os_name'],d['os_version'])) for d in data])
    keySSet = set([x for x in keySet if 5 != x[0]])
    mminStamp = minStamp - dt.timedelta(days=1)
    mmaxStamp = maxStamp + dt.timedelta(days=1)
    self.prepareConfigForPeriod(keySet,mminStamp,mmaxStamp)
    tc = topcrasher.TopCrashesBySignature(me.config)
    tc.dateColumnName = 'date_processed'

    summaryData = {}
    tc.extractDataForPeriod(minStamp,maxStamp,summaryData)
    #assert 110 == len(summaryData), 'Regression test only, value not calculated. Expect 110, got %s'%(len(summaryData)) #Lars buildid
    assert 99 == len(summaryData), 'Regression test only, value not calculated. Expect 99, got %s'%(len(summaryData))

    cursor.execute("DELETE from product_visibility")
    self.connection.commit()

    self.prepareConfigForPeriod(keySSet,mminStamp,mmaxStamp)
    summaryData = {}
    tc.extractDataForPeriod(minStamp,maxStamp,summaryData)
    #assert 96 == len(summaryData), 'Regression test only, value not calculated. Expect 96, got %s'%(len(summaryData)) #Lars buildid
    assert 85 == len(summaryData), 'Regression test only, value not calculated. Expect 85, got %s'%(len(summaryData))

  def testStoreFacts(self):
    """
    TestTopCrashesBySignature.testStoreFacts
    """
    global me
    cursor = self.connection.cursor()
    idCache = cia.IdCache(cursor)
    minStamp, maxStamp, data = self.prepareExtractDataForPeriod('date_processed',31,5) # full set of keys
    keySet = set([(idCache.getProductId(d['product'],d['version']),idCache.getOsId(d['os_name'],d['os_version'])) for d in data])
    tc = topcrasher.TopCrashesBySignature(me.config)
    tc.dateColumnName = 'date_processed'
    beforeDate = minStamp-dt.timedelta(minutes=30)
    afterDate = maxStamp+dt.timedelta(minutes=60)
    self.prepareConfigForPeriod(keySet,beforeDate,afterDate)
    summaryCrashes = {}
    summaryCrashes = tc.extractDataForPeriod(beforeDate,afterDate,summaryCrashes)

    countSql = "SELECT count(*) from top_crashes_by_signature"
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    assert 0 == gotCount, 'but got a count of %s'%gotCount

    #Try with none
    tc.storeFacts([],"the test interval")
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    assert 0 == gotCount, 'but got %s'%gotCount

    #Try with three
    smKeys = summaryCrashes.keys()[:3]
    sum = dict((k,summaryCrashes[k]) for k in smKeys)
    stime = dt.datetime(2009,9,8,7,30)
    fifteen = dt.timedelta(minutes=15)
    cd = tc.fixupCrashData(sum,stime,fifteen)
    tc.storeFacts(cd,"interval three")
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    assert 3 == gotCount, 'but got %s'%gotCount
    cursor.execute("SELECT window_end, window_size from top_crashes_by_signature")
    got = cursor.fetchall()
    self.connection.commit()
    expect = [(stime,fifteen),] * gotCount
    assert expect == got, 'but got %s'%(got)

    cursor.execute("DELETE FROM top_crashes_by_signature")
    self.connection.commit()

    #Try with about half
    smKeys = summaryCrashes.keys()[-130:]
    sum = dict((k,summaryCrashes[k]) for k in smKeys)
    cd = tc.fixupCrashData(sum,dt.datetime(2009,9,8,7,30),fifteen)
    tc.storeFacts(cd,"interval about half")
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    #assert 130 == gotCount, 'but got %s'%gotCount #Lars buildid
    assert 129 == gotCount, 'but got %s'%gotCount
    cursor.execute("SELECT window_end,window_size from top_crashes_by_signature")
    got = cursor.fetchall()
    self.connection.commit()
    expect = [(stime,fifteen),] * gotCount
    assert expect == got, 'but got %s'%(got)

    cursor.execute("DELETE FROM top_crashes_by_signature")
    self.connection.commit()

    #Try with all of them
    cd = tc.fixupCrashData(summaryCrashes,dt.datetime(2009,9,8,7,30),fifteen)
    tc.storeFacts(cd,"all of them")
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    assert len(summaryCrashes) == gotCount, 'but got %s'%gotCount
    cursor.execute("SELECT window_end, window_size from top_crashes_by_signature")
    got = cursor.fetchall()
    self.connection.commit()
    expect = [(stime,fifteen),] * gotCount
    assert expect == got, 'but got %s'%(got)

  def testChangeWindowSize(self):
    """
    TestTopCrashesBySignature.testChangeWindowSize
    """
    global me
    cursor = self.connection.cursor()
    idCache = cia.IdCache(cursor,logger=me.logger)
    minStamp, maxStamp, data = self.prepareExtractDataForPeriod('date_processed',31,5) # full set of keys
    bogusEnd = dt.datetime(2007,12,30)
    bogusSize = dt.timedelta(minutes=20)
    configBegin = minStamp - dt.timedelta(hours=1)
    configEnd = maxStamp + dt.timedelta(hours=1)
    keySet = set([(idCache.getProductId(d['product'],d['version']),idCache.getOsId(d['os_name'],d['os_version'])) for d in data])
    self.prepareConfigForPeriod(keySet,configBegin,configEnd)
    getSql = "SELECT window_end,window_size FROM top_crashes_by_signature ORDER BY id DESC LIMIT 1"
    cursor.execute(getSql)
    got = cursor.fetchone()
    assert None == got, 'Expect no data at this point, but %s'%(str(got))
    self.connection.rollback()
    inSql = "INSERT INTO top_crashes_by_signature (window_end,window_size) VALUES (%s,%s)"
    cursor.execute(inSql,(bogusEnd,bogusSize))
    self.connection.commit()
    cursor.execute(getSql)
    got = cursor.fetchone()
    self.connection.rollback()
    assert bogusSize == got[1],'But it was %s'%(str(got))
    config = copy.copy(me.config)
    config['startDate'] = dt.datetime(2008,1,2,1)
    config['endDate'] = dt.datetime(2008,1,2,2)
    config['startWindow'] = config['startDate']
    config['deltaWindow'] = dt.timedelta(minutes=10)
    tc = topcrasher.TopCrashesBySignature(config)
    tc.processDateInterval()
    cursor.execute(getSql)
    got = cursor.fetchone()
    self.connection.rollback()
    assert config['deltaWindow'] == got[1], 'But it was %s'%(str(got))

    config['startDate'] = config['endDate']
    config['endDate'] = dt.datetime(2008,1,2,3)
    config['deltaDate'] = config['endDate'] - config['startDate']
    config['startWindow'] = config['startDate']
    config['deltaWindow'] = dt.timedelta(minutes=60)
    config['endWindow'] = config['startWindow']+config['deltaWindow']
    tc = topcrasher.TopCrashesBySignature(config)
    tc.processDateInterval()
    cursor.execute(getSql)
    got = cursor.fetchone()
    self.connection.rollback()
    assert config['deltaWindow'] == got[1], 'But it was %s'%(str(got))

  def testProcessDateInterval(self):
    """
    TestTopCrashesBySignature.testProcessDateInterval
    """
    global me
    cursor = self.connection.cursor()
    idCache = cia.IdCache(cursor)

    # test a small full set of keys. Since we have already tested each component, that should be enough
    minStamp, maxStamp, data = self.prepareExtractDataForPeriod('date_processed',31,5) # full set of keys
    configBegin = minStamp - dt.timedelta(hours=1)
    configEnd = maxStamp + dt.timedelta(hours=1)
    keySet = set([(idCache.getProductId(d['product'],d['version']),idCache.getOsId(d['os_name'],d['os_version'])) for d in data])
    self.prepareConfigForPeriod(keySet,configBegin,configEnd)
    tc = topcrasher.TopCrashesBySignature(me.config)
    config = copy.copy(me.config)
    config['startWindow'] = dt.datetime(2008,1,2,0,0)
    config['deltaWindow'] = dt.timedelta(minutes=12)
    config['endWindow'] = config['startWindow']+config['deltaWindow']
    config['startDate'] =  dt.datetime(2008,1,2,0,0)
    config['endDate'] = dt.datetime(2008,1,6,5,0)
    config['deltaDate'] = config['endDate'] - config['startDate']
    tc = topcrasher.TopCrashesBySignature(config)

    # first assure that we have a clean playing field
    countSql = "SELECT count(*) from top_crashes_by_signature"
    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    assert 0 == gotCount, "but top_crashes_by_signature isn't empty. Had %s rows"%gotCount

    sDate = minStamp.replace(hour=0,minute=0,second=0,microsecond=0)
    maxMin = 30
    dHour = dt.timedelta(hours=0)
    if maxStamp.minute >= 30:
      maxMin = 0
      dHour = dt.timedelta(hours=1)
    eDate = maxStamp.replace(minute=maxMin,second=0,microsecond=0)+dHour
    tc.dateColumnName= 'client_crash_date'
    tc.processDateInterval(startDate=sDate, endDate=eDate, dateColumnName='date_processed')
    assert 'client_crash_date' == tc.dateColumnName

    cursor.execute(countSql)
    self.connection.commit()
    gotCount = cursor.fetchone()[0]
    me.logger.debug("DEBUG testProcessIntervals after count top_crashes_by_signature = %s",gotCount)
    expect = 137
    #expect = 155 # Lars buildid
    assert expect == gotCount, 'Regression test only, value not calculated. Expect %s, got %s'%(expect,gotCount)

if __name__ == "__main__":
  unittest.main()
