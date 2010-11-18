
import errno
import logging
import os
import urllib2

import psycopg2

import unittest
from nose.tools import *

import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.util
import socorro.lib.psycopghelper as psy
import socorro.cron.builds as builds
import socorro.database.schema as sch

from   socorro.unittest.testlib.loggerForTest import TestingLogger
from   socorro.unittest.testlib.testDB import TestDB
import socorro.unittest.testlib.util as tutil
import socorro.unittest.testlib.expectations as exp

import cronTestconfig as testConfig

def makeBogusBuilds(connection, cursor):
  # (product, version, platform, buildid, changeset, filename, date)
  fakeBuildsData = [ ("PRODUCTNAME1", "VERSIONAME1", "PLATFORMNAME1", "1", "CHANGESET1", "FILENAME1", "2010-03-09 14:57:04.046627", "APP_CHANGESET_1_1", "APP_CHANGESET_1_2"),
                     ("PRODUCTNAME2", "VERSIONAME2", "PLATFORMNAME2", "2", "CHANGESET2", "FILENAME2", "2010-03-09 14:57:04.046627", "APP_CHANGESET_2_1", "APP_CHANGESET_2_2"),
                     ("PRODUCTNAME3", "VERSIONAME3", "PLATFORMNAME3", "3", "CHANGESET3", "FILENAME3", "2010-03-09 14:57:04.046627", "APP_CHANGESET_3_1", "APP_CHANGESET_3_2"),
                     ("PRODUCTNAME4", "VERSIONAME4", "PLATFORMNAME4", "4", "CHANGESET4", "FILENAME4", "2010-03-09 14:57:04.046627", "APP_CHANGESET_4_1", "APP_CHANGESET_4_2"),
                   ]

  for b in fakeBuildsData:
    try:
      cursor.execute("INSERT INTO builds (product, version, platform, buildid, platform_changeset, filename, date, app_changeset_1, app_changeset_2) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)", b)
      connection.commit()
    except Exception, x:
      print "Exception at makeBogusBuilds() buildsTable.insert", type(x),x
      connection.rollback()


class Me:
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
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing builds')
  tutil.nosePrintModule(__file__)
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
    me.logFilePathname = 'logs/builds_test.log'
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
  me.fileLogger = logging.getLogger("builds")
  me.fileLogger.addHandler(fileLog)
  # Got trouble?  See what's happening by uncommenting the next three lines
  #stderrLog = logging.StreamHandler()
  #stderrLog.setLevel(10)
  #me.fileLogger.addHandler(stderrLog)

  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)
  me.testDB = TestDB()
  me.testDB.removeDB(me.config,me.fileLogger)
  me.testDB.createDB(me.config,me.fileLogger)
  try:
    me.conn = psycopg2.connect(me.dsn)
    me.cur = me.conn.cursor(cursor_factory=psy.LoggingCursor)
  except Exception, x:
    print "Exception in setup_module() connecting to database ... Error: ",type(x),x
    socorro.lib.util.reportExceptionAndAbort(me.fileLogger)
  makeBogusBuilds(me.conn, me.cur)

def teardown_module():
  global me
  me.testDB.removeDB(me.config,me.fileLogger)
  me.conn.close()
  try:
    os.unlink(me.logFilePathname)
  except:
    pass


class TestBuilds(unittest.TestCase):
  def setUp(self):
    global me
    self.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing builds')

    myDir = os.path.split(__file__)[0]
    if not myDir: myDir = '.'
    replDict = {'testDir':'%s'%myDir}
    for i in self.config:
      try:
        self.config[i] = self.config.get(i)%(replDict)
      except:
        pass
    self.logger = TestingLogger(me.fileLogger)

    self.testConfig = configurationManager.Config([('t','testPath', True, './TEST-BUILDS', ''),
                                                   ('f','testFileName', True, 'lastrun.pickle', ''),
                                                  ])
    self.testConfig["persistentDataPathname"] = os.path.join(self.testConfig.testPath, self.testConfig.testFileName)


  def tearDown(self):
    self.logger.clear()


  def do_buildExists(self, d, correct):
    me.cur = me.conn.cursor(cursor_factory=psy.LoggingCursor)
    me.cur.setLogger(me.fileLogger)

    actual = builds.buildExists(me.cur, d[0], d[1], d[2], d[3])
    assert actual == correct, "expected %s, got %s " % (correct, actual)


  def test_buildExists(self):
    d = ( "failfailfail", "VERSIONAME1", "PLATFORMNAME1", "1" )
    self.do_buildExists(d, None)
    d = ( "PRODUCTNAME1", "VERSIONAME1", "PLATFORMNAME1", "1" )
    self.do_buildExists(d, True)


  def test_fetchBuild(self):
    fake_response_contents_1 = '11111'
    fake_response_contents_2 = '22222'
    fake_response_contents = '%s %s' % (fake_response_contents_1, fake_response_contents_2)
    fake_urllib2_url = 'http://www.example.com/'

    fakeResponse = exp.DummyObjectWithExpectations()
    fakeResponse.code = 200
    fakeResponse.expect('read', (), {}, fake_response_contents)
    fakeResponse.expect('close', (), {})

    fakeUrllib2 = exp.DummyObjectWithExpectations()
    fakeUrllib2.expect('urlopen', (fake_urllib2_url,), {}, fakeResponse)

    try:
      actual = builds.fetchBuild(fake_urllib2_url, fakeUrllib2)
      assert actual[0] == fake_response_contents_1, "expected %s, got %s " % (fake_response_contents_1, actual)
      assert actual[1] == fake_response_contents_2, "expected %s, got %s " % (fake_response_contents_2, actual)
    except Exception, x:
      print "Exception in test_fetchBuild() ... Error: ",type(x),x
      socorro.lib.util.reportExceptionAndAbort(me.fileLogger)


  def test_insertBuild(self):
    me.cur = me.conn.cursor(cursor_factory=psy.LoggingCursor)
    me.cur.setLogger(me.fileLogger)

    me.cur.execute("DELETE FROM builds WHERE product = 'PRODUCTNAME5'")
    me.cur.connection.commit()

    try:
      builds.insertBuild(me.cur, 'PRODUCTNAME5', 'VERSIONAME5', 'PLATFORMNAME5', '5', 'CHANGESET5', 'APP_CHANGESET_2_5', 'APP_CHANGESET_2_5', 'FILENAME5')
      actual = builds.buildExists(me.cur, 'PRODUCTNAME5', 'VERSIONAME5', 'PLATFORMNAME5', '5')
      assert actual == 1, "expected 1, got %s" % (actual)
    except Exception, x:
      print "Exception in do_insertBuild() ... Error: ",type(x),x
      socorro.lib.util.reportExceptionAndAbort(me.fileLogger)

    me.cur.connection.rollback()


  def test_fetchTextFiles(self):
    self.config.base_url = 'http://www.example.com/'
    self.config.platforms = ('platform1', 'platform2')
    fake_product_uri = 'firefox/nightly/latest-mozilla-1.9.1/'

    fake_response_url = "%s%s" % (self.config.base_url, fake_product_uri)
    fake_response_contents = """
       blahblahblahblahblah
       <a href="product1-version1.en-US.platform1.txt">product1-version1.en-US.platform1.txt</a>
       <a href="product1-version1.en-US.platform1.zip">product1-version1.en-US.platform1.zip</a>
       <a href="product2-version2.en-US.platform2.txt">product2-version2.en-US.platform2.txt</a>
       <a href="product2-version2.en-US.platform2.zip">product2-version2.en-US.platform2.zip</a>
       blahblahblahblahblah
    """ 
    fake_response_success_1 = {'platform':'platform1', 'product':'product1', 'version':'version1', 'filename':'product1-version1.en-US.platform1.txt'}
    fake_response_success_2 = {'platform':'platform2', 'product':'product2', 'version':'version2', 'filename':'product2-version2.en-US.platform2.txt'}
    fake_response_successes = (fake_response_success_1, fake_response_success_2)

    fakeResponse = exp.DummyObjectWithExpectations()
    fakeResponse.code = 200
    fakeResponse.expect('read', (), {}, fake_response_contents)
    fakeResponse.expect('close', (), {})

    fakeUrllib2 = exp.DummyObjectWithExpectations()
    fakeUrllib2.expect('urlopen', (fake_response_url,), {}, fakeResponse)
    
    try:
      actual = builds.fetchTextFiles(self.config, fake_product_uri, fakeUrllib2) 
      assert actual['url'] == fake_response_url, "expected %s, got %s " % (fake_response_url, actual['url'])
      assert actual['builds'][0] == fake_response_success_1, "expected %s, got %s " % (fake_response_success_1, actual['builds'][0])
      assert actual['builds'][1] == fake_response_success_2, "expected %s, got %s " % (fake_response_success_2, actual['builds'][1])
    except Exception, x:
      print "Exception in test_fetchTextFiles() ... Error: ",type(x),x
      socorro.lib.util.reportExceptionAndAbort(me.fileLogger)


if __name__ == "__main__":
  unittest.main()
