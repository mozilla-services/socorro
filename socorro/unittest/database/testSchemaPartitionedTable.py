import datetime as dt
import errno
import logging
import os
import time

from nose.tools import *
import psycopg2

import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.psycopghelper as socorro_pg
import socorro.lib.datetimeutil as dtutil
import socorro.database.schema as schema
import socorro.database.postgresql as socorro_psg

from socorro.unittest.testlib.testDB import TestDB

import dbTestconfig as testConfig

class Me:
  pass
me = None

def setup_module():
  global me
  if me:
    return
  me = Me()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Postgresql Utils')
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
    me.logFilePathname = 'logs/db_test.log'
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
  me.logger = logging.getLogger("db_test")
  me.logger.addHandler(fileLog)
  me.logger.setLevel(logging.DEBUG)
  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)
  me.testDB = TestDB()

def teardown_module():
  me.testDB.removeDB(me.config,me.logger)

tptCreationSql = "CREATE TABLE %s (id serial not null primary key, date_col timestamp without time zone)"
partitionSql = "CREATE table %%(partitionName)s () INHERITS (%s)"
tptPartitionCreationSqlTemplate = partitionSql%'tpt'
tpt3PartitionCreationSqlTemplate = partitionSql%'tpt3'
class TPT(schema.PartitionedTable):
  def __init__(self,logger):
    super(TPT,self).__init__(name='tpt',logger=logger,creationSql=tptCreationSql%'tpt',partitionCreationSqlTemplate=tptPartitionCreationSqlTemplate,weekInterval=None)
    logger.debug("DEBUG - My pcst is %s",self.partitionCreationSqlTemplate)
  def partitionCreationParameters(self,stuff):
    return {'partitionName':'tpt_%s'%stuff}
class ThreePT(schema.PartitionedTable):
  def __init__(self,logger):
    super(ThreePT,self).__init__(name='tpt3',logger=logger,creationSql=tptCreationSql%'tpt3',partitionCreationSqlTemplate=tpt3PartitionCreationSqlTemplate,weekInterval=None)
  def partitionCreationParameters(self,stuff):
    pn = "_".join([str(x) for x in stuff[0].timetuple()[:3]])
    return {'partitionName':'tpt3_%s'%pn}

class TestPartitionedTable:
  def setUp(self):
    self.connection = psycopg2.connect(me.dsn)
  def tearDown(self):
    self.connection.close()
    
  def testConstructor(self):
    """
    TestPartitionedTable.testConstructor(self):
      - (pause a moment if right at midnight, then ...)
      - check that the constructor works as expected
    """
    # make sure we don't fail if we are being run 'too close for comfort' to midnight
    now = dt.datetime.now()
    midnight = dt.datetime(now.year,now.month,now.day,0,0,00)
    midnight += dt.timedelta(days=1)
    middiff = midnight - now
    if middiff < dt.timedelta(0,2):
      time.sleep(middiff.seconds)
    # end of midnight (time) creep
    today = dt.date.today() # now guaranteed to be 'after' midnight
    expectedIntervalList = [x for x in schema.mondayPairsIteratorFactory(today,today)]
    testPt = TPT(logger=me.logger)
    assert 'tpt' == testPt.name
    assert me.logger == testPt.logger
    assert '%s' == testPt.partitionNameTemplate
    assert tptCreationSql%'tpt' == testPt.creationSql
    createdIntervalList = [x for xi in testPt.weekInterval]
    assert expectedIntervalList == createdIntervalList

  def testCreatePartitions_one(self):
    """
    TestPartitionedTable.testCreatePartitions_one():
      - assure that we create the expected partition(s) for a PartitionedTable that has no dependencies
    """
    global me
    cursor = self.connection.cursor()
    cursor.execute("DROP TABLE IF EXISTS tpt, tpt3 CASCADE")
    self.connection.commit()
    testPt = TPT(logger=me.logger)
    try:
      tptSet0 = set(socorro_psg.tablesMatchingPattern('tpt%',cursor))
      assert set() == tptSet0, 'Assure we start with clean slate'
      testPt.create(cursor)
      self.connection.commit()
      tptSet1 = set(socorro_psg.tablesMatchingPattern('tpt%',cursor))
      testPt.createPartitions(cursor,iter(range(2)))
      self.connection.commit()
      tptSet2 = set(socorro_psg.tablesMatchingPattern('tpt%',cursor))
      assert set(['tpt_0', 'tpt_1',]) == tptSet2 - tptSet1,'Got tptSet2: %s minus tptSet1: %s'%(tptSet2,tptSet1)
    finally:
      cursor.execute("DROP TABLE IF EXISTS tpt, tpt3 CASCADE")
      self.connection.commit()
    
  def testCreatePartitions_depend(self):
    """
    TestPartitionedTable.testCreatePartitions_depend():
      - assure that we create the expected partition(s) for a PartitionedTable that has dependencies
    """
    global me
    cursor = self.connection.cursor()
    cursor.execute("DROP TABLE IF EXISTS tpt, tpt3 CASCADE")
    self.connection.commit()
    testPt = ThreePT(logger = me.logger)
    try:
      tptSet0 = set(socorro_psg.tablesMatchingPattern('tpt%',cursor))
      reportSet0 = set(socorro_psg.tablesMatchingPattern('report%',cursor))
      assert set() == tptSet0
      assert set() == reportSet0
      testPt.create(cursor)
      schema.ReportsTable(me.logger).create(cursor)
      self.connection.commit()
      tptSet1 = set(socorro_psg.tablesMatchingPattern('tpt%',cursor))
      reportSet1 = set(socorro_psg.tablesMatchingPattern('report%',cursor))
      schema.databaseDependenciesForPartition[ThreePT] = [schema.ReportsTable]
      testPt.createPartitions(cursor,iter([(dt.date(2008,1,1),dt.date(2008,1,1)),(dt.date(2008,2,2),dt.date(2008,2,9))]))
      self.connection.commit()
      tptSet2 = set(socorro_psg.tablesMatchingPattern('tpt%',cursor))
      reportSet2 = set(socorro_psg.tablesMatchingPattern('report%',cursor))
      assert set(['tpt3_2008_1_1','tpt3_2008_2_2']) == tptSet2 - tptSet1
      assert set(['reports_20080101', 'reports_20080202']) == reportSet2 - reportSet1
    finally:
      cursor.execute("DROP TABLE IF EXISTS tpt, tpt3, reports CASCADE")
      self.connection.commit()

  def altConnectionCursor(self):
    global me
    connection = psycopg2.connect(me.dsn)
    cursor = connection.cursor()
    return (connection,cursor)
  
  def testPartitionInsert(self):
    """
    TestPartitionedTable.testPartitionInsert():
    - check that we automagically create the needed partition on insert
    """
    global me
    tz = dtutil.UTC()
    # test in this order, because other things depend on reports
    insertRows = [
      [schema.ReportsTable,['0bba61c5-dfc3-43e7-dead-8afd20071025',dt.datetime(2007,12,25,5,4,3,21,tz),dt.datetime(2007,12,25,5,4,3,33),'product','version','build','url',3000,0,22,'email',dt.date(2007,12,1),None,"","","",""]],
      [schema.ExtensionsTable,[1,dt.datetime(2007,12,25,5,4,3,33),1,'extensionid','version']],
      [schema.FramesTable,[1,2,dt.datetime(2007,12,25,5,4,3,33),'somesignature']],
      [schema.DumpsTable,[1,dt.datetime(2007,12,25,5,4,3,33),"data"]],
      ]
    # call insert, expecting auto-creation of partitions
    cursor = self.connection.cursor()
    me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)
    schema.setupDatabase(me.config,me.logger)
    before = set([x for x in socorro_psg.tablesMatchingPattern('%',cursor) if not 'pg_toast' in x])
    for t in insertRows:
      obj = t[0](logger=me.logger)
      obj.insert(cursor,t[1],self.altConnectionCursor,date_processed=dt.datetime(2007,12,25,5,4,3,33))
      self.connection.commit()
      current = set([x for x in socorro_psg.tablesMatchingPattern('%',cursor) if not 'pg_toast' in x])
      diff = current - before
      assert set(['%s_20071224'%obj.name]) == diff,'Expected set([%s_20071224]), got %s'%(obj.name,diff)
      before = current
  
