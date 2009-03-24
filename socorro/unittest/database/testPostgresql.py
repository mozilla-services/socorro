
import errno
import logging
import os

import psycopg2

import socorro.lib.ConfigurationManager as configurationManager
import socorro.database.postgresql as postg
import socorro.database.schema as schema

from   socorro.unittest.testlib.loggerForTest import TestingLogger
from   socorro.unittest.testlib.testDB import TestDB

import dbTestconfig as testConfig

testTableNames = [
  "foo",
  "foo_1",
  "foo_2",
  "a_foo",
  "boot",
  "rip",
  ]
testTablePatterns = {
  'foo%':['foo','foo_1','foo_2',],
  'foo_%':['foo_1','foo_2',],
  '%foo':['foo','a_foo',],
  '%oo%':['foo','foo_1','foo_2','a_foo','boot'],
  'rip':['rip'],
  'rap':[],
  }
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
  # config gets messed up by some tests. Use this one during module setup and teardown
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
  me.logger = logging.getLogger("testPostresql")
  me.logger.addHandler(fileLog)
  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)

def teardown_module():
  try:
    os.unlink(me.logFilePathname)
  except:
    pass

class TestPostgreql:
  def setUp(self):
    global me
    # config gets messed up by some tests. Use this one by preference
    self.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Postgresql Utils')
    for i in self.config:
      try:
        self.config[i] = self.config.get(i)%(replDict)
      except:
        pass
    self.connection = psycopg2.connect(me.dsn)
    self.testDB = TestDB()
    self.testDB.removeDB(self.config,me.logger)
  def tearDown(self):
    cursor = self.connection.cursor()
    dropSql = "drop table %s"
    for tn in testTableNames:
      try:
        cursor.execute(dropSql%tn)
      except psycopg2.ProgrammingError:
        self.connection.rollback();
    self.connection.commit()
  
  def testTablesMatchingPattern(self):
    cursor = self.connection.cursor()
    createSql = "CREATE TABLE %s (id integer)" # postgresql allows empty tables, but it makes me itch...
    for tn in testTableNames:
      cursor.execute(createSql%tn)
    self.connection.commit()
    for pat in testTablePatterns:
      result = postg.tablesMatchingPattern(pat,cursor)
      expected = testTablePatterns[pat]
      assert set(expected)==set(result), "for %s: expected:%s, result:%s"%(pat,expected,result)
    self.connection.commit()
    
  def testTriggersForTable(self):
    global me
    cursor = self.connection.cursor()
    self.testDB.createDB(self.config,me.logger)
    print "TRRRRRIGERS"
    for cl in schema.getOrderedSetupList():
      name = cl(logger = me.logger).name
      print name,
      trigs = postg.triggersForTable(name,cursor)
      print trigs
    self.connection.commit()
  
  def testIndexesForTable(self):
    pass
  
  def testRulesForTable(self):
    pass

  def testContraintsAndTypeForTable(self):
    pass

  def testColumnNameTypeDictionaryForTable(self):
    pass

  def testChildTablesForTable(self):
    pass
  
