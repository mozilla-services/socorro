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

  def fillMtbfTables(self,cursor):
    cursor.execute("SELECT p.id, p.product, p.version, p.release, o.id, o.os_name, o.os_version from productdims as p, osdims as o LIMIT 12")
    self.productDimData = cursor.fetchall()
    cursor.connection.commit()
    versionS = set([x[2] for x in self.productDimData])
    versions = [x for x in versionS]
    self.baseDate = datetime.date(2008,1,1)
    intervals = [(self.baseDate                        ,self.baseDate+datetime.timedelta(days=30)),
                 (self.baseDate + datetime.timedelta(days=10),self.baseDate + datetime.timedelta(days=40)),
                 (self.baseDate + datetime.timedelta(days=20),self.baseDate + datetime.timedelta(days=50)),
                 (self.baseDate + datetime.timedelta(days=10),self.baseDate + datetime.timedelta(days=40)),
                 (self.baseDate + datetime.timedelta(days=20),self.baseDate + datetime.timedelta(days=50)),
                 (self.baseDate + datetime.timedelta(days=30),self.baseDate + datetime.timedelta(days=60)),
                 (self.baseDate + datetime.timedelta(days=90),self.baseDate + datetime.timedelta(days=91)),
                 (self.baseDate + datetime.timedelta(days=90),self.baseDate + datetime.timedelta(days=91)),
                 ]
    assert len(versions) >= len(intervals), "Must add exactly %s versions to the productdims table"%(len(intervals)-len(versions))
    assert len(intervals) >= len(versions), "Must add exatly %s more intervals above"%(len(versions)-len(intervals))
    self.intervals = {}
    for x in range(len(intervals)):
      self.intervals[versions[x]] = intervals[x]

    PDindexes = [-1,0,5,10,15,25,35,45,55,60,61]
    productsInProcessingDay = [
      [], #  -1,
      [(1,1),(1,2)],#  0,
      [(1,1),(1,2)],#  5,
      [(1,1),(1,2),(4,1),(4,2),(5,1)],#  10,
      [(1,1),(1,2),(4,1),(4,2),(5,1)],#  15,
      [(1,1),(1,2),(4,1),(4,2),(5,1),(6,1),(8,1)],#  25,
      [(2,1),(2,2),(4,1),(4,2),(5,1),(6,1),(8,1)],#  35,
      [(2,1),(2,2),(6,1),(8,1)],#  45,
      [(2,1),(2,2)],#  55,
      [(2,1),(2,2)],#  60,
      [],#  61,
      ]
    # processing days are located at and beyond the extremes of the full range, and
    # at some interior points, midway between each pair of interior points
    # layout is: (a date, the day-offset from baseDate, the expected resulting [(prod_id,os_id)])
    self.processingDays = [ (self.baseDate+datetime.timedelta(days=PDindexes[x]),PDindexes[x],productsInProcessingDay[x]) for x in range(len(PDindexes))]
    
    # (id), productdims_id, osdims_id, start_dt, end_dt : Date-interval when product is interesting
    configData =[ (x[0],x[4],self.intervals[x[2]][0],self.intervals[x[2]][1] ) for x in self.productDimData ]
    cursor.executemany('insert into mtbfconfig (productdims_id,osdims_id,start_dt,end_dt) values(%s,%s,%s,%s)',configData)
    cursor.connection.commit()
    self.expectedNewFacts = {
      -1: [],
      0: [
      (7, datetime.date(2008, 1, 1), 35, 6),
      (5, datetime.date(2008, 1, 1), 25, 6),
      (3, datetime.date(2008, 1, 1), 15, 6),
      (8, datetime.date(2008, 1, 1), 40, 6),
      (3, datetime.date(2008, 1, 1), 55, 6),
      (1, datetime.date(2008, 1, 1), 5, 6),
      (2, datetime.date(2008, 1, 1), 10, 6),
      (4, datetime.date(2008, 1, 1), 20, 6),
      (1, datetime.date(2008, 1, 1), 45, 6),
      (2, datetime.date(2008, 1, 1), 50, 6),
      (4, datetime.date(2008, 1, 1), 60, 6),
      (6, datetime.date(2008, 1, 1), 30, 6),
      (7, datetime.date(2008, 1, 1), 35, 6),
      (5, datetime.date(2008, 1, 1), 25, 6),
      (3, datetime.date(2008, 1, 1), 15, 6),
      (8, datetime.date(2008, 1, 1), 40, 6),
      (3, datetime.date(2008, 1, 1), 55, 6),
      (1, datetime.date(2008, 1, 1), 5, 6),
      (2, datetime.date(2008, 1, 1), 10, 6),
      (4, datetime.date(2008, 1, 1), 20, 6),
      (1, datetime.date(2008, 1, 1), 45, 6),
      (2, datetime.date(2008, 1, 1), 50, 6),
      (4, datetime.date(2008, 1, 1), 60, 6),
      (6, datetime.date(2008, 1, 1), 30, 6),
      ],
      5: [
      (7, datetime.date(2008, 1, 6), 35, 6),
      (5, datetime.date(2008, 1, 6), 25, 6),
      (3, datetime.date(2008, 1, 6), 15, 6),
      (8, datetime.date(2008, 1, 6), 40, 6),
      (3, datetime.date(2008, 1, 6), 55, 6),
      (1, datetime.date(2008, 1, 6), 5, 6),
      (2, datetime.date(2008, 1, 6), 10, 6),
      (4, datetime.date(2008, 1, 6), 20, 6),
      (1, datetime.date(2008, 1, 6), 45, 6),
      (2, datetime.date(2008, 1, 6), 50, 6),
      (4, datetime.date(2008, 1, 6), 60, 6),
      (6, datetime.date(2008, 1, 6), 30, 6),
      (7, datetime.date(2008, 1, 6), 35, 6),
      (5, datetime.date(2008, 1, 6), 25, 6),
      (3, datetime.date(2008, 1, 6), 15, 6),
      (8, datetime.date(2008, 1, 6), 40, 6),
      (3, datetime.date(2008, 1, 6), 55, 6),
      (1, datetime.date(2008, 1, 6), 5, 6),
      (2, datetime.date(2008, 1, 6), 10, 6),
      (4, datetime.date(2008, 1, 6), 20, 6),
      (1, datetime.date(2008, 1, 6), 45, 6),
      (2, datetime.date(2008, 1, 6), 50, 6),
      (4, datetime.date(2008, 1, 6), 60, 6),
      (6, datetime.date(2008, 1, 6), 30, 6),
      ],
      10: [
      (7, datetime.date(2008, 1, 11), 35, 6),
      (5, datetime.date(2008, 1, 11), 25, 6),
      (3, datetime.date(2008, 1, 11), 15, 6),
      (8, datetime.date(2008, 1, 11), 40, 6),
      (3, datetime.date(2008, 1, 11), 55, 6),
      (1, datetime.date(2008, 1, 11), 5, 6),
      (2, datetime.date(2008, 1, 11), 10, 6),
      (4, datetime.date(2008, 1, 11), 20, 6),
      (1, datetime.date(2008, 1, 11), 45, 6),
      (2, datetime.date(2008, 1, 11), 50, 6),
      (4, datetime.date(2008, 1, 11), 60, 6),
      (6, datetime.date(2008, 1, 11), 30, 6),
      (7, datetime.date(2008, 1, 11), 35, 6),
      (5, datetime.date(2008, 1, 11), 25, 6),
      (3, datetime.date(2008, 1, 11), 15, 6),
      (8, datetime.date(2008, 1, 11), 40, 6),
      (3, datetime.date(2008, 1, 11), 55, 6),
      (1, datetime.date(2008, 1, 11), 5, 6),
      (2, datetime.date(2008, 1, 11), 10, 6),
      (4, datetime.date(2008, 1, 11), 20, 6),
      (1, datetime.date(2008, 1, 11), 45, 6),
      (2, datetime.date(2008, 1, 11), 50, 6),
      (4, datetime.date(2008, 1, 11), 60, 6),
      (6, datetime.date(2008, 1, 11), 30, 6),
      (7, datetime.date(2008, 1, 11), 35, 6),
      (5, datetime.date(2008, 1, 11), 25, 6),
      (3, datetime.date(2008, 1, 11), 15, 6),
      (8, datetime.date(2008, 1, 11), 40, 6),
      (3, datetime.date(2008, 1, 11), 55, 6),
      (1, datetime.date(2008, 1, 11), 5, 6),
      (2, datetime.date(2008, 1, 11), 10, 6),
      (4, datetime.date(2008, 1, 11), 20, 6),
      (1, datetime.date(2008, 1, 11), 45, 6),
      (2, datetime.date(2008, 1, 11), 50, 6),
      (4, datetime.date(2008, 1, 11), 60, 6),
      (6, datetime.date(2008, 1, 11), 30, 6),
      (7, datetime.date(2008, 1, 11), 35, 6),
      (5, datetime.date(2008, 1, 11), 25, 6),
      (3, datetime.date(2008, 1, 11), 15, 6),
      (8, datetime.date(2008, 1, 11), 40, 6),
      (3, datetime.date(2008, 1, 11), 55, 6),
      (1, datetime.date(2008, 1, 11), 5, 6),
      (2, datetime.date(2008, 1, 11), 10, 6),
      (4, datetime.date(2008, 1, 11), 20, 6),
      (1, datetime.date(2008, 1, 11), 45, 6),
      (2, datetime.date(2008, 1, 11), 50, 6),
      (4, datetime.date(2008, 1, 11), 60, 6),
      (6, datetime.date(2008, 1, 11), 30, 6),
      (7, datetime.date(2008, 1, 11), 35, 6),
      (5, datetime.date(2008, 1, 11), 25, 6),
      (3, datetime.date(2008, 1, 11), 15, 6),
      (8, datetime.date(2008, 1, 11), 40, 6),
      (3, datetime.date(2008, 1, 11), 55, 6),
      (1, datetime.date(2008, 1, 11), 5, 6),
      (2, datetime.date(2008, 1, 11), 10, 6),
      (4, datetime.date(2008, 1, 11), 20, 6),
      (1, datetime.date(2008, 1, 11), 45, 6),
      (2, datetime.date(2008, 1, 11), 50, 6),
      (4, datetime.date(2008, 1, 11), 60, 6),
      (6, datetime.date(2008, 1, 11), 30, 6),
      ],
      15: [
      (7, datetime.date(2008, 1, 16), 35, 6),
      (5, datetime.date(2008, 1, 16), 25, 6),
      (3, datetime.date(2008, 1, 16), 15, 6),
      (8, datetime.date(2008, 1, 16), 40, 6),
      (3, datetime.date(2008, 1, 16), 55, 6),
      (1, datetime.date(2008, 1, 16), 5, 6),
      (2, datetime.date(2008, 1, 16), 10, 6),
      (4, datetime.date(2008, 1, 16), 20, 6),
      (1, datetime.date(2008, 1, 16), 45, 6),
      (2, datetime.date(2008, 1, 16), 50, 6),
      (4, datetime.date(2008, 1, 16), 60, 6),
      (6, datetime.date(2008, 1, 16), 30, 6),
      (7, datetime.date(2008, 1, 16), 35, 6),
      (5, datetime.date(2008, 1, 16), 25, 6),
      (3, datetime.date(2008, 1, 16), 15, 6),
      (8, datetime.date(2008, 1, 16), 40, 6),
      (3, datetime.date(2008, 1, 16), 55, 6),
      (1, datetime.date(2008, 1, 16), 5, 6),
      (2, datetime.date(2008, 1, 16), 10, 6),
      (4, datetime.date(2008, 1, 16), 20, 6),
      (1, datetime.date(2008, 1, 16), 45, 6),
      (2, datetime.date(2008, 1, 16), 50, 6),
      (4, datetime.date(2008, 1, 16), 60, 6),
      (6, datetime.date(2008, 1, 16), 30, 6),
      (7, datetime.date(2008, 1, 16), 35, 6),
      (5, datetime.date(2008, 1, 16), 25, 6),
      (3, datetime.date(2008, 1, 16), 15, 6),
      (8, datetime.date(2008, 1, 16), 40, 6),
      (3, datetime.date(2008, 1, 16), 55, 6),
      (1, datetime.date(2008, 1, 16), 5, 6),
      (2, datetime.date(2008, 1, 16), 10, 6),
      (4, datetime.date(2008, 1, 16), 20, 6),
      (1, datetime.date(2008, 1, 16), 45, 6),
      (2, datetime.date(2008, 1, 16), 50, 6),
      (4, datetime.date(2008, 1, 16), 60, 6),
      (6, datetime.date(2008, 1, 16), 30, 6),
      (7, datetime.date(2008, 1, 16), 35, 6),
      (5, datetime.date(2008, 1, 16), 25, 6),
      (3, datetime.date(2008, 1, 16), 15, 6),
      (8, datetime.date(2008, 1, 16), 40, 6),
      (3, datetime.date(2008, 1, 16), 55, 6),
      (1, datetime.date(2008, 1, 16), 5, 6),
      (2, datetime.date(2008, 1, 16), 10, 6),
      (4, datetime.date(2008, 1, 16), 20, 6),
      (1, datetime.date(2008, 1, 16), 45, 6),
      (2, datetime.date(2008, 1, 16), 50, 6),
      (4, datetime.date(2008, 1, 16), 60, 6),
      (6, datetime.date(2008, 1, 16), 30, 6),
      (7, datetime.date(2008, 1, 16), 35, 6),
      (5, datetime.date(2008, 1, 16), 25, 6),
      (3, datetime.date(2008, 1, 16), 15, 6),
      (8, datetime.date(2008, 1, 16), 40, 6),
      (3, datetime.date(2008, 1, 16), 55, 6),
      (1, datetime.date(2008, 1, 16), 5, 6),
      (2, datetime.date(2008, 1, 16), 10, 6),
      (4, datetime.date(2008, 1, 16), 20, 6),
      (1, datetime.date(2008, 1, 16), 45, 6),
      (2, datetime.date(2008, 1, 16), 50, 6),
      (4, datetime.date(2008, 1, 16), 60, 6),
      (6, datetime.date(2008, 1, 16), 30, 6),
      ],
      25: [
      (7, datetime.date(2008, 1, 26), 35, 6),
      (5, datetime.date(2008, 1, 26), 25, 6),
      (3, datetime.date(2008, 1, 26), 15, 6),
      (8, datetime.date(2008, 1, 26), 40, 6),
      (3, datetime.date(2008, 1, 26), 55, 6),
      (1, datetime.date(2008, 1, 26), 5, 6),
      (2, datetime.date(2008, 1, 26), 10, 6),
      (4, datetime.date(2008, 1, 26), 20, 6),
      (1, datetime.date(2008, 1, 26), 45, 6),
      (2, datetime.date(2008, 1, 26), 50, 6),
      (4, datetime.date(2008, 1, 26), 60, 6),
      (6, datetime.date(2008, 1, 26), 30, 6),
      (7, datetime.date(2008, 1, 26), 35, 6),
      (5, datetime.date(2008, 1, 26), 25, 6),
      (3, datetime.date(2008, 1, 26), 15, 6),
      (8, datetime.date(2008, 1, 26), 40, 6),
      (3, datetime.date(2008, 1, 26), 55, 6),
      (1, datetime.date(2008, 1, 26), 5, 6),
      (2, datetime.date(2008, 1, 26), 10, 6),
      (4, datetime.date(2008, 1, 26), 20, 6),
      (1, datetime.date(2008, 1, 26), 45, 6),
      (2, datetime.date(2008, 1, 26), 50, 6),
      (4, datetime.date(2008, 1, 26), 60, 6),
      (6, datetime.date(2008, 1, 26), 30, 6),
      (7, datetime.date(2008, 1, 26), 35, 6),
      (5, datetime.date(2008, 1, 26), 25, 6),
      (3, datetime.date(2008, 1, 26), 15, 6),
      (8, datetime.date(2008, 1, 26), 40, 6),
      (3, datetime.date(2008, 1, 26), 55, 6),
      (1, datetime.date(2008, 1, 26), 5, 6),
      (2, datetime.date(2008, 1, 26), 10, 6),
      (4, datetime.date(2008, 1, 26), 20, 6),
      (1, datetime.date(2008, 1, 26), 45, 6),
      (2, datetime.date(2008, 1, 26), 50, 6),
      (4, datetime.date(2008, 1, 26), 60, 6),
      (6, datetime.date(2008, 1, 26), 30, 6),
      (7, datetime.date(2008, 1, 26), 35, 6),
      (5, datetime.date(2008, 1, 26), 25, 6),
      (3, datetime.date(2008, 1, 26), 15, 6),
      (8, datetime.date(2008, 1, 26), 40, 6),
      (3, datetime.date(2008, 1, 26), 55, 6),
      (1, datetime.date(2008, 1, 26), 5, 6),
      (2, datetime.date(2008, 1, 26), 10, 6),
      (4, datetime.date(2008, 1, 26), 20, 6),
      (1, datetime.date(2008, 1, 26), 45, 6),
      (2, datetime.date(2008, 1, 26), 50, 6),
      (4, datetime.date(2008, 1, 26), 60, 6),
      (6, datetime.date(2008, 1, 26), 30, 6),
      (7, datetime.date(2008, 1, 26), 35, 6),
      (5, datetime.date(2008, 1, 26), 25, 6),
      (3, datetime.date(2008, 1, 26), 15, 6),
      (8, datetime.date(2008, 1, 26), 40, 6),
      (3, datetime.date(2008, 1, 26), 55, 6),
      (1, datetime.date(2008, 1, 26), 5, 6),
      (2, datetime.date(2008, 1, 26), 10, 6),
      (4, datetime.date(2008, 1, 26), 20, 6),
      (1, datetime.date(2008, 1, 26), 45, 6),
      (2, datetime.date(2008, 1, 26), 50, 6),
      (4, datetime.date(2008, 1, 26), 60, 6),
      (6, datetime.date(2008, 1, 26), 30, 6),
      (7, datetime.date(2008, 1, 26), 35, 6),
      (5, datetime.date(2008, 1, 26), 25, 6),
      (3, datetime.date(2008, 1, 26), 15, 6),
      (8, datetime.date(2008, 1, 26), 40, 6),
      (3, datetime.date(2008, 1, 26), 55, 6),
      (1, datetime.date(2008, 1, 26), 5, 6),
      (2, datetime.date(2008, 1, 26), 10, 6),
      (4, datetime.date(2008, 1, 26), 20, 6),
      (1, datetime.date(2008, 1, 26), 45, 6),
      (2, datetime.date(2008, 1, 26), 50, 6),
      (4, datetime.date(2008, 1, 26), 60, 6),
      (6, datetime.date(2008, 1, 26), 30, 6),
      (7, datetime.date(2008, 1, 26), 35, 6),
      (5, datetime.date(2008, 1, 26), 25, 6),
      (3, datetime.date(2008, 1, 26), 15, 6),
      (8, datetime.date(2008, 1, 26), 40, 6),
      (3, datetime.date(2008, 1, 26), 55, 6),
      (1, datetime.date(2008, 1, 26), 5, 6),
      (2, datetime.date(2008, 1, 26), 10, 6),
      (4, datetime.date(2008, 1, 26), 20, 6),
      (1, datetime.date(2008, 1, 26), 45, 6),
      (2, datetime.date(2008, 1, 26), 50, 6),
      (4, datetime.date(2008, 1, 26), 60, 6),
      (6, datetime.date(2008, 1, 26), 30, 6),
      ],
      35: [
      (7, datetime.date(2008, 2, 5), 35, 6),
      (5, datetime.date(2008, 2, 5), 25, 6),
      (3, datetime.date(2008, 2, 5), 15, 6),
      (8, datetime.date(2008, 2, 5), 40, 6),
      (3, datetime.date(2008, 2, 5), 55, 6),
      (1, datetime.date(2008, 2, 5), 5, 6),
      (2, datetime.date(2008, 2, 5), 10, 6),
      (4, datetime.date(2008, 2, 5), 20, 6),
      (1, datetime.date(2008, 2, 5), 45, 6),
      (2, datetime.date(2008, 2, 5), 50, 6),
      (4, datetime.date(2008, 2, 5), 60, 6),
      (6, datetime.date(2008, 2, 5), 30, 6),
      (7, datetime.date(2008, 2, 5), 35, 6),
      (5, datetime.date(2008, 2, 5), 25, 6),
      (3, datetime.date(2008, 2, 5), 15, 6),
      (8, datetime.date(2008, 2, 5), 40, 6),
      (3, datetime.date(2008, 2, 5), 55, 6),
      (1, datetime.date(2008, 2, 5), 5, 6),
      (2, datetime.date(2008, 2, 5), 10, 6),
      (4, datetime.date(2008, 2, 5), 20, 6),
      (1, datetime.date(2008, 2, 5), 45, 6),
      (2, datetime.date(2008, 2, 5), 50, 6),
      (4, datetime.date(2008, 2, 5), 60, 6),
      (6, datetime.date(2008, 2, 5), 30, 6),
      (7, datetime.date(2008, 2, 5), 35, 6),
      (5, datetime.date(2008, 2, 5), 25, 6),
      (3, datetime.date(2008, 2, 5), 15, 6),
      (8, datetime.date(2008, 2, 5), 40, 6),
      (3, datetime.date(2008, 2, 5), 55, 6),
      (1, datetime.date(2008, 2, 5), 5, 6),
      (2, datetime.date(2008, 2, 5), 10, 6),
      (4, datetime.date(2008, 2, 5), 20, 6),
      (1, datetime.date(2008, 2, 5), 45, 6),
      (2, datetime.date(2008, 2, 5), 50, 6),
      (4, datetime.date(2008, 2, 5), 60, 6),
      (6, datetime.date(2008, 2, 5), 30, 6),
      (7, datetime.date(2008, 2, 5), 35, 6),
      (5, datetime.date(2008, 2, 5), 25, 6),
      (3, datetime.date(2008, 2, 5), 15, 6),
      (8, datetime.date(2008, 2, 5), 40, 6),
      (3, datetime.date(2008, 2, 5), 55, 6),
      (1, datetime.date(2008, 2, 5), 5, 6),
      (2, datetime.date(2008, 2, 5), 10, 6),
      (4, datetime.date(2008, 2, 5), 20, 6),
      (1, datetime.date(2008, 2, 5), 45, 6),
      (2, datetime.date(2008, 2, 5), 50, 6),
      (4, datetime.date(2008, 2, 5), 60, 6),
      (6, datetime.date(2008, 2, 5), 30, 6),
      (7, datetime.date(2008, 2, 5), 35, 6),
      (5, datetime.date(2008, 2, 5), 25, 6),
      (3, datetime.date(2008, 2, 5), 15, 6),
      (8, datetime.date(2008, 2, 5), 40, 6),
      (3, datetime.date(2008, 2, 5), 55, 6),
      (1, datetime.date(2008, 2, 5), 5, 6),
      (2, datetime.date(2008, 2, 5), 10, 6),
      (4, datetime.date(2008, 2, 5), 20, 6),
      (1, datetime.date(2008, 2, 5), 45, 6),
      (2, datetime.date(2008, 2, 5), 50, 6),
      (4, datetime.date(2008, 2, 5), 60, 6),
      (6, datetime.date(2008, 2, 5), 30, 6),
      (7, datetime.date(2008, 2, 5), 35, 6),
      (5, datetime.date(2008, 2, 5), 25, 6),
      (3, datetime.date(2008, 2, 5), 15, 6),
      (8, datetime.date(2008, 2, 5), 40, 6),
      (3, datetime.date(2008, 2, 5), 55, 6),
      (1, datetime.date(2008, 2, 5), 5, 6),
      (2, datetime.date(2008, 2, 5), 10, 6),
      (4, datetime.date(2008, 2, 5), 20, 6),
      (1, datetime.date(2008, 2, 5), 45, 6),
      (2, datetime.date(2008, 2, 5), 50, 6),
      (4, datetime.date(2008, 2, 5), 60, 6),
      (6, datetime.date(2008, 2, 5), 30, 6),
      (7, datetime.date(2008, 2, 5), 35, 6),
      (5, datetime.date(2008, 2, 5), 25, 6),
      (3, datetime.date(2008, 2, 5), 15, 6),
      (8, datetime.date(2008, 2, 5), 40, 6),
      (3, datetime.date(2008, 2, 5), 55, 6),
      (1, datetime.date(2008, 2, 5), 5, 6),
      (2, datetime.date(2008, 2, 5), 10, 6),
      (4, datetime.date(2008, 2, 5), 20, 6),
      (1, datetime.date(2008, 2, 5), 45, 6),
      (2, datetime.date(2008, 2, 5), 50, 6),
      (4, datetime.date(2008, 2, 5), 60, 6),
      (6, datetime.date(2008, 2, 5), 30, 6),
      ],
      45: [
      (7, datetime.date(2008, 2, 15), 35, 6),
      (5, datetime.date(2008, 2, 15), 25, 6),
      (3, datetime.date(2008, 2, 15), 15, 6),
      (8, datetime.date(2008, 2, 15), 40, 6),
      (3, datetime.date(2008, 2, 15), 55, 6),
      (1, datetime.date(2008, 2, 15), 5, 6),
      (2, datetime.date(2008, 2, 15), 10, 6),
      (4, datetime.date(2008, 2, 15), 20, 6),
      (1, datetime.date(2008, 2, 15), 45, 6),
      (2, datetime.date(2008, 2, 15), 50, 6),
      (4, datetime.date(2008, 2, 15), 60, 6),
      (6, datetime.date(2008, 2, 15), 30, 6),
      (7, datetime.date(2008, 2, 15), 35, 6),
      (5, datetime.date(2008, 2, 15), 25, 6),
      (3, datetime.date(2008, 2, 15), 15, 6),
      (8, datetime.date(2008, 2, 15), 40, 6),
      (3, datetime.date(2008, 2, 15), 55, 6),
      (1, datetime.date(2008, 2, 15), 5, 6),
      (2, datetime.date(2008, 2, 15), 10, 6),
      (4, datetime.date(2008, 2, 15), 20, 6),
      (1, datetime.date(2008, 2, 15), 45, 6),
      (2, datetime.date(2008, 2, 15), 50, 6),
      (4, datetime.date(2008, 2, 15), 60, 6),
      (6, datetime.date(2008, 2, 15), 30, 6),
      (7, datetime.date(2008, 2, 15), 35, 6),
      (5, datetime.date(2008, 2, 15), 25, 6),
      (3, datetime.date(2008, 2, 15), 15, 6),
      (8, datetime.date(2008, 2, 15), 40, 6),
      (3, datetime.date(2008, 2, 15), 55, 6),
      (1, datetime.date(2008, 2, 15), 5, 6),
      (2, datetime.date(2008, 2, 15), 10, 6),
      (4, datetime.date(2008, 2, 15), 20, 6),
      (1, datetime.date(2008, 2, 15), 45, 6),
      (2, datetime.date(2008, 2, 15), 50, 6),
      (4, datetime.date(2008, 2, 15), 60, 6),
      (6, datetime.date(2008, 2, 15), 30, 6),
      (7, datetime.date(2008, 2, 15), 35, 6),
      (5, datetime.date(2008, 2, 15), 25, 6),
      (3, datetime.date(2008, 2, 15), 15, 6),
      (8, datetime.date(2008, 2, 15), 40, 6),
      (3, datetime.date(2008, 2, 15), 55, 6),
      (1, datetime.date(2008, 2, 15), 5, 6),
      (2, datetime.date(2008, 2, 15), 10, 6),
      (4, datetime.date(2008, 2, 15), 20, 6),
      (1, datetime.date(2008, 2, 15), 45, 6),
      (2, datetime.date(2008, 2, 15), 50, 6),
      (4, datetime.date(2008, 2, 15), 60, 6),
      (6, datetime.date(2008, 2, 15), 30, 6),
      ],
      55: [
      (7, datetime.date(2008, 2, 25), 35, 6),
      (5, datetime.date(2008, 2, 25), 25, 6),
      (3, datetime.date(2008, 2, 25), 15, 6),
      (8, datetime.date(2008, 2, 25), 40, 6),
      (3, datetime.date(2008, 2, 25), 55, 6),
      (1, datetime.date(2008, 2, 25), 5, 6),
      (2, datetime.date(2008, 2, 25), 10, 6),
      (4, datetime.date(2008, 2, 25), 20, 6),
      (1, datetime.date(2008, 2, 25), 45, 6),
      (2, datetime.date(2008, 2, 25), 50, 6),
      (4, datetime.date(2008, 2, 25), 60, 6),
      (6, datetime.date(2008, 2, 25), 30, 6),
      (7, datetime.date(2008, 2, 25), 35, 6),
      (5, datetime.date(2008, 2, 25), 25, 6),
      (3, datetime.date(2008, 2, 25), 15, 6),
      (8, datetime.date(2008, 2, 25), 40, 6),
      (3, datetime.date(2008, 2, 25), 55, 6),
      (1, datetime.date(2008, 2, 25), 5, 6),
      (2, datetime.date(2008, 2, 25), 10, 6),
      (4, datetime.date(2008, 2, 25), 20, 6),
      (1, datetime.date(2008, 2, 25), 45, 6),
      (2, datetime.date(2008, 2, 25), 50, 6),
      (4, datetime.date(2008, 2, 25), 60, 6),
      (6, datetime.date(2008, 2, 25), 30, 6),
      ],
      60: [
      (7, datetime.date(2008, 3, 1), 35, 6),
      (5, datetime.date(2008, 3, 1), 25, 6),
      (3, datetime.date(2008, 3, 1), 15, 6),
      (8, datetime.date(2008, 3, 1), 40, 6),
      (3, datetime.date(2008, 3, 1), 55, 6),
      (1, datetime.date(2008, 3, 1), 5, 6),
      (2, datetime.date(2008, 3, 1), 10, 6),
      (4, datetime.date(2008, 3, 1), 20, 6),
      (1, datetime.date(2008, 3, 1), 45, 6),
      (2, datetime.date(2008, 3, 1), 50, 6),
      (4, datetime.date(2008, 3, 1), 60, 6),
      (6, datetime.date(2008, 3, 1), 30, 6),
      (7, datetime.date(2008, 3, 1), 35, 6),
      (5, datetime.date(2008, 3, 1), 25, 6),
      (3, datetime.date(2008, 3, 1), 15, 6),
      (8, datetime.date(2008, 3, 1), 40, 6),
      (3, datetime.date(2008, 3, 1), 55, 6),
      (1, datetime.date(2008, 3, 1), 5, 6),
      (2, datetime.date(2008, 3, 1), 10, 6),
      (4, datetime.date(2008, 3, 1), 20, 6),
      (1, datetime.date(2008, 3, 1), 45, 6),
      (2, datetime.date(2008, 3, 1), 50, 6),
      (4, datetime.date(2008, 3, 1), 60, 6),
      (6, datetime.date(2008, 3, 1), 30, 6),
      ],
      61: [],
      }
    self.expectedFacts = {
      # key is offset from baseDate
      # value is array of (productdims_id,day,avg_seconds,report_count,count(distinct(user)))
      # This data WAS NOT CALCULATED BY HAND: The test was run once with prints in place
      # and that output was encoded here. As of 2009-Feb, count of unique users is always 0
      -1: [],
      0: [
      (1, datetime.date(2008,1,1), 5, 6, 0),
      (4, datetime.date(2008,1,1), 20, 6, 0),
      ],
      5: [
      (1, datetime.date(2008,1,6), 5, 6, 0),
      (4, datetime.date(2008,1,6), 20, 6, 0),
      ],
      10: [
      (1, datetime.date(2008,1,11), 5, 6, 0),
      (2, datetime.date(2008,1,11), 10, 6, 0),
      (4, datetime.date(2008,1,11), 20, 6, 0),
      (5, datetime.date(2008,1,11), 25, 6, 0),
      (7, datetime.date(2008,1,11), 35, 6, 0),
      (10, datetime.date(2008,1,11), 50, 6, 0),
      ],
      15: [
      (1, datetime.date(2008,1,16), 5, 6, 0),
      (2, datetime.date(2008,1,16), 10, 6, 0),
      (4, datetime.date(2008,1,16), 20, 6, 0),
      (5, datetime.date(2008,1,16), 25, 6, 0),
      (7, datetime.date(2008,1,16), 35, 6, 0),
      (10, datetime.date(2008,1,16), 50, 6, 0),
      ],
      25: [
      (1, datetime.date(2008,1,26), 5, 6, 0),
      (2, datetime.date(2008,1,26), 10, 6, 0),
      (3, datetime.date(2008,1,26), 15, 6, 0),
      (4, datetime.date(2008,1,26), 20, 6, 0),
      (5, datetime.date(2008,1,26), 25, 6, 0),
      (6, datetime.date(2008,1,26), 30, 6, 0),
      (7, datetime.date(2008,1,26), 35, 6, 0),
      (8, datetime.date(2008,1,26), 40, 6, 0),
      (10, datetime.date(2008,1,26), 50, 6, 0),
      (11, datetime.date(2008,1,26), 55, 6, 0),
      ],
      35: [
      (2, datetime.date(2008,2,5), 10, 6, 0),
      (3, datetime.date(2008,2,5), 15, 6, 0),
      (5, datetime.date(2008,2,5), 25, 6, 0),
      (6, datetime.date(2008,2,5), 30, 6, 0),
      (7, datetime.date(2008,2,5), 35, 6, 0),
      (8, datetime.date(2008,2,5), 40, 6, 0),
      (9, datetime.date(2008,2,5), 45, 6, 0),
      (10, datetime.date(2008,2,5), 50, 6, 0),
      (11, datetime.date(2008,2,5), 55, 6, 0),
      (12, datetime.date(2008,2,5), 60, 6, 0),
      ],
      45: [
      (3, datetime.date(2008,2,15), 15, 6, 0),
      (6, datetime.date(2008,2,15), 30, 6, 0),
      (8, datetime.date(2008,2,15), 40, 6, 0),
      (9, datetime.date(2008,2,15), 45, 6, 0),
      (11, datetime.date(2008,2,15), 55, 6, 0),
      (12, datetime.date(2008,2,15), 60, 6, 0),
      ],
      55: [
      (9, datetime.date(2008,2,25), 45, 6, 0),
      (12, datetime.date(2008,2,25), 60, 6, 0),
      ],
      60: [
      (9, datetime.date(2008,3,1), 45, 6, 0),
      (12, datetime.date(2008,3,1), 60, 6, 0),
      ],
      61: [],
      }

  def fillReports(self,cursor):
    """fill enough data to test mtbf behavior:
       - AVG(uptime); COUNT(date_processed); COUNT(DISTINCT(user_id))
    """
    self.fillMtbfTables(cursor) # prime the pump
    sql2 = """INSERT INTO crash_reports
                (uuid, client_crash_date, install_age, last_crash, uptime, date_processed, success, signaturedims_id, productdims_id, osdims_id)
          VALUES(%s,   %s,                %s,          %s,         %s,     %s,             %s,      %s,               %s,             %s)"""
    processTimes = ['00:00:00','05:00:00','10:00:00','15:00:00','20:00:00','23:59:59']
    crashTimes =   ['00:00:00','04:59:40','9:55:00', '14:55:55','19:59:59','23:59:50']
    assert len(processTimes) == len(crashTimes), 'Otherwise things get way too weird'
    uptimes = [5*x for x in range(1,15)]
    data = []
    data2 = []
    uuidGen = dbtestutil.moreUuid()
    uptimeIndex = 0
    for product in self.productDimData:
      uptime = uptimes[uptimeIndex%len(uptimes)]
      uptimeIndex += 1
      for d,off,ig in self.processingDays:
        for ptIndex in range(len(processTimes)):
          pt = processTimes[ptIndex]
          ct = crashTimes[ptIndex]
          dp = "%s %s"%(d.isoformat(),pt)
          ccd = "%s %s"%(d.isoformat(),ct)
          tup = (uuidGen.next(), uptime,dp,product[1],product[2],product[5],product[6])
          # Use ptIndex as signaturedims_id
          tup2 = (tup[0], ccd, 10000, 100, uptime, dp, True, ptIndex+1, product[0], product[4])
          data.append(tup)
          data2.append(tup2)
    cursor.executemany(sql2,data2)

  # ========================================================================== #  
  def testCalculateMtbf(self):
    """
    testCalculateMtbf(self): slow(1)
      check that we get the expected data. This is NOT hand-calculated, just a regression check
    """
    cursor = self.connection.cursor()
    self.fillReports(cursor)
    self.connection.commit()
    sql = "SELECT productdims_id,day,avg_seconds,report_count FROM mtbffacts WHERE day = %s"
    for pd in self.processingDays:
      self.config.processingDay = pd[0].isoformat()
      mtbf.calculateMtbf(self.config, self.logger)
      cursor.execute(sql,(pd[0].isoformat(),))
      data = cursor.fetchall()
      self.connection.commit()
      expected = set(self.expectedFacts[pd[1]])
      got = set(data)
      if not expected == got:
        expected = set(self.expectedNewFacts[pd[1]])
        if not expected == got:
          assert len(expected) == len(got), 'Except\n%s\n%s'%(expected,got)
          for x in expected:
            assert x in got, 'Except %s was not gotten: %s'%(x,got)
          for g in got:
            assert g in expected, 'Except %s was got, not expected : %s'%(g,expected)
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
        assert logging.WARNING == self.logger.levels[-1]
        assert 'Currently there are no MTBF products configured' == self.logger.buffer[-1]
      else:
        pass # testing for expected log calls is sorta kinda stupid. 
      pids = set([(x['product_id'],x['os_id']) for x in products])
      expected = set(d[2])
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
    assert_raises(IndexError,mtbf.ProductAndOsData,[1,2,3,4])
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
