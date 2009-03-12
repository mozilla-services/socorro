import copy
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
  logFileDir = os.path.split(me.config.logFilePathname)[0]
  try:
    os.makedirs(logFileDir)
  except OSError,x:
    if errno.EEXIST == x.errno: pass
    else: raise
  f = open(me.config.logFilePathname,'w')
  f.close()
  fileLog = logging.FileHandler(me.config.logFilePathname, 'a')
  fileLog.setLevel(logging.DEBUG)
  fileLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
  fileLog.setFormatter(fileLogFormatter)
  me.fileLogger = logging.getLogger("testMtbf")
  me.fileLogger.addHandler(fileLog)
  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)

# Create and destroy these tables for MTBF testing. Create in this order
mtbfTables = ["mtbfconfig","mtbffacts","productdims",]
fbtmTables = copy.copy(mtbfTables)
fbtmTables.reverse() # probably not needed, but not wrong, and maybe good
def createMtbfTables(cursor,config):
  '''Create tables for MTBF testing. Starts with dropping them all, in case'''
  global mtbfTables
  # always work from clear deck:
  dropMtbfTables(cursor)
  createSqls = {
    'mtbffacts': ["""CREATE TABLE mtbffacts (
                  id serial NOT NULL PRIMARY KEY,
                  avg_seconds integer NOT NULL,
                  report_count integer NOT NULL,
                  unique_users integer NOT NULL,
                  day date,
                  productdims_id integer
                  )""",
                  """CREATE INDEX mtbffacts_day_key ON mtbffacts USING btree (day)""",
                  """CREATE INDEX mtbffacts_product_id_key ON mtbffacts USING btree (productdims_id)""",
                  ],
    'mtbfconfig': ["""CREATE TABLE mtbfconfig (
                     id serial NOT NULL PRIMARY KEY,
                     productdims_id integer,
                     start_dt date,
                     end_dt date
                     )""",
                   """CREATE INDEX mtbfconfig_end_dt_key ON mtbfconfig USING btree (end_dt)""",
                   """CREATE INDEX mtbfconfig_start_dt_key ON mtbfconfig USING btree (start_dt)""",
                   ],
    'productdims': [""" CREATE TABLE productdims (
                    id serial NOT NULL PRIMARY KEY,
                    product character varying(30) NOT NULL,
                    version character varying(16) NOT NULL,
                    os_name character varying(100),
                    release character varying(50) NOT NULL
                    )""",
                    """CREATE UNIQUE INDEX productdims_product_version_os_name_release_key ON productdims USING btree (product, version, release, os_name)""",
                    # Foreign key constraints using this table id as FK
                    """ALTER TABLE ONLY mtbfconfig
                    ADD CONSTRAINT mtbfconfig_productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id)""",
                    """ALTER TABLE ONLY mtbffacts
                    ADD CONSTRAINT mtbffacts_productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id)"""
                    ],
    }
  try:
    for table in mtbfTables:
      for sql in createSqls[table]:
        cursor.execute(sql)
    cursor.connection.commit()
  except Exception,x:
    print "PROBLEM",x # DEBUG
    cursor.connection.rollback()
    raise
    
def dropMtbfTables(cursor):
  '''unilaterally drop the mtbf-exclusive tables'''
  sql = "DROP TABLE IF EXISTS %s CASCADE"%(", ".join(fbtmTables))
  cursor.execute(sql)
  cursor.connection.commit()

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
    dropMtbfTables(cursor)
    self.testDB.removeDB(self.config,self.logger)

    self.testDB.createDB(self.config,self.logger)
    createMtbfTables(cursor,self.config)
    
  def tearDown(self):
    dropMtbfTables(self.connection.cursor())
    self.testDB.removeDB(self.config,self.logger)

  def fillMtbfTables(self,cursor):
    """
    Need some data to test with. Here's where we make it out of whole cloth...
    """
    # (id),product,version,os,release : what product is it, by id
    prods = ['zorro','vogel','lizz',]
    oss = ['OSX','LOX','WOX',]
    productDimData = [ [prods[p],'%s.1.%s'%(p,r), oss[o], 'beta-%s'%r] for p in range(2) for o in range(2) for r in range(1,4) ]
    cursor.executemany('INSERT into productdims (product,version,os_name,release) values (%s,%s,%s,%s)',productDimData)
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
    self.processingDays = [
      (self.baseDate + dt.timedelta(days=-1), -1, []),
      (self.baseDate + dt.timedelta(days= 0),  0, [1,4]),
      (self.baseDate + dt.timedelta(days= 5),  5, [1,4]),
      (self.baseDate + dt.timedelta(days=10), 10, [1,2,4,5,7,10]),
      (self.baseDate + dt.timedelta(days=15), 15, [1,2,4,5,7,10]),
      (self.baseDate + dt.timedelta(days=25), 25, [1,2,3,4,5,6,7,8,10,11]),
      (self.baseDate + dt.timedelta(days=35), 35, [2,3,5,6,7,8,9,10,11,12]),
      (self.baseDate + dt.timedelta(days=45), 45, [3,6,8,9,11,12]),
      (self.baseDate + dt.timedelta(days=55), 55, [9,12]),
      (self.baseDate + dt.timedelta(days=60), 60, [9,12]),
      (self.baseDate + dt.timedelta(days=61), 61, []),
    ]

    # (id), productdims_id, start_dt, end_dt : Date-interval when product is interesting
    configData =[ (x[0],self.intervals[x[2]][0],self.intervals[x[2]][1] ) for x in productDimData ]
    cursor.executemany('insert into mtbfconfig (productdims_id,start_dt,end_dt) values(%s,%s,%s)',configData)
    cursor.connection.commit()

  def fillReports(self,cursor):
    """fill enough data to test mtbf behavior:
       - AVG(uptime); COUNT(date_processed); COUNT(DISTINCT(user_id))
    """
    sql = 'insert into reports (uuid, uptime, date_processed) values(%s, %s,%s)'
    processTimes = ['00:00:00','10:00:00','20:00:00','23:59:59']
    uptimes =  [0,10,100,150,200,450,500,700,900,1000,4000,]
    upIdx = 0
    data = []
    uuidGen = dbtestutil.moreUuid()
    for d,off,ig in self.processingDays:
      for loop in range(7+upIdx%3+upIdx%5):
        pt = processTimes[upIdx%len(processTimes)]
        dp = "%s %s"%(d.isoformat(),pt)
        data.append((uuidGen.next(), uptimes[upIdx%len(uptimes)],dp))
        upIdx += 1
    cursor.executemany(sql,data)
    cursor.connection.commit()

  # ========================================================================== #  
  def testCalculateMtbf(self):
    cursor = self.connection.cursor()
    self.fillMtbfTables(cursor)
    self.fillReports(cursor)
    sql = 'select * from mtbffacts'
    cursor.execute(sql)
    print "\nPRE",cursor.fetchall()
    self.connection.commit()
    for pd in self.processingDays:
      self.config.processingDay = pd[0].isoformat()
      products = mtbf.getProductsToUpdate(cursor,self.config,self.logger)
      print "PD %s (%s) %s"%((pd[0]),pd[1],len(products)),["%s:%s"%(x.dimensionId,x.product) for x in products]
      mtbf.calculateMtbf(self.config, self.logger)
      cursor.execute(sql)
      data = cursor.fetchall()
      self.connection.commit()
      print 'INDEX %s, Length: %s'%(pd[1],len(data))
      for d in data:
        print "FACT",d
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
