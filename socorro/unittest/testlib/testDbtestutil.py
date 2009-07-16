import socorro.unittest.testlib.dbtestutil as dbtu

import socorro.lib.psycopghelper as psycopghelper
import socorro.lib.ConfigurationManager as configurationManager
import socorro.database.postgresql as db_postgresql
import socorro.database.schema as db_schema

from nose.tools import *
from socorro.unittest.testlib.testDB import TestDB
import libTestconfig as testConfig
import socorro.unittest.testlib.createJsonDumpStore as createJDS
import socorro.unittest.testlib.util as tutil

import psycopg2

import datetime as dt
import errno
import logging
import os
import re
import time

logger = logging.getLogger()

class Me():
  pass
me = None

def setup_module():
  global me
  if me:
    return
  me = Me()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing dbtestutil')
  tutil.nosePrintModule(__file__)
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass

  logger.setLevel(logging.DEBUG)
  logFilePathname = me.config.logFilePathname
  logfileDir = os.path.split(me.config.logFilePathname)[0]
  try:
    os.makedirs(logfileDir)
  except OSError,x:
    if errno.EEXIST != x.errno: raise
  f = open(me.config.logFilePathname,'w')
  f.close()

  fileLog = logging.FileHandler(logFilePathname, 'a')
  fileLog.setLevel(logging.DEBUG)
  fileLogFormatter = logging.Formatter(me.config.logFileLineFormatString)
  fileLog.setFormatter(fileLogFormatter)
  logger.addHandler(fileLog)
  me.dsn = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % (me.config)
  me.connection = psycopg2.connect(me.dsn)
  me.testDB = TestDB()
  me.testDB.removeDB(me.config,logger)
  me.testDB.createDB(me.config,logger)
  
def teardown_module():
  me.testDB.removeDB(me.config,logger)
  me.connection.close()

def testDatetimeNow():
  global me
  cursor = me.connection.cursor()
  before = dt.datetime.now()
  time.sleep(.01)
  got = dbtu.datetimeNow(cursor)
  time.sleep(.01)
  after = dt.datetime.now()
  assert before < got and got < after, "but\nbefore:%s\ngot:   %s\nafter: %s"%(before,got,after)

def testFillProcessorTable_NoMap():
  """ testDbtestutil:testFillProcessorTable_NoMap():
  - check correct behavior for presence or absence of parameter 'stamp'
  - check correct number of entries created
  - check correct number of priority_job_X tables created
  """
  global me
  cursor = me.connection.cursor()
  ssql = "SELECT id,name,startdatetime,lastseendatetime FROM processors"
  dsql = "DELETE FROM processors"
  dropSql = "DROP TABLE IF EXISTS %s"
  stamps = [None,None,dt.datetime(2008,1,2,3,4,5,666),dt.datetime(2009,1,2,3), None, dt.datetime(2010,12,11,10,9,8,777)]
  try:
    for i in range(len(stamps)):
      before = dt.datetime.now()
      time.sleep(.01)
      dbtu.fillProcessorTable(cursor,i,stamp=stamps[i])
      time.sleep(.01)
      after =  dt.datetime.now()
      cursor.execute(ssql)
      data = cursor.fetchall()
      assert i == len(data)
      for d in data:
        if stamps[i]:
          assert stamps[i] == d[2]
          assert stamps[i] == d[3]
        else:
          assert before < d[2] and d[2] < after
          assert d[2] == d[3]
      priJobsTables = db_postgresql.tablesMatchingPattern("priority_jobs_%",cursor)
      assert i == len(priJobsTables)
      cursor.execute(dsql)
      if priJobsTables:
        cursor.execute(dropSql%(','.join(priJobsTables)))
      me.connection.commit()
  finally:
    pt = db_schema.ProcessorsTable(logger)
    pt.drop(cursor)
    pt.create(cursor)
    cursor.execute('DELETE FROM jobs')
    me.connection.commit()

def testFillProcessorTable_WithMap():
  """testDbtestutil:testFillProcessorTable_WithMap():
  - check that othr params ignored for non-empty map
  - check that mapped data is used correctly (id is ignored, mapped stamp is lastseendatetime)
  """
  global me
  cursor = me.connection.cursor()
  ssql = "SELECT id,name,startdatetime,lastseendatetime FROM processors"
  dsql = "DELETE FROM processors"
  dropSql = "DROP TABLE IF EXISTS %s"
  tmap = {12:dt.datetime(2008,3,4,5,6,12),37:dt.datetime(2009,5,6,7,8,37)}
  try:
    dbtu.fillProcessorTable(cursor,7,stamp=dt.datetime(2009,4,5,6,7),processorMap=tmap)
    cursor.execute(ssql)
    data = cursor.fetchall()
    me.connection.commit()
    assert 2 == len(data)
    expectSet = set([dt.datetime(2008,3,4,5,6,12),dt.datetime(2009,5,6,7,8,37)])
    gotSet = set()
    for d in data:
      assert dt.datetime(2009,4,5,6,7) == d[2]
      gotSet.add(d[3])
      assert d[0] in [1,2]
    assert expectSet == gotSet
  finally:
    pt = db_schema.ProcessorsTable(logger)
    pt.drop(cursor)
    pt.create(cursor)
    cursor.execute('DELETE FROM jobs')
    me.connection.commit()
  
def testMoreUuid():
  m = {'hexD':'[0-9a-fA-F]'}
  p = '^%(hexD)s{8}-%(hexD)s{4}-%(hexD)s{4}-%(hexD)s{4}-%(hexD)s{12}$'%m
  rep = re.compile(p)
  gen = dbtu.moreUuid()
  seen = set()
  # surely no test set has more than 150K uuids... and we want to run in < 1 second
  for i in range(150000): 
    d = gen.next()
    assert 36 == len(d)
    assert d not in seen
    assert rep.match(d)
    seen.add(d)

def _makeJobDetails(aMap):
  "This is a test, but it is also a setup for the next test, so it will run there, not alone"
  jdCount = {1:0,2:0,3:0,4:0}
  data = dbtu.makeJobDetails(aMap)
  for d in data:
    jdCount[d[2]] += 1
    assert '/' in d[0]
    assert d[1] in d[0]
  assert jdCount == aMap
  return data

def testAddSomeJobs():
  global me
  cursor = me.connection.cursor()
  cursor.execute("SELECT id from processors")
  me.connection.commit()
  jdMap = {1:1,2:2,3:3,4:0}
  xdMap = {1:set(),2:set(),3:set(),4:set()}
  gdMap = {1:set(),2:set(),3:set(),4:set()}
  data = _makeJobDetails(jdMap)
  for d in data:
    xdMap[d[2]].add(d)
  try:
    dbtu.fillProcessorTable(cursor,3,logger=logger)
    cursor.execute("SELECT id from processors")
    me.connection.commit()
    addedJobs = dbtu.addSomeJobs(cursor,jdMap)
    me.connection.commit()
    assert data == addedJobs
    cursor.execute("SELECT pathname,uuid,owner FROM jobs ORDER BY OWNER ASC")
    me.connection.commit()
    data2 = cursor.fetchall()
    assert len(data) == len(data2)
    for d in data2:
      gdMap[d[2]].add(d)
    assert xdMap == gdMap
  finally:
    pt = db_schema.ProcessorsTable(logger)
    pt.drop(cursor)
    pt.create(cursor)
    cursor.execute("DELETE from jobs")
    me.connection.commit()

def testSetPriority_Jobs():
  global me
  cursor = me.connection.cursor()
  try:
    dbtu.fillProcessorTable(cursor,3,stamp=dt.datetime(2008,3,4,5,6,7))
    cursor.execute("SELECT id FROM processors")
    me.connection.commit()
    counts = dict((x[0],x[0]) for x in cursor.fetchall())
    dbtu.addSomeJobs(cursor,counts,logger)
    cursor.execute("SELECT id FROM jobs")
    me.connection.commit()
    jobIds = [x[0] for x in cursor.fetchall()]
    half = len(jobIds)/2
    expectPri = jobIds[:half]
    expectNon = jobIds[half:]
    dbtu.setPriority(cursor,expectPri)
    cursor.execute("SELECT id FROM jobs WHERE priority > 0 ORDER BY id")
    gotPri = [x[0] for x in cursor.fetchall()]
    cursor.execute("SELECT id FROM jobs WHERE priority = 0 ORDER BY id")
    gotNon = [x[0] for x in cursor.fetchall()]
    me.connection.commit()
    assert expectPri == gotPri
    assert expectNon == gotNon
  finally:
    jt = db_schema.JobsTable(logger)
    jt.drop(cursor)
    jt.create(cursor)
    pt = db_schema.ProcessorsTable(logger)
    pt.drop(cursor)
    pt.create(cursor)
    me.connection.commit()

def testSetPriority_PriorityJobs():
  global me
  cursor = me.connection.cursor()
  try:
    dbtu.fillProcessorTable(cursor,3,stamp=dt.datetime(2008,3,4,5,6,7))
    cursor.execute("SELECT id FROM processors")
    counts = dict((x[0],x[0]) for x in cursor.fetchall())
    dbtu.addSomeJobs(cursor,counts,logger)
    cursor.execute("SELECT id,uuid FROM jobs")
    me.connection.commit()
    data = cursor.fetchall()
    jobIds = [x[0] for x in data]
    jobUuids = [x[1] for x in data]
    half = len(jobIds)/2
    expect1Pri = jobIds[:half]
    expect2Pri = jobIds[half:]
    expect1Uuid = sorted(jobUuids[:half])
    expect2Uuid = sorted(jobUuids[half:])
    dbtu.setPriority(cursor,expect1Pri,'priority_jobs_1')
    dbtu.setPriority(cursor,expect2Pri,'priority_jobs_2')
    sql = "SELECT uuid from %s ORDER BY uuid"
    cursor.execute(sql%'priority_jobs_1')
    got1Uuid = [x[0] for x in cursor.fetchall()]
    cursor.execute(sql%'priority_jobs_2')
    got2Uuid = [x[0] for x in cursor.fetchall()]
    me.connection.commit()
    assert expect1Uuid == got1Uuid
    assert expect2Uuid == got2Uuid 
  finally:
    jt = db_schema.JobsTable(logger)
    jt.drop(cursor)
    jt.create(cursor)
    pt = db_schema.ProcessorsTable(logger)
    pt.drop(cursor)
    pt.create(cursor)
    me.connection.commit()

def testFillDimsTables_Default():
  global me
  cursor = me.connection.cursor()
  dimsTables = [db_schema.ProductDimsTable, db_schema.UrlDimsTable, db_schema.OsDimsTable]
  toBeCleanedInstances = [x(logger) for x in db_schema.getOrderedSetupList(dimsTables)]
  try:
    dbtu.fillDimsTables(cursor)
    for table,filler in dbtu.dimsData.items():
      got = []
      colList = filler[0].keys()
      cols = ','.join(colList)
      cursor.execute("SELECT %s from %s ORDER BY id"%(cols,table))
      gotData = cursor.fetchall()
      for d in gotData:
        got.append(dict(zip(colList,d)))
      assert dbtu.dimsData[table] == got
    me.connection.commit()
  finally:
    for inst in toBeCleanedInstances:
      inst.drop(cursor)
    me.connection.commit()
    for inst in toBeCleanedInstances:
      inst._createSelf(cursor)
    me.connection.commit()

def testFillDimsTables_MyData():
  global me
  cursor = me.connection.cursor()
  dimsTables = [db_schema.ProductDimsTable, db_schema.UrlDimsTable, db_schema.OsDimsTable]
  toBeCleanedInstances = [x(logger) for x in db_schema.getOrderedSetupList(dimsTables)]
  data = {
    'productdims':[{'product':'P1','version':'V1','release':'major'},{'product':'P2','version':'V2','release':'milestone'},{'product':'P1','version':'V3','release':'development'}],
    'urldims':[{'domain':'www.woot.com','url':'http://www.woot.com/patootie#bleep'},{'domain':'google.com','url':'http://google.com/search'}],
    'osdims':[{'os_name':'AnOS','os_version':'6.6.6'}],
    }
  try:
    dbtu.fillDimsTables(cursor,data)
    for table,filler in data.items():
      got = []
      colList = filler[0].keys()
      cols = ','.join(colList)
      cursor.execute("SELECT %s from %s ORDER BY id"%(cols,table))
      me.connection.commit()
      gotData = cursor.fetchall()
      for d in gotData:
        got.append(dict(zip(colList,d)))
      assert data[table] == got, 'expected %s, got %s'%(data[table],got)
  finally:
    for inst in toBeCleanedInstances:
      inst.drop(cursor)
    me.connection.commit()
    for inst in toBeCleanedInstances:
      inst._createSelf(cursor)
    me.connection.commit()
    

