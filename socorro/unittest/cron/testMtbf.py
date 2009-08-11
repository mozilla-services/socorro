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
for i in dir(testConfig):
  print "CONFIG",i,type(i)

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
      mtbf.processOneMtbfWindow(self.config, self.logger)
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
      check that start/endWindow beats processingDay
      check that kwargs start/endWindow beats config
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
    self.config['processingDay'] = self.processingDays[3][0].isoformat()
    assert self.processingDays[3][0] != pd[0]
    cursor.execute(sql,(pdtS,))
    self.connection.commit()
    assert [] == cursor.fetchall(), 'Better be empty before we start mucking about'
    # override the day
    mtbf.processOneMtbfWindow(self.config,self.logger,processingDay=pd[0].isoformat())
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
      mtbf.processOneMtbfWindow(self.config,self.logger,**testItem)
      cursor.execute('SELECT f.window_end, p.product,p.version,o.os_name,o.os_version FROM time_before_failure f JOIN productdims p ON f.productdims_id = p.id JOIN osdims o ON f.osdims_id = o.id')
      self.connection.rollback() # select needs no commit
      got = cursor.fetchall()
      assert set(testItem.get('expected')) == set(got),"%s\nEX: %s\nGOT %s"%(self.whichProduct(testItem),testItem.get('expected'),got)
#       print "EXP: %s, GOT: %s"%(len(testItem.get('expected')), len(set(got)))
#       if not len(testItem.get('expected')) == len(set(got)):
#         print "OOPS "*5,self.whichProduct(testItem)
#         print "GOT - EXPECTED:",set(got)-set(testItem.get('expected'))
#         print "EXPECTED - GOT:",set(testItem.get('expected'))-set(got)

    #check that start/endWindow beats processingDay
    goodProcessingDay = self.processingDays[4][0]
    goodEndWindow = goodProcessingDay+datetime.timedelta(days=1)
    badProcessingDay = datetime.datetime(2000,11,12,0,0,0) # well outside useful range
    self.config['processingDay'] = goodProcessingDay.isoformat()
    self.config['endWindow'] = badProcessingDay.isoformat()
    self.config['startWindow'] = (badProcessingDay-datetime.timedelta(days=1)).isoformat()
    cursor.execute(delSql)
    self.connection.commit()
    mtbf.processOneMtbfWindow(self.config,self.logger)
    self.connection.commit()
    cursor.execute('select count(id) from time_before_failure')
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 0 == count, 'Expect no data from year 2000, but %s'%(count)

    #check that kwargs endWindow beats config
    cursor.execute(delSql)
    self.connection.commit()
    self.config['endWindow'] = badProcessingDay.isoformat()
    self.config['startWindow'] = (badProcessingDay-datetime.timedelta(days=1)).isoformat()
    mtbf.processOneMtbfWindow(self.config,self.logger,endWindow=goodEndWindow,startWindow=goodEndWindow-datetime.timedelta(days=1))
    self.connection.commit()
    cursor.execute('select count(id) from time_before_failure')
    self.connection.commit()
    count = cursor.fetchone()[0]
    assert 13 == count, 'Expect 13 rows from this good day, but got %s'%count
    
    #check that deltaWindow beats the default 1 day
    cursor.execute("SELECT SUM(sum_uptime_seconds) from time_before_failure")
    self.connection.commit()
    fullDaySum = cursor.fetchone()[0]
    cursor.execute(delSql)
    self.connection.commit()
    del self.config['startWindow']
    mtbf.processOneMtbfWindow(self.config,self.logger,endWindow=goodEndWindow,deltaWindow=datetime.timedelta(seconds=360),show=True)
    self.connection.commit()
    cursor.execute("SELECT SUM(sum_uptime_seconds) from time_before_failure")
    self.connection.commit()
    partDaySum = cursor.fetchone()[0]
    assert partDaySum < fullDaySum, 'Actually, expect full:2730 (got %s) , partial:455 (got %s)'%(fullDaySum,partDaySum)

  # ========================================================================== #  
  def testDateInterval(self):
    """
    TestMtbf.testProcessDateInterval(self):
    check that we get the expected results from various intervals. This is JUST a regression test
    """
    cursor = self.connection.cursor()
    self.fillMtbfTables(cursor,limit=33)
    self.fillReports(cursor, False)
    self.connection.commit()
    sql = "SELECT count(id) FROM time_before_failure"
    delSql = 'DELETE from time_before_failure'

    deltaDay = datetime.timedelta(days=1)
    testIntervals = [
      (self.processingDays[0][0]-(3*deltaDay),self.processingDays[0][0],0),
      (self.processingDays[0][0]-(3*deltaDay),self.processingDays[1][0],0),
      (self.processingDays[0][0],self.processingDays[1][0],0),
      (self.processingDays[0][0],self.processingDays[2][0],0),
      (self.processingDays[0][0],self.processingDays[3][0],0),
      (),
      (),
     ]
    for j in testIntervals:
      if not j: continue
      cursor.execute(delSql)
      self.connection.commit()
      mtbf.processDateInterval(self.config,self.logger,startDate=j[0],endDate=j[1])
      cursor.execute(sql)
      self.connection.rollback()
    
if __name__ == "__main__":
  unittest.main()
