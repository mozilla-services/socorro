
import datetime
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
import socorro.cron.signatureProductdims as signatureProductdims
import socorro.database.schema as sch

from   socorro.unittest.testlib.loggerForTest import TestingLogger
from   socorro.unittest.testlib.testDB import TestDB
import socorro.unittest.testlib.util as tutil
import socorro.unittest.testlib.expectations as exp

import cronTestconfig as testConfig

def makeBogusSignatureProductdims(connection, cursor):
  bogusProductDimsIds = [100,101]

  sql = "INSERT INTO osdims (id, os_name, os_version) VALUES ( %d, '%s', '%s')" % (1, 'Mac OS X', '10.6.1')
  cursor.execute(sql)
  connection.commit()
  
  sql = "INSERT INTO productdims (id, product, version, branch, release) VALUES (%d, '%s', '%s', '%s', '%s')" % (bogusProductDimsIds[0], "firefox", "3.6.9", "1.9.2", "major")
  cursor.execute(sql)
  connection.commit()
  
  sql = "INSERT INTO productdims (id, product, version, branch, release) VALUES (%d, '%s', '%s', '%s', '%s')" % (bogusProductDimsIds[1], "firefox", "3.6.10", "1.9.3", "major")
  cursor.execute(sql)
  connection.commit()
  
  today = datetime.date.today()
  window_end = datetime.datetime(today.year, today.month, today.day - 1, 2, 0, 0).isoformat(' ')
  fakeData = [(5, 3000, "signature1", bogusProductDimsIds[0], 1, window_end, "01:00:00"),
              (5, 3000, "signature2", bogusProductDimsIds[0], 1, window_end, "01:00:00"),
              (5, 3000, "signature3", bogusProductDimsIds[0], 1, window_end, "01:00:00"),
              (5, 3000, "signature4", bogusProductDimsIds[0], 1, window_end, "01:00:00"),
              (5, 3000, "signature4", bogusProductDimsIds[1], 1, window_end, "01:00:00"),
  ]

  for fd in fakeData:
    try:
      sql = """
        INSERT INTO top_crashes_by_signature
        (count, uptime, signature, productdims_id, osdims_id, window_end, window_size)
        VALUES
        (%d, %d, '%s', %d, %d, '%s', '%s') 
      """ % (fd)
      print sql
      cursor.execute(sql)
      connection.commit()
    except Exception, x:
      print "Exception at testInsertSignatureVersionsData()", type(x), x
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
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing signatureProductdims')
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
    me.logFilePathname = 'logs/signatureProductdims_test.log'
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
  stderrLog = logging.StreamHandler()
  stderrLog.setLevel(10)
  me.fileLogger = logging.getLogger("builds")
  me.fileLogger.addHandler(fileLog)
  me.fileLogger.addHandler(stderrLog)
    
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
    util.reportExceptionAndAbort(me.fileLogger)


def teardown_module():  
  global me
  me.testDB.removeDB(me.config,me.fileLogger)
  me.conn.close()
  try:
    os.unlink(me.logFilePathname)
  except:
    pass


class TestSignatureProductdims(unittest.TestCase):
  def setUp(self):
    global me
    self.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing signatureProductdims')

    myDir = os.path.split(__file__)[0]
    if not myDir: myDir = '.'
    replDict = {'testDir':'%s'%myDir}
    for i in self.config:
      try:
        self.config[i] = self.config.get(i)%(replDict)
      except:
        pass
    self.logger = TestingLogger(me.fileLogger)

    self.testConfig = configurationManager.Config([('t','testPath', True, './TEST-SIGNATUREPRODUCTDIMS', ''),
                                                   ('f','testFileName', True, 'lastrun.pickle', ''),
                                                  ])
    self.testConfig["persistentDataPathname"] = os.path.join(self.testConfig.testPath, self.testConfig.testFileName)


  def tearDown(self):
    self.logger.clear()


  def testPopulateSignatureProductdims(self):
    """
    TestTopCrashesBySignature.populateSignatureProductdims
    """
    me.cur = me.conn.cursor(cursor_factory=psy.LoggingCursor)
    makeBogusSignatureProductdims(me.conn, me.cur)
    
    self.config.start_day = 1
    signatureProductdims.populateSignatureProductdims(self.config)

    bogusProductDimsIds = [100,101]
    bogusSignature = 'signature4'

    sql = """
       SELECT count(*) FROM signature_productdims WHERE productdims_id = %d
    """ % (bogusProductDimsIds[0])
    me.cur.execute(sql)
    me.conn.commit()
    result = me.cur.fetchone()[0]
    try:
      assert result == 4, 'expected to get 4, but got %s instead' % result
    except Exception, x:
      print "Exception in testPopulateSignatureProductdims() Assert Sig by ProductDimsID ... Error: ",type(x),x

    sql = """
       SELECT distinct productdims_id FROM signature_productdims WHERE signature = '%s' 
    """ % (bogusSignature)
    me.cur.execute(sql)
    me.conn.commit()
    result = me.cur.fetchone()[0]
    try:
      assert result == 2, 'expected to get 2, but got %s instead' % result
    except Exception, x:
      print "Exception in testPopulateSignatureProductdims() Assert Sig by ProductDimsID ... Error: ",type(x),x

if __name__ == "__main__":
  unittest.main()
