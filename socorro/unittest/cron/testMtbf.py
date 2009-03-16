import datetime as dt
import errno
import logging
import os
import time

import psycopg2

import unittest
from nose.tools import *

import socorro.lib.ConfigurationManager as configurationManager

import socorro.cron.mtbf as mtbf

from createTables import createCronTables, dropCronTables
import socorro.unittest.testlib.dbtestutil as dbtestutil
from   socorro.unittest.testlib.loggerForTest import TestingLogger
from   socorro.unittest.testlib.testDB import TestDB

import mtbfTestconfig as testConfig

class Me(): # not quite "self"
  """
  I need stuff to be initialized once per module. Rather than having a bazillion globals, lets just have 'me'
  """
  pass
me = None

def setup_module():
  global me
  if me:
    return
  me = Me()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing MTBF')
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass
  me.logFilePathname = me.config.logFilePathname
  if not me.logFilePathname:
    me.logFilePathname = 'logs/mtbf_test.log'
  logFileDir = os.path.split(me.logFilePathname)[0]
  try:
    os.makedirs(logFileDir)
  except OSError,x:
    if errno.EEXIST == x.errno: pass
    else: raise
  f = open(me.logFilePathname,'w')
  f.close()
  fileLog = logging.FileHandler(me.logFilePathname, 'a')
  fileLog.setLevel(logging.DEBUG)
  fileLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
  fileLog.setFormatter(fileLogFormatter)
  me.fileLogger = logging.getLogger("testMtbf")
  me.fileLogger.addHandler(fileLog)
  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)

def teardown_module():
  try:
    os.unlink(me.logFilePathname)
  except:
    pass

# Create and destroy these tables for MTBF testing. Create in this order
mtbfTables = ["mtbfconfig","mtbffacts","productdims",]
class TestMtbf(unittest.TestCase):
  def setUp(self):
    global me
    self.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing MTBF')
    
    self.config.mtbfTables = ["mtbfconfig","mtbffacts","productdims",]
    myDir = os.path.split(__file__)[0]
    if not myDir: myDir = '.'
    replDict = {'testDir':'%s'%myDir}
    for i in self.config:
      try:
        self.config[i] = self.config.get(i)%(replDict)
      except:
        pass
    self.logger = TestingLogger(me.fileLogger)
    self.connection = psycopg2.connect(me.dsn)
    cursor = self.connection.cursor()
    self.testDB = TestDB()
    dropCronTables(cursor,mtbfTables)
    self.testDB.removeDB(self.config,self.logger)

    self.testDB.createDB(self.config,self.logger)
    self.prods = ['zorro','vogel','lizz',]
    self.oss = ['OSX','LOX','WOX',]
    self.productDimData = [] # filled in by fillMtbfTables
    createCronTables(cursor,mtbfTables)
    
  def tearDown(self):
    dropCronTables(self.connection.cursor(),mtbfTables)
    self.testDB.removeDB(self.config,self.logger)
    self.logger.clear()

  def fillMtbfTables(self,cursor):
    """
    Need some data to test with. Here's where we make it out of whole cloth...
    """
    # (id),product,version,os,release : what product is it, by id
    self.productDimData = [ [self.prods[p],'%s.1.%s'%(p,r), self.oss[o], 'beta-%s'%r] for p in range(2) for o in range(2) for r in range(1,4) ]
    cursor.executemany('INSERT into productdims (product,version,os_name,release) values (%s,%s,%s,%s)',self.productDimData)
    cursor.connection.commit()
    cursor.execute("SELECT id, product,version, os_name, release from productdims")
    productDimData = cursor.fetchall()
    cursor.connection.commit()
    self.baseDate = dt.date(2008,1,1)
    self.intervals = {
      '0.1.1':(self.baseDate                        ,self.baseDate+dt.timedelta(days=30)),
      '0.1.2':(self.baseDate + dt.timedelta(days=10),self.baseDate + dt.timedelta(days=40)),
      '0.1.3':(self.baseDate + dt.timedelta(days=20),self.baseDate + dt.timedelta(days=50)),
      '1.1.1':(self.baseDate + dt.timedelta(days=10),self.baseDate + dt.timedelta(days=40)),
      '1.1.2':(self.baseDate + dt.timedelta(days=20),self.baseDate + dt.timedelta(days=50)),
      '1.1.3':(self.baseDate + dt.timedelta(days=30),self.baseDate + dt.timedelta(days=60)),
      }
    # processing days are located at and beyond the extremes of the full range, and
    # at some interior points, midway between each pair of interior points
    # layout is: (a date, the day-offset from baseDate, the expected resulting [ids])
    PDindexes = [-1,0,5,10,15,25,35,45,55,60,61]
    productsInProcessingDay = [
      [], #  -1,
      [1,4],#  0,
      [1,4],#  5,
      [1,2,4,5,7,10],#  10,
      [1,2,4,5,7,10],#  15,
      [1,2,3,4,5,6,7,8,10,11],#  25,
      [2,3,5,6,7,8,9,10,11,12],#  35,
      [3,6,8,9,11,12],#  45,
      [9,12],#  55,
      [9,12],#  60,
      [],#  61,
      ]
    self.processingDays = [ (self.baseDate+dt.timedelta(days=PDindexes[x]),PDindexes[x],productsInProcessingDay[x]) for x in range(len(PDindexes))]
    
    # (id), productdims_id, start_dt, end_dt : Date-interval when product is interesting
    configData =[ (x[0],self.intervals[x[2]][0],self.intervals[x[2]][1] ) for x in productDimData ]
    cursor.executemany('insert into mtbfconfig (productdims_id,start_dt,end_dt) values(%s,%s,%s)',configData)
    cursor.connection.commit()

    self.expectedFacts = {
      # key is offset from baseDate
      # value is array of (productDims_id,day,avg_seconds,report_count,count(distinct(user))
      # This data WAS NOT CALCULATED BY HAND: The test was run once with prints in place
      # and that output was encoded here. As of 2009-Feb, count of unique users is always 0
      -1: [],
      0: [
      (1, dt.date(2008,1,1), 5, 6, 0),
      (4, dt.date(2008,1,1), 20, 6, 0),
      ],
      5: [
      (1, dt.date(2008,1,6), 5, 6, 0),
      (4, dt.date(2008,1,6), 20, 6, 0),
      ],
      10: [
      (1, dt.date(2008,1,11), 5, 6, 0),
      (2, dt.date(2008,1,11), 10, 6, 0),
      (4, dt.date(2008,1,11), 20, 6, 0),
      (5, dt.date(2008,1,11), 25, 6, 0),
      (7, dt.date(2008,1,11), 35, 6, 0),
      (10, dt.date(2008,1,11), 50, 6, 0),
      ],
      15: [
      (1, dt.date(2008,1,16), 5, 6, 0),
      (2, dt.date(2008,1,16), 10, 6, 0),
      (4, dt.date(2008,1,16), 20, 6, 0),
      (5, dt.date(2008,1,16), 25, 6, 0),
      (7, dt.date(2008,1,16), 35, 6, 0),
      (10, dt.date(2008,1,16), 50, 6, 0),
      ],
      25: [
      (1, dt.date(2008,1,26), 5, 6, 0),
      (2, dt.date(2008,1,26), 10, 6, 0),
      (3, dt.date(2008,1,26), 15, 6, 0),
      (4, dt.date(2008,1,26), 20, 6, 0),
      (5, dt.date(2008,1,26), 25, 6, 0),
      (6, dt.date(2008,1,26), 30, 6, 0),
      (7, dt.date(2008,1,26), 35, 6, 0),
      (8, dt.date(2008,1,26), 40, 6, 0),
      (10, dt.date(2008,1,26), 50, 6, 0),
      (11, dt.date(2008,1,26), 55, 6, 0),
      ],
      35: [
      (2, dt.date(2008,2,5), 10, 6, 0),
      (3, dt.date(2008,2,5), 15, 6, 0),
      (5, dt.date(2008,2,5), 25, 6, 0),
      (6, dt.date(2008,2,5), 30, 6, 0),
      (7, dt.date(2008,2,5), 35, 6, 0),
      (8, dt.date(2008,2,5), 40, 6, 0),
      (9, dt.date(2008,2,5), 45, 6, 0),
      (10, dt.date(2008,2,5), 50, 6, 0),
      (11, dt.date(2008,2,5), 55, 6, 0),
      (12, dt.date(2008,2,5), 60, 6, 0),
      ],
      45: [
      (3, dt.date(2008,2,15), 15, 6, 0),
      (6, dt.date(2008,2,15), 30, 6, 0),
      (8, dt.date(2008,2,15), 40, 6, 0),
      (9, dt.date(2008,2,15), 45, 6, 0),
      (11, dt.date(2008,2,15), 55, 6, 0),
      (12, dt.date(2008,2,15), 60, 6, 0),
      ],
      55: [
      (9, dt.date(2008,2,25), 45, 6, 0),
      (12, dt.date(2008,2,25), 60, 6, 0),
      ],
      60: [
      (9, dt.date(2008,3,1), 45, 6, 0),
      (12, dt.date(2008,3,1), 60, 6, 0),
      ],
      61: [],
      }

  def fillReports(self,cursor):
    """fill enough data to test mtbf behavior:
       - AVG(uptime); COUNT(date_processed); COUNT(DISTINCT(user_id))
    """
    self.fillMtbfTables(cursor) # prime the pump
    sql = 'insert into reports (uuid, uptime, date_processed,product,version,os_name) values(%s,%s,%s,%s,%s,%s)'
    processTimes = ['00:00:00','05:00:00','10:00:00','15:00:00','20:00:00','23:59:59']
    uptimes = [5*x for x in range(1,15)]
    data = []
    uuidGen = dbtestutil.moreUuid()
    uptimeIndex = 0
    for product in self.productDimData:
      uptime = uptimes[uptimeIndex%len(uptimes)]
      uptimeIndex += 1
      for d,off,ig in self.processingDays:
        for pt in processTimes:
          dp = "%s %s"%(d.isoformat(),pt)
          tup = (uuidGen.next(), uptime,dp,product[0],product[1],product[2])
          data.append(tup)
    cursor.executemany(sql,data)
    cursor.connection.commit()

  # ========================================================================== #  
  def testCalculateMtbf(self):
    """
    testCalculateMtbf(self): slow(1)
      check that we get the expected data. This is NOT hand-calculated, just a regression check
    """
    cursor = self.connection.cursor()
    self.fillReports(cursor)
    sql = 'select productdims_id,day,avg_seconds,report_count,unique_users from mtbffacts WHERE day = %s'
    self.connection.commit()
    for pd in self.processingDays:
      self.config.processingDay = pd[0].isoformat()
      mtbf.calculateMtbf(self.config, self.logger)
      cursor.execute(sql,(pd[0].isoformat(),))
      data = cursor.fetchall()
      self.connection.commit()
      expected = set(self.expectedFacts[pd[1]])
      got = set(data)
      assert expected==got, 'Expected: %s\nGot: %s'%(expected,got)
    #end of loop through processingDay
  
  # ========================================================================== #  
  def testGetProductsToUpdate(self):
    """
    testGetProductsToUpdate(self):
      check that we get the appropriate list of products when:
       - we have none (on either end of the range)
       - we have only one or several
      check that we correctly log when there are no products in range
    """
    cursor = self.connection.cursor()
    self.fillMtbfTables(cursor)
    for d in self.processingDays:
      self.config.processingDay = d[0].isoformat()
      self.logger.clear()
      products = mtbf.getProductsToUpdate(cursor,self.config,self.logger)
      self.connection.commit()
      if d[1] in (-1,61):
        # be sure that when appropriate we log a warning about no configured products
        assert 2 == len(self.logger)
        assert logging.WARNING == self.logger.levels[1]
        assert 'Currently there are no MTBF products configured' == self.logger.buffer[1]
      else:
        # ignore the expected logging: It could change. Catch unexpected logging calls
        assert len(d[2])+2 == len(self.logger)
        INF = 0
        DBG = 0
        oth = 0
        for i in self.logger.levels:
          if logging.INFO == i: INF += 1
          elif logging.DEBUG == i: DBG += 1
          else: oth += 1
        # Don't care about DBG or INFO counts, except we expect no other
        #assert len(d[2])+1 == INF, 'expected %d, but %s\n%s'%(len(d[2])+1,INF,str(self.logger))
        #assert 1 == DBG
        assert 0 == oth
      pids = set([x.dimensionId for x in products])
      expected = set(d[2])
      # This is the meat of the test
      assert expected == pids, 'Expected %s, got %s'%(expected,pids)
  
  # ========================================================================== #  
  def testGetWhereClauseFor(self):
    """
    testGetWhereClauseFor(self):
      check that we correctly handle the 'ALL' product
      check that we correctly order and truncate version,product,os_name
    """
    class P:
      pass
    p = P()
    p.product = 'ALL'
    assert '' == mtbf.getWhereClauseFor(p)
    p.product = 'product'
    assert_raises(AttributeError,mtbf.getWhereClauseFor,p)
    p.version = 'version'
    assert_raises(AttributeError,mtbf.getWhereClauseFor,p)
    p.os_name='os_name'
    expected = " AND version = 'version' AND product = 'product' AND substr(os_name, 1, 3) = 'os_name' "
    assert expected == mtbf.getWhereClauseFor(p), 'but "%s"'%(mtbf.getWhereClauseFor(p))

  # ========================================================================== #  
  def testClassProductDimension(self):
    """
    testClassProductDimension(self):
       check that we handle config with correct or greater items in config
    """
    assert_raises(IndexError,mtbf.ProductDimension,[])
    assert_raises(IndexError,mtbf.ProductDimension,[1])
    assert_raises(IndexError,mtbf.ProductDimension,[1,2])
    assert_raises(IndexError,mtbf.ProductDimension,[1,2,3])
    self.logger.clear()
    assert_raises(IndexError,mtbf.ProductDimension,[1,2,3,4])
    config = [999,'umlaut',3.14,'OX','lemme go','toomuch']
    pd = mtbf.ProductDimension(config,self.logger)
    assert 999 == pd.dimensionId
    assert 'umlaut' == pd.product
    assert 3.14 == pd.version
    assert 'OX' == pd.os_name
    assert 'lemme go' == pd.release
    assert 5 == len(pd.__dict__), "Assure nobody adds another dimension element without updating tests"
    assert 0 == len(self.logger),'but logger:\n%s'%self.logger
      
if __name__ == "__main__":
  unittest.main()
