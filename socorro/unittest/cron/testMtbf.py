import copy
import datetime
import errno
import logging
import os
import time

import psycopg2

import unittest
from nose.tools import *

import socorro.lib.ConfigurationManager as configurationManager

import socorro.cron.mtbf as mtbf

#from createTables import createCronTables, dropCronTables
import socorro.unittest.testlib.dbtestutil as dbtestutil
import socorro.unittest.testlib.util as tutil
from   socorro.unittest.testlib.loggerForTest import TestingLogger
from   socorro.unittest.testlib.testDB import TestDB

import cronTestconfig as testConfig

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
  tutil.nosePrintModule(__file__)
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

class TestMtbf(unittest.TestCase):
  def setUp(self):
    global me
    self.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing MTBF')
    
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
    self.testDB.removeDB(self.config,self.logger)
    self.testDB.createDB(self.config,self.logger)
    dbtestutil.fillDimsTables(self.connection.cursor())
    
  def tearDown(self):
    self.testDB.removeDB(self.config,self.logger)
    self.logger.clear()

  def fillMtbfTables(self,cursor,limit=12):
    self.processingDays, self.productDimData = dbtestutil.fillMtbfTables(cursor,limit)
    self.expectedFacts = {
      #productdims_id, osdims_id, day, sum_uptime_seconds, report_count
      -1: [],
      0: [
      (1, 5, datetime.datetime(2008, 1, 1, 0, 0), 270, 6),
      (1, 4, datetime.datetime(2008, 1, 1, 0, 0), 60, 6),
      ],
      5: [
      (1, 4, datetime.datetime(2008, 1, 6, 0, 0), 60, 6),
      (1, 5, datetime.datetime(2008, 1, 6, 0, 0), 270, 6),
      ],
      10: [
      (4, 4, datetime.datetime(2008, 1, 11, 0, 0), 240, 6),
      (1, 4, datetime.datetime(2008, 1, 11, 0, 0), 60, 6),
      (5, 4, datetime.datetime(2008, 1, 11, 0, 0), 90, 6),
      (1, 5, datetime.datetime(2008, 1, 11, 0, 0), 270, 6),
      (4, 5, datetime.datetime(2008, 1, 11, 0, 0), 330, 6),
      ],
      15: [
      (4, 5, datetime.datetime(2008, 1, 16, 0, 0), 330, 6),
      (1, 5, datetime.datetime(2008, 1, 16, 0, 0), 270, 6),
      (5, 4, datetime.datetime(2008, 1, 16, 0, 0), 90, 6),
      (4, 4, datetime.datetime(2008, 1, 16, 0, 0), 240, 6),
      (1, 4, datetime.datetime(2008, 1, 16, 0, 0), 60, 6),
      ],
      25: [
      (8, 4, datetime.datetime(2008, 1, 26, 0, 0), 30, 6),
      (5, 4, datetime.datetime(2008, 1, 26, 0, 0), 90, 6),
      (4, 5, datetime.datetime(2008, 1, 26, 0, 0), 330, 6),
      (6, 4, datetime.datetime(2008, 1, 26, 0, 0), 150, 6),
      (1, 4, datetime.datetime(2008, 1, 26, 0, 0), 60, 6),
      (1, 5, datetime.datetime(2008, 1, 26, 0, 0), 270, 6),
      (4, 4, datetime.datetime(2008, 1, 26, 0, 0), 240, 6),
      ],
      35: [
      (4, 5, datetime.datetime(2008, 2, 5, 0, 0), 330, 6),
      (6, 4, datetime.datetime(2008, 2, 5, 0, 0), 150, 6),
      (2, 4, datetime.datetime(2008, 2, 5, 0, 0), 180, 6),
      (1, 4, datetime.datetime(2008, 2, 5, 0, 0), 60, 6),
      (1, 5, datetime.datetime(2008, 2, 5, 0, 0), 270, 6),
      (8, 4, datetime.datetime(2008, 2, 5, 0, 0), 30, 6),
      (5, 4, datetime.datetime(2008, 2, 5, 0, 0), 90, 6),
      (2, 5, datetime.datetime(2008, 2, 5, 0, 0), 300, 6),
      (4, 4, datetime.datetime(2008, 2, 5, 0, 0), 240, 6),
      ],
      45: [
      (5, 4, datetime.datetime(2008, 2, 15, 0, 0), 90, 6),
      (2, 4, datetime.datetime(2008, 2, 15, 0, 0), 180, 6),
      (2, 5, datetime.datetime(2008, 2, 15, 0, 0), 300, 6),
      (1, 4, datetime.datetime(2008, 2, 15, 0, 0), 60, 6),
      (1, 5, datetime.datetime(2008, 2, 15, 0, 0), 270, 6),
      (4, 5, datetime.datetime(2008, 2, 15, 0, 0), 330, 6),
      (6, 4, datetime.datetime(2008, 2, 15, 0, 0), 150, 6),
      (4, 4, datetime.datetime(2008, 2, 15, 0, 0), 240, 6),
      (8, 4, datetime.datetime(2008, 2, 15, 0, 0), 30, 6),
      ],
      55: [
      (6, 4, datetime.datetime(2008, 2, 25, 0, 0), 150, 6),
      (2, 5, datetime.datetime(2008, 2, 25, 0, 0), 300, 6),
      (8, 4, datetime.datetime(2008, 2, 25, 0, 0), 30, 6),
      (4, 4, datetime.datetime(2008, 2, 25, 0, 0), 240, 6),
      (2, 4, datetime.datetime(2008, 2, 25, 0, 0), 180, 6),
      (1, 4, datetime.datetime(2008, 2, 25, 0, 0), 60, 6),
      (4, 5, datetime.datetime(2008, 2, 25, 0, 0), 330, 6),
      (1, 5, datetime.datetime(2008, 2, 25, 0, 0), 270, 6),
      (5, 4, datetime.datetime(2008, 2, 25, 0, 0), 90, 6),
      ],
      60: [
      (6, 4, datetime.datetime(2008, 3, 1, 0, 0), 150, 6),
      (4, 5, datetime.datetime(2008, 3, 1, 0, 0), 330, 6),
      (8, 4, datetime.datetime(2008, 3, 1, 0, 0), 30, 6),
      (2, 4, datetime.datetime(2008, 3, 1, 0, 0), 180, 6),
      (5, 4, datetime.datetime(2008, 3, 1, 0, 0), 90, 6),
      (1, 5, datetime.datetime(2008, 3, 1, 0, 0), 270, 6),
      (1, 4, datetime.datetime(2008, 3, 1, 0, 0), 60, 6),
      (4, 4, datetime.datetime(2008, 3, 1, 0, 0), 240, 6),
      (2, 5, datetime.datetime(2008, 3, 1, 0, 0), 300, 6),
      ],
      61: [
      (8, 4, datetime.datetime(2008, 3, 2, 0, 0), 30, 6),
      (4, 5, datetime.datetime(2008, 3, 2, 0, 0), 330, 6),
      (4, 4, datetime.datetime(2008, 3, 2, 0, 0), 240, 6),
      (6, 4, datetime.datetime(2008, 3, 2, 0, 0), 150, 6),
      (2, 5, datetime.datetime(2008, 3, 2, 0, 0), 300, 6),
      (5, 4, datetime.datetime(2008, 3, 2, 0, 0), 90, 6),
      (2, 4, datetime.datetime(2008, 3, 2, 0, 0), 180, 6),
      ],
      }
    
  def fillReports(self,cursor,doFillMtbfTables = True,multiplier=1):
    """fill enough data to test mtbf behavior:
       - SUM(uptime); COUNT(date_processed)
    """
    if doFillMtbfTables:
      self.fillMtbfTables(cursor) # prime the pump
    self.processingDays, self.productDimData = dbtestutil.fillReportsTable(cursor,False,False, multiplier)

  # ========================================================================== #  
  def testCalculateMtbf(self):
    """
    testCalculateMtbf(self): slow(1)
      check that we get the expected data. This is NOT hand-calculated, just a regression check
    """
    cursor = self.connection.cursor()
    self.fillReports(cursor)
    self.connection.commit()

    sql = "SELECT productdims_id,osdims_id,(window_end-window_size),sum_uptime_seconds,report_count FROM time_before_failure WHERE (window_end-window_size)=%s"
    for pd in self.processingDays:
      self.config['processingDay'] = pd[0].isoformat()
      mtbf.calculateMtbf(self.config, self.logger)
      cursor.execute(sql,(pd[0],))
      self.connection.commit()
      data = cursor.fetchall()
      expected = set(self.expectedFacts[pd[1]])
      got = set(data)
      assert expected == got, 'OOPS. Comment this line and uncomment the next block for details'
#       if not expected == got:
#         print
#         print len(expected) == len(got), 'For PD (%s), expected %s, got %s\nex-got: %s\ngot-ex: %s'%(pd[1],len(expected),len(got),expected-got, got-expected)
#         for x in expected:
#           assert x in got, 'For PD (%s) expected %s was not in got: %s'%(pd[1],x,got)
#         for g in got:
#           assert g in expected, 'For PD (%s) got %s was not in expected: %s'%(pd[1],g,expected)
#       # end of block: not expected == got
    #end of loop through processingDay
    
  def whichProduct(self,data):
    return "P:%s V:%s::OS:%s, OSV:%s"%(data.get('product','-'),data.get('version','-'),data.get('os_name','-'),data.get('os_version','-'))
  # ========================================================================== #  
  def testCalculateMtbf_kwargs(self):
    """
    testCalculateMtbf_kwargs(self):
    check that we do NOT get the default-specified data, but instead get data specified in kwargs:
      check that processingDay overrides config
      check that product and version remove other product data
      check that os_name and os_version remove other OSs
      check that slotEnd beats processingDay
      check that kwargs slotEnd beats config
      check that slotSizeMinutes raises AssertionError unless slotEnd
      check that slotSizeMinutes beats the default 1 day
      check that kwargs slotSizeMinutes beats config
    """
    cursor = self.connection.cursor()
    self.fillMtbfTables(cursor,limit=33)
    self.fillReports(cursor, False)
    self.connection.commit()
    sql = "SELECT productdims_id,osdims_id,(window_end-window_size),sum_uptime_seconds,report_count FROM time_before_failure WHERE (window_end-window_size)=%s"
    noTime = datetime.time(0,0,0)
    pd = self.processingDays[5]
    pdtS = datetime.datetime.combine(pd[0],noTime)
    pdtE = pdtS + datetime.timedelta(days=1)
    assert 25 == pd[1]
    self.config.processingDay = self.processingDays[3][0].isoformat()
    assert self.processingDays[3][0] != pd[0]
    cursor.execute(sql,(pdtS,))
    self.connection.commit()
    assert [] == cursor.fetchall(), 'Better be empty before we start mucking about'
    # override the day
    mtbf.calculateMtbf(self.config,self.logger,processingDay=pd[0].isoformat())
    # check that we got the overridden day
    cursor.execute(sql,(pdtS,))
    self.connection.commit()
    data = cursor.fetchall()
    for d in data:
      assert pdtS == d[2], 'Expected date: %s, got: %s'%(pdtS,d[2])
    # check that we did NOT get the config day
    cursor.execute(sql,(self.processingDays[3][0],))
    self.connection.commit()
    data = cursor.fetchall()
    assert [] == data, 'Expected empty, got %s'%(str(data))
    delSql = 'DELETE from time_before_failure'
    testList = [
      {'processingDay':pd[0].isoformat(),'product':'Thunderbird',
       'expected':[(pdtE, 'Thunderbird', '2.0.0.21', 'Mac OS X', '10.4.10 8R2218'),
                   (pdtE, 'Thunderbird', '2.0.0.21', 'Mac OS X', '10.5.6 9G2110'),
                   (pdtE, 'Thunderbird', '2.0.0.21', 'Linux', '2.6.27.21 i686'),
                   (pdtE, 'Thunderbird', '2.0.0.21', 'Linux', '2.6.28 i686'),
                   ],
       'debug':False,
       },
      {'processingDay':pd[0].isoformat(),'product':'Firefox','version':'3.1.1',
       'expected':[(pdtE, 'Firefox', '3.1.1', 'Mac OS X', '10.5.6 9G2110'),
                   (pdtE, 'Firefox', '3.1.1', 'Linux', '2.6.27.21 i686'),
                   (pdtE, 'Firefox', '3.1.1', 'Linux', '2.6.28 i686'),
                   (pdtE, 'Firefox', '3.1.1', 'Mac OS X', '10.4.10 8R2218'),
                   ],
       'debug':False,
       },
      {'processingDay':pd[0].isoformat(),'os_name':'Mac OS X',
       'expected':[(pdtE, 'Thunderbird', '2.0.0.21', 'Mac OS X', '10.4.10 8R2218'),
                   (pdtE, 'Firefox', '3.0.6', 'Mac OS X', '10.5.6 9G2110'),
                   (pdtE, 'Firefox', '3.0.6', 'Mac OS X', '10.4.10 8R2218'),
                   (pdtE, 'Firefox', '3.1.1', 'Mac OS X', '10.4.10 8R2218'),
                   (pdtE, 'Thunderbird', '2.0.0.21', 'Mac OS X', '10.5.6 9G2110'),
                   (pdtE, 'Firefox', '3.1.3b', 'Mac OS X', '10.5.6 9G2110'),
                   (pdtE, 'Firefox', '3.1.2b', 'Mac OS X', '10.5.6 9G2110'),
                   (pdtE, 'Firefox', '3.1.3b', 'Mac OS X', '10.4.10 8R2218'),
                   (pdtE, 'Firefox', '3.1.2b', 'Mac OS X', '10.4.10 8R2218'),
                   (pdtE, 'Firefox', '3.1.1', 'Mac OS X', '10.5.6 9G2110'),
                   ],
       'debug':True,
       },
      {'processingDay':pd[0].isoformat(),'os_name':'Mac OS X','os_version':'10.4.10 8R2218',
       'expected':[(pdtE, 'Thunderbird', '2.0.0.21', 'Mac OS X', '10.4.10 8R2218'),
                   (pdtE, 'Firefox', '3.0.6', 'Mac OS X', '10.4.10 8R2218'),
                   (pdtE, 'Firefox', '3.1.3b', 'Mac OS X', '10.4.10 8R2218'),
                   (pdtE, 'Firefox', '3.1.2b', 'Mac OS X', '10.4.10 8R2218'),
                   (pdtE, 'Firefox', '3.1.1', 'Mac OS X', '10.4.10 8R2218'),
                   ],
       'debug':True,
       },
      {'processingDay':pd[0].isoformat(),'product':'Thunderbird','os_name':'Mac OS X','os_version':'10.4.10 8R2218',
       'expected':[(pdtE, 'Thunderbird', '2.0.0.21', 'Mac OS X', '10.4.10 8R2218'),],
       'debug':False,
      },
      {'processingDay':pd[0].isoformat(),'product':'Thunderbird','version':'2.0.0.21',
                                         'os_name':'Mac OS X','os_version':'10.4.10 8R2218',
       'expected':[(pdtE, 'Thunderbird', '2.0.0.21', 'Mac OS X', '10.4.10 8R2218'),],
       'debug':False,
       },
      {'processingDay':pd[0].isoformat(),'product':'Thunderbird','version':'bogus',
                                         'os_name':'Mac OS X','os_version':'10.4.10 8R2218',
       'expected':[],
       'debug':False,
       },
      ]
    for testItem in testList:
      cursor.execute(delSql)
      self.connection.commit()
      cursor.execute(sql,(pdtS,))
      self.connection.commit()
      assert [] == cursor.fetchall(), 'Better be empty before we mucking about again'
      mtbf.calculateMtbf(self.config,self.logger,**testItem)
      cursor.execute('select f.window_end, p.product,p.version,o.os_name,o.os_version from time_before_failure f JOIN productdims p ON f.productdims_id = p.id JOIN osdims o ON f.osdims_id = o.id')
      self.connection.commit()
      got = cursor.fetchall()
      assert set(testItem.get('expected')) == set(got),"%s\nEX: %s\nGOT %s"%(self.whichProduct(testItem),testItem.get('expected'),got)
#       print "EXP: %s, GOT: %s"%(len(testItem.get('expected')), len(set(got)))
#       if not len(testItem.get('expected')) == len(set(got)):
#         print "OOPS "*5,self.whichProduct(testItem)
#         print "GOT - EXPECTED:",set(got)-set(testItem.get('expected'))
#         print "EXPECTED - GOT:",set(testItem.get('expected'))-set(got)

    #check that slotSizeMinutes raises AssertionError unless slotEnd
    goodProcessingDay = self.processingDays[4][0]
    assert_raises(AssertionError,mtbf.calculateMtbf,self.config,self.logger,slotSizeMinutes=200)
                  
    #check that slotEnd beats processingDay
    goodSlotEnd = goodProcessingDay+datetime.timedelta(days=1)
    badProcessingDay = datetime.datetime(2000,11,12,0,0,0) # well outside useful range
    self.config.processingDay = goodProcessingDay.isoformat()
    self.config['slotEnd'] = badProcessingDay.isoformat()
    cursor.execute(delSql)
    self.connection.commit()
    mtbf.calculateMtbf(self.config,self.logger)
    self.connection.commit()
    cursor.execute('select count(id) from time_before_failure')
    self.connection.commit()
    count = cursor.fetchone()[0]
    assert 0 == count, 'Expect no data from year 2000, but %s'%(count)

    #check that kwargs slotEnd beats config
    cursor.execute(delSql)
    self.connection.commit()
    self.config['slotEnd'] = badProcessingDay.isoformat()
    mtbf.calculateMtbf(self.config,self.logger,slotEnd=goodSlotEnd)
    self.connection.commit()
    cursor.execute('select count(id) from time_before_failure')
    self.connection.commit()
    count = cursor.fetchone()[0]
    assert 13 == count, 'Expect 13 rows from this good day, but got %s'%count
    
    #check that slotSizeMinutes beats the default 1 day
    cursor.execute("SELECT SUM(sum_uptime_seconds) from time_before_failure")
    self.connection.commit()
    fullDaySum = cursor.fetchone()[0]
    cursor.execute(delSql)
    self.connection.commit()
    mtbf.calculateMtbf(self.config,self.logger,slotEnd=goodSlotEnd,slotSizeMinutes=6,show=True)
    self.connection.commit()
    cursor.execute("SELECT SUM(sum_uptime_seconds) from time_before_failure")
    self.connection.commit()
    partDaySum = cursor.fetchone()[0]
    assert partDaySum < fullDaySum, 'Actually, expect full:2730 (got %s) , partial:455 (got %s)'%(fullDaySum,partDaySum)
     
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
        assert logging.WARNING == self.logger.levels[-1], "expected trailing WARNING, but %s"%(self.logger.levels)
        assert 'Currently there are no MTBF products configured' == self.logger.buffer[-1]
      else:
        pass # testing for expected log calls is sorta kinda stupid. 
      pids = set([x['product_id'] for x in products])
      expected = set(x[0] for x in d[2])
      # This is the meat of the test
      assert expected == pids, 'In day %s(%s), Expected %s, got %s'%(d[0],d[1],expected,pids)

  # ========================================================================== #  
  def testGetWhereClauseFor(self):
    """
    testGetWhereClauseFor(self):
      check that we correctly handle the 'ALL' product
      check that we correctly order and truncate version,product,os_name
    """
    expected = {
      (None,None,None,None):"",
      (None,None,None,'ALL'):"",
      (None,None,None,'os_version'):" AND os_version = 'os_version' ",
      (None,None,None,'0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' ",
      (None,None,None,'os_name os_versionn'):" AND substr(os_version, 1, 7) = 'os_name' ",
      (None,None,None,'os_name 0.0.0 os_version2'):" AND substr(os_version, 1, 7) = 'os_name' ",
      (None,None,'ALL',None):"",
      (None,None,'ALL','ALL'):"",
      (None,None,'ALL','os_version'):" AND os_version = 'os_version' ",
      (None,None,'ALL','0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' ",
      (None,None,'ALL','os_name os_versionn'):" AND substr(os_version, 1, 7) = 'os_name' ",
      (None,None,'ALL','os_name 0.0.0 os_version2'):" AND substr(os_version, 1, 7) = 'os_name' ",
      (None,None,'os_name',None):" AND substr(os_name, 1, 3) = 'os_' ",
      (None,None,'os_name','ALL'):" AND substr(os_name, 1, 3) = 'os_' ",
      (None,None,'os_name','os_version'):" AND os_version = 'os_version' AND substr(os_name, 1, 3) = 'os_' ",
      (None,None,'os_name','0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' AND substr(os_name, 1, 3) = 'os_' ",
      (None,None,'os_name','os_name os_versionn'):" AND substr(os_version, 9, 11) = 'os_versionn' AND substr(os_name, 1, 3) = 'os_' ",
      (None,None,'os_name','os_name 0.0.0 os_version2'):" AND substr(os_version, 15, 11) = 'os_version2' AND substr(os_name, 1, 3) = 'os_' ",
      (None,'ALL',None,None):"",
      (None,'ALL',None,'ALL'):"",
      (None,'ALL',None,'os_version'):" AND os_version = 'os_version' ",
      (None,'ALL',None,'0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' ",
      (None,'ALL',None,'os_name os_versionn'):" AND substr(os_version, 1, 7) = 'os_name' ",
      (None,'ALL',None,'os_name 0.0.0 os_version2'):" AND substr(os_version, 1, 7) = 'os_name' ",
      (None,'ALL','ALL',None):"",
      (None,'ALL','ALL','ALL'):"",
      (None,'ALL','ALL','os_version'):" AND os_version = 'os_version' ",
      (None,'ALL','ALL','0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' ",
      (None,'ALL','ALL','os_name os_versionn'):" AND substr(os_version, 1, 7) = 'os_name' ",
      (None,'ALL','ALL','os_name 0.0.0 os_version2'):" AND substr(os_version, 1, 7) = 'os_name' ",
      (None,'ALL','os_name',None):" AND substr(os_name, 1, 3) = 'os_' ",
      (None,'ALL','os_name','ALL'):" AND substr(os_name, 1, 3) = 'os_' ",
      (None,'ALL','os_name','os_version'):" AND os_version = 'os_version' AND substr(os_name, 1, 3) = 'os_' ",
      (None,'ALL','os_name','0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' AND substr(os_name, 1, 3) = 'os_' ",
      (None,'ALL','os_name','os_name os_versionn'):" AND substr(os_version, 9, 11) = 'os_versionn' AND substr(os_name, 1, 3) = 'os_' ",
      (None,'ALL','os_name','os_name 0.0.0 os_version2'):" AND substr(os_version, 15, 11) = 'os_version2' AND substr(os_name, 1, 3) = 'os_' ",
      (None,'version',None,None):" AND version = 'version' ",
      (None,'version',None,'ALL'):" AND version = 'version' ",
      (None,'version',None,'os_version'):" AND version = 'version' AND os_version = 'os_version' ",
      (None,'version',None,'0.0.0 os_verison0'):" AND version = 'version' AND substr(os_version, 7, 11) = 'os_verison0' ",
      (None,'version',None,'os_name os_versionn'):" AND version = 'version' AND substr(os_version, 1, 7) = 'os_name' ",
      (None,'version',None,'os_name 0.0.0 os_version2'):" AND version = 'version' AND substr(os_version, 1, 7) = 'os_name' ",
      (None,'version','ALL',None):" AND version = 'version' ",
      (None,'version','ALL','ALL'):" AND version = 'version' ",
      (None,'version','ALL','os_version'):" AND version = 'version' AND os_version = 'os_version' ",
      (None,'version','ALL','0.0.0 os_verison0'):" AND version = 'version' AND substr(os_version, 7, 11) = 'os_verison0' ",
      (None,'version','ALL','os_name os_versionn'):" AND version = 'version' AND substr(os_version, 1, 7) = 'os_name' ",
      (None,'version','ALL','os_name 0.0.0 os_version2'):" AND version = 'version' AND substr(os_version, 1, 7) = 'os_name' ",
      (None,'version','os_name',None):" AND version = 'version' AND substr(os_name, 1, 3) = 'os_' ",
      (None,'version','os_name','ALL'):" AND version = 'version' AND substr(os_name, 1, 3) = 'os_' ",
      (None,'version','os_name','os_version'):" AND version = 'version' AND os_version = 'os_version' AND substr(os_name, 1, 3) = 'os_' ",
      (None,'version','os_name','0.0.0 os_verison0'):" AND version = 'version' AND substr(os_version, 7, 11) = 'os_verison0' AND substr(os_name, 1, 3) = 'os_' ",
      (None,'version','os_name','os_name os_versionn'):" AND version = 'version' AND substr(os_version, 9, 11) = 'os_versionn' AND substr(os_name, 1, 3) = 'os_' ",
      (None,'version','os_name','os_name 0.0.0 os_version2'):" AND version = 'version' AND substr(os_version, 15, 11) = 'os_version2' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL',None,None,None):"",
      ('ALL',None,None,'ALL'):"",
      ('ALL',None,None,'os_version'):" AND os_version = 'os_version' ",
      ('ALL',None,None,'0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('ALL',None,None,'os_name os_versionn'):" AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL',None,None,'os_name 0.0.0 os_version2'):" AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL',None,'ALL',None):"",
      ('ALL',None,'ALL','ALL'):"",
      ('ALL',None,'ALL','os_version'):" AND os_version = 'os_version' ",
      ('ALL',None,'ALL','0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('ALL',None,'ALL','os_name os_versionn'):" AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL',None,'ALL','os_name 0.0.0 os_version2'):" AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL',None,'os_name',None):" AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL',None,'os_name','ALL'):" AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL',None,'os_name','os_version'):" AND os_version = 'os_version' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL',None,'os_name','0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL',None,'os_name','os_name os_versionn'):" AND substr(os_version, 9, 11) = 'os_versionn' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL',None,'os_name','os_name 0.0.0 os_version2'):" AND substr(os_version, 15, 11) = 'os_version2' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','ALL',None,None):"",
      ('ALL','ALL',None,'ALL'):"",
      ('ALL','ALL',None,'os_version'):" AND os_version = 'os_version' ",
      ('ALL','ALL',None,'0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('ALL','ALL',None,'os_name os_versionn'):" AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL','ALL',None,'os_name 0.0.0 os_version2'):" AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL','ALL','ALL',None):"",
      ('ALL','ALL','ALL','ALL'):"",
      ('ALL','ALL','ALL','os_version'):" AND os_version = 'os_version' ",
      ('ALL','ALL','ALL','0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('ALL','ALL','ALL','os_name os_versionn'):" AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL','ALL','ALL','os_name 0.0.0 os_version2'):" AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL','ALL','os_name',None):" AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','ALL','os_name','ALL'):" AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','ALL','os_name','os_version'):" AND os_version = 'os_version' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','ALL','os_name','0.0.0 os_verison0'):" AND substr(os_version, 7, 11) = 'os_verison0' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','ALL','os_name','os_name os_versionn'):" AND substr(os_version, 9, 11) = 'os_versionn' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','ALL','os_name','os_name 0.0.0 os_version2'):" AND substr(os_version, 15, 11) = 'os_version2' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','version',None,None):" AND version = 'version' ",
      ('ALL','version',None,'ALL'):" AND version = 'version' ",
      ('ALL','version',None,'os_version'):" AND version = 'version' AND os_version = 'os_version' ",
      ('ALL','version',None,'0.0.0 os_verison0'):" AND version = 'version' AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('ALL','version',None,'os_name os_versionn'):" AND version = 'version' AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL','version',None,'os_name 0.0.0 os_version2'):" AND version = 'version' AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL','version','ALL',None):" AND version = 'version' ",
      ('ALL','version','ALL','ALL'):" AND version = 'version' ",
      ('ALL','version','ALL','os_version'):" AND version = 'version' AND os_version = 'os_version' ",
      ('ALL','version','ALL','0.0.0 os_verison0'):" AND version = 'version' AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('ALL','version','ALL','os_name os_versionn'):" AND version = 'version' AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL','version','ALL','os_name 0.0.0 os_version2'):" AND version = 'version' AND substr(os_version, 1, 7) = 'os_name' ",
      ('ALL','version','os_name',None):" AND version = 'version' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','version','os_name','ALL'):" AND version = 'version' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','version','os_name','os_version'):" AND version = 'version' AND os_version = 'os_version' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','version','os_name','0.0.0 os_verison0'):" AND version = 'version' AND substr(os_version, 7, 11) = 'os_verison0' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','version','os_name','os_name os_versionn'):" AND version = 'version' AND substr(os_version, 9, 11) = 'os_versionn' AND substr(os_name, 1, 3) = 'os_' ",
      ('ALL','version','os_name','os_name 0.0.0 os_version2'):" AND version = 'version' AND substr(os_version, 15, 11) = 'os_version2' AND substr(os_name, 1, 3) = 'os_' ",
      ('product',None,None,None):" AND product = 'product' ",
      ('product',None,None,'ALL'):" AND product = 'product' ",
      ('product',None,None,'os_version'):" AND product = 'product' AND os_version = 'os_version' ",
      ('product',None,None,'0.0.0 os_verison0'):" AND product = 'product' AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('product',None,None,'os_name os_versionn'):" AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product',None,None,'os_name 0.0.0 os_version2'):" AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product',None,'ALL',None):" AND product = 'product' ",
      ('product',None,'ALL','ALL'):" AND product = 'product' ",
      ('product',None,'ALL','os_version'):" AND product = 'product' AND os_version = 'os_version' ",
      ('product',None,'ALL','0.0.0 os_verison0'):" AND product = 'product' AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('product',None,'ALL','os_name os_versionn'):" AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product',None,'ALL','os_name 0.0.0 os_version2'):" AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product',None,'os_name',None):" AND product = 'product' AND substr(os_name, 1, 3) = 'os_' ",
      ('product',None,'os_name','ALL'):" AND product = 'product' AND substr(os_name, 1, 3) = 'os_' ",
      ('product',None,'os_name','os_version'):" AND product = 'product' AND os_version = 'os_version' AND substr(os_name, 1, 3) = 'os_' ",
      ('product',None,'os_name','0.0.0 os_verison0'):" AND product = 'product' AND substr(os_version, 7, 11) = 'os_verison0' AND substr(os_name, 1, 3) = 'os_' ",
      ('product',None,'os_name','os_name os_versionn'):" AND product = 'product' AND substr(os_version, 9, 11) = 'os_versionn' AND substr(os_name, 1, 3) = 'os_' ",
      ('product',None,'os_name','os_name 0.0.0 os_version2'):" AND product = 'product' AND substr(os_version, 15, 11) = 'os_version2' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','ALL',None,None):" AND product = 'product' ",
      ('product','ALL',None,'ALL'):" AND product = 'product' ",
      ('product','ALL',None,'os_version'):" AND product = 'product' AND os_version = 'os_version' ",
      ('product','ALL',None,'0.0.0 os_verison0'):" AND product = 'product' AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('product','ALL',None,'os_name os_versionn'):" AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product','ALL',None,'os_name 0.0.0 os_version2'):" AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product','ALL','ALL',None):" AND product = 'product' ",
      ('product','ALL','ALL','ALL'):" AND product = 'product' ",
      ('product','ALL','ALL','os_version'):" AND product = 'product' AND os_version = 'os_version' ",
      ('product','ALL','ALL','0.0.0 os_verison0'):" AND product = 'product' AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('product','ALL','ALL','os_name os_versionn'):" AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product','ALL','ALL','os_name 0.0.0 os_version2'):" AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product','ALL','os_name',None):" AND product = 'product' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','ALL','os_name','ALL'):" AND product = 'product' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','ALL','os_name','os_version'):" AND product = 'product' AND os_version = 'os_version' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','ALL','os_name','0.0.0 os_verison0'):" AND product = 'product' AND substr(os_version, 7, 11) = 'os_verison0' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','ALL','os_name','os_name os_versionn'):" AND product = 'product' AND substr(os_version, 9, 11) = 'os_versionn' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','ALL','os_name','os_name 0.0.0 os_version2'):" AND product = 'product' AND substr(os_version, 15, 11) = 'os_version2' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','version',None,None):" AND version = 'version' AND product = 'product' ",
      ('product','version',None,'ALL'):" AND version = 'version' AND product = 'product' ",
      ('product','version',None,'os_version'):" AND version = 'version' AND product = 'product' AND os_version = 'os_version' ",
      ('product','version',None,'0.0.0 os_verison0'):" AND version = 'version' AND product = 'product' AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('product','version',None,'os_name os_versionn'):" AND version = 'version' AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product','version',None,'os_name 0.0.0 os_version2'):" AND version = 'version' AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product','version','ALL',None):" AND version = 'version' AND product = 'product' ",
      ('product','version','ALL','ALL'):" AND version = 'version' AND product = 'product' ",
      ('product','version','ALL','os_version'):" AND version = 'version' AND product = 'product' AND os_version = 'os_version' ",
      ('product','version','ALL','0.0.0 os_verison0'):" AND version = 'version' AND product = 'product' AND substr(os_version, 7, 11) = 'os_verison0' ",
      ('product','version','ALL','os_name os_versionn'):" AND version = 'version' AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product','version','ALL','os_name 0.0.0 os_version2'):" AND version = 'version' AND product = 'product' AND substr(os_version, 1, 7) = 'os_name' ",
      ('product','version','os_name',None):" AND version = 'version' AND product = 'product' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','version','os_name','ALL'):" AND version = 'version' AND product = 'product' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','version','os_name','os_version'):" AND version = 'version' AND product = 'product' AND os_version = 'os_version' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','version','os_name','0.0.0 os_verison0'):" AND version = 'version' AND product = 'product' AND substr(os_version, 7, 11) = 'os_verison0' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','version','os_name','os_name os_versionn'):" AND version = 'version' AND product = 'product' AND substr(os_version, 9, 11) = 'os_versionn' AND substr(os_name, 1, 3) = 'os_' ",
      ('product','version','os_name','os_name 0.0.0 os_version2'):" AND version = 'version' AND product = 'product' AND substr(os_version, 15, 11) = 'os_version2' AND substr(os_name, 1, 3) = 'os_' ",
    }
    got = {}
    for p in [None,'ALL','product']:
      for v in [None,'ALL','version']:
        for o in [None,'ALL','os_name']:
          for u in [None,'ALL','os_version','0.0.0 os_verison0','os_name os_versionn','os_name 0.0.0 os_version2']:
            product = {}
            if p: product['product'] = p
            if v: product['version'] = v
            if o: product['os_name'] = o
            if u: product['os_version'] = u
            got[(p,v,o,u)] = "%s"%(mtbf.getWhereClauseFor(product))
    if expected != got:
      assert len(expected) == len(got), 'Expected %s keys, but got %s'%(len(expected),len(got))
      for x in expected:
        assert expected[x] == got[x], 'for inputs %s\nexp: "%s"\ngot: "%s"'%(x,expected[x],got[x])
      for g in got:
        assert expected[g] == got[g], 'for inputs %s\nexp: "%s"\ngot: "%s"'%(x,expected[x],got[x])
      assert expected == got, 'You can NOT get here and see this line!'

  # ========================================================================== #  
  def testClassProductAndOsData(self):
    """
    testClassProductAndOsData(self):
       check that we handle config with correct or greater items in config
    """
    assert_raises(IndexError,mtbf.ProductAndOsData,[])
    assert_raises(IndexError,mtbf.ProductAndOsData,[1])
    assert_raises(IndexError,mtbf.ProductAndOsData,[1,2])
    assert_raises(IndexError,mtbf.ProductAndOsData,[1,2,3])
    #assert_raises(IndexError,mtbf.ProductAndOsData,[1,2,3,4]) 4 is a legal count
    assert_raises(IndexError,mtbf.ProductAndOsData,[1,2,3,4,5])
    assert_raises(IndexError,mtbf.ProductAndOsData,[1,2,3,4,5,6])
    self.logger.clear()
    config = [999,'umlaut',3.14,'lemme go',12,'oss','3.5.8','toomuch']
    pd = mtbf.ProductAndOsData(config,self.logger)
    assert 7 == len(pd), "Assure nobody adds another dimension element without updating tests"
    assert 999 == pd.product_id
    assert 'umlaut' == pd['product']
    assert 3.14 == pd.version
    assert 'lemme go' == pd['release']
    assert 12 == pd.os_id
    assert 'oss' == pd['os_name']
    assert '3.5.8' == pd.os_version
      
if __name__ == "__main__":
  unittest.main()
