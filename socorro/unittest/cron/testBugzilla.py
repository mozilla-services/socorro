import datetime as dt
import errno
import logging
import os
import time

import psycopg2

import unittest
from nose.tools import *

import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.util
import socorro.lib.psycopghelper as psy
import socorro.cron.bugzilla as bug
import socorro.database.schema as sch
import socorro.database.database as sdatabase

from socorro.lib.datetimeutil import UTC

#from createTables import createCronTables, dropCronTables
import socorro.unittest.testlib.dbtestutil as dbtestutil
from   socorro.unittest.testlib.loggerForTest import TestingLogger
from   socorro.unittest.testlib.testDB import TestDB
import socorro.unittest.testlib.util as tutil

import cronTestconfig as testConfig

def makeBogusReports (connection, cursor, logger):
  # make some bogus data in the reports table
  reportsTable = sch.ReportsTable(logger)
                    # ( uuid,    client_crash_date,   date_processed,                         product,   version,   build,   url,              install_age,   last_crash,   uptime,   email,   user_id,   user_comments,   app_notes,   distributor,   distributor_version, topmost_filenames, addons_checked, flash_version, hangid, process_type) values
  fakeReportData = [ (( "uuid1", None,                dt.datetime(2009, 05, 04, tzinfo=UTC),  "bogus",   "1.0",     "xxx",   "http://cnn.com", 100,           14,           10,       None,    None,      "bogus",         "",          "",            ",",                 None,              None,           None,          None,   None,         'release'), "BogusClass::bogus_signature (const char**, void *)"),
                     (( "uuid2", None,                dt.datetime(2009, 05, 04, tzinfo=UTC),  "bogus",   "1.0",     "xxx",   "http://cnn.com", 100,           14,           10,       None,    None,      "bogus",         "",          "",            ",",                 None,              None,           None,          None,   None,         'release'), "js3250.dll@0x6cb96"),
                     (( "uuid3", None,                dt.datetime(2009, 05, 04, tzinfo=UTC),  "bogus",   "1.0",     "xxx",   "http://cnn.com", 100,           14,           10,       None,    None,      "bogus",         "",          "",            ",",                 None,              None,           None,          None,   None,         'release'), "libobjc.A.dylib@0x1568c"),
                     (( "uuid4", None,                dt.datetime(2009, 05, 04, tzinfo=UTC),  "bogus",   "1.0",     "xxx",   "http://cnn.com", 100,           14,           10,       None,    None,      "bogus",         "",          "",            ",",                 None,              None,           None,          None,   None,         'release'), "nanojit::LIns::isTramp()"),
                     (( "uuid5", None,                dt.datetime(2009, 05, 04, tzinfo=UTC),  "bogus",   "1.0",     "xxx",   "http://cnn.com", 100,           14,           10,       None,    None,      "bogus",         "",          "",            ",",                 None,              None,           None,          None,   None,         'release'), "libobjc.A.dylib@0x1568c"),
                   ]
  try:
    #altconn = psycopg2.connect(me.dsn)
    altconn = me.database.connection()
    altcur = altconn.cursor()
  except Exception, x:
    print "Exception at line 40:",type(x),x
    raise
  def cursorFunction():
    return altconn, altcur
  for rep, sig in fakeReportData:
    try:
      reportsTable.insert(cursor, rep, cursorFunction, date_processed=rep[2])
      connection.commit()
      cursor.execute("update reports set signature=%s where date_processed = %s and uuid = %s", (sig, rep[2], rep[0]))
      connection.commit()
    except Exception, x:
      print "Exception at line 51", type(x),x
      connection.rollback()
  altconn.close()

class Me: # not quite "self"
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
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing bugzilla')
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
    me.logFilePathname = 'logs/bugzilla_test.log'
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
  me.fileLogger = logging.getLogger("bugzilla")
  me.fileLogger.addHandler(fileLog)
  # Got trouble?  See what's happening by uncommenting the next three lines
  #stderrLog = logging.StreamHandler()
  #stderrLog.setLevel(10)
  #me.fileLogger.addHandler(stderrLog)

  me.database = sdatabase.Database(me.config)
  #me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      #me.config.databaseUserName,me.config.databasePassword)
  me.testDB = TestDB()
  me.testDB.removeDB(me.config,me.fileLogger)
  me.testDB.createDB(me.config,me.fileLogger)
  try:
    me.conn = me.database.connection()
    #me.conn = psycopg2.connect(me.dsn)
    #me.cur = me.conn.cursor(cursor_factory=psy.LoggingCursor)
    me.cur = me.conn.cursor()
  except Exception, x:
    print "Exception at line 107",type(x),x
    socorro.lib.util.reportExceptionAndAbort(me.fileLogger)
  makeBogusReports(me.conn, me.cur, me.fileLogger)

def teardown_module():
  global me
  me.testDB.removeDB(me.config,me.fileLogger)
  me.conn.close()
  try:
    os.unlink(me.logFilePathname)
  except:
    pass

class TestBugzilla(unittest.TestCase):
  def setUp(self):
    global me
    self.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing bugzilla')

    myDir = os.path.split(__file__)[0]
    if not myDir: myDir = '.'
    replDict = {'testDir':'%s'%myDir}
    for i in self.config:
      try:
        self.config[i] = self.config.get(i)%(replDict)
      except:
        pass
    self.logger = TestingLogger(me.fileLogger)
    self.connection = me.database.connection()
    #self.connection = psycopg2.connect(me.dsn)

    self.testConfig = configurationManager.Config([('t','testPath', True, './TEST-BUGZILLA', ''),
                                                  ('f','testFileName', True, 'lastrun.pickle', ''),
                                                  ('', 'daysIntoPast', True, 0),])
    self.testConfig["persistentDataPathname"] = os.path.join(self.testConfig.testPath, self.testConfig.testFileName)

  def tearDown(self):
    self.logger.clear()

  def test_bugzilla_iterator(self):
    csv = ['bug_id,"bug_status","resolution","short_desc","cf_crash_signature"\n',
           '1,"RESOLVED",,"this is a comment","This sig, while bogus, has a ] bracket"',
           '2,"CLOSED","WONTFIX","comments are not too important","single [@ BogusClass::bogus_sig (const char**) ] signature"',
           '3,"ASSIGNED",,"this is a comment. [@ nanojit::LIns::isTramp()]","[@ js3250.dll@0x6cb96] [@ valid.sig@0x333333]"',
           '4,"CLOSED","RESOLVED","two sigs enter, one sig leaves","[@ layers::Push@0x123456] [@ layers::Push@0x123456]"',
           '5,"ASSIGNED","INCOMPLETE",,"[@ MWSBAR.DLL@0x2589f] and a broken one [@ sadTrombone.DLL@0xb4s455"',
           '6,"ASSIGNED",,"empty crash sigs should not throw errors",""',
           '7,"CLOSED",,"gt 525355 gt","[@gfx::font(nsTArray<nsRefPtr<FontEntry> > const&)]"',
           '8,"CLOSED","RESOLVED","newlines in sigs","[@ legitimate(sig)] \n junk \n [@ another::legitimate(sig) ]"'
          ]
    correct = [ (1, "RESOLVED", "", "this is a comment", set([])),
                (2, "CLOSED", "WONTFIX", "comments are not too important", set(["BogusClass::bogus_sig (const char**)"])),
                (3, "ASSIGNED", "", "this is a comment. [@ nanojit::LIns::isTramp()]",
                 set(["js3250.dll@0x6cb96", "valid.sig@0x333333"])),
                (4, "CLOSED", "RESOLVED", "two sigs enter, one sig leaves", set(["layers::Push@0x123456"])),
                (5, "ASSIGNED", "INCOMPLETE", "", set(["MWSBAR.DLL@0x2589f"])),
                (6, "ASSIGNED", "", "empty crash sigs should not throw errors", set([])),
                (7, "CLOSED", "", "gt 525355 gt", set(["gfx::font(nsTArray<nsRefPtr<FontEntry> > const&)"])),
                (8, "CLOSED", "RESOLVED", "newlines in sigs", set(['another::legitimate(sig)', 'legitimate(sig)']))
              ]
    for expected, actual in zip(bug.bugzilla_iterator(csv, iter), correct):
      assert expected == actual, "expected %s, got %s" % (str(expected), str(actual))

  def test_signature_is_found(self):
    global me
    assert bug.signature_is_found("js3250.dll@0x6cb96", me.cur)
    assert not bug.signature_is_found("sir_not_appearing_in_this_film", me.cur)
    me.cur.connection.rollback()

  def verify_tables(self, correct):
    global me
    # bug_status
    count = 0
    for expected, actual in zip(psy.execute(me.cur, "select id, status, resolution, short_desc from bugs order by 1"), correct["bugs"]):
      count += 1
      assert expected == actual, "expected %s, got %s" % (str(expected), str(actual))
    assert len(correct["bugs"]) == count, "expected %d entries in bugs but found %d" % (len(correct["bugs"]), count)
    #bug_associations
    count = 0
    for expected, actual in zip(psy.execute(me.cur, "select signature, bug_id from bug_associations order by 1, 2"), correct["bug_associations"]):
      count += 1
      assert expected == actual, "expected %s, got %s" % (str(expected), str(actual))
    assert len(correct["bug_associations"]) == count, "expected %d entries in bug_associations but found %d" % (len(correct["bug_associations"]), count)

  def test_insert_or_update_bug_in_database(self):
    #bugId, statusFromBugzilla, resolutionFromBugzilla, signatureListFromBugzilla
    #new    *                   *                       empty
    #new    *                   *                       1 new
    #new    *                   *                       2 new
    #old    *                   *                       empty
    #old    new                 new
    global me

    def true(x, y):
      return True

    def hasYES(x, y):
      return "YES" in x

    me.cur = me.conn.cursor()
    #me.cur = me.conn.cursor(cursor_factory=psy.LoggingCursor)
    #me.cur.setLogger(me.fileLogger)

    psy.execute(me.cur, "delete from bug_status")
    me.cur.connection.commit()

    # test intial insert
    sample1 = [ (2,"CLOSED","WONTFIX","a short desc",set(["aaaa"])),
                (3,"NEW","","a short desc",set([])),
                (343324,"ASSIGNED","","a short desc",set(["bbbb","cccc"])),
                (343325,"CLOSED","RESOLVED","a short desc",set(["dddd"])),
              ]
    correct1 = { "bugs": [(2,     "CLOSED",  "WONTFIX", "a short desc"),
                          (343324,"ASSIGNED","",        "a short desc"),
                          (343325,"CLOSED",  "RESOLVED","a short desc")],
                 "bug_associations": [("aaaa", 2),
                                      ("bbbb", 343324),
                                      ("cccc", 343324),
                                      ("dddd", 343325)]
               }
    for bugId, statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla, signatureListFromBugzilla in sample1:
      bug.insert_or_update_bug_in_database(bugId, statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla, signatureListFromBugzilla, me.cur, true)
    self.verify_tables(correct1)

    #test removing existing associations
    sample2 = [ (2,"CLOSED","WONTFIX","a short desc",set([])),
                (343324,"ASSIGNED","","a short desc",set(["bbbb"])),
              ]
    correct2 = { "bugs": [(343324,"ASSIGNED","","a short desc"),
                          (343325,"CLOSED",  "RESOLVED","a short desc")],
                 "bug_associations": [("bbbb", 343324),
                                      ("dddd", 343325)]
               }
    for bugId, statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla, signatureListFromBugzilla in sample2:
      bug.insert_or_update_bug_in_database(bugId, statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla, signatureListFromBugzilla, me.cur, true)
    self.verify_tables(correct2)

    #test updating existing associations
    sample2 = [(343324,"CLOSED","RESOLVED","a short desc",set(["bbbb"])),
              ]
    correct2 = { "bugs": [(343324,"CLOSED","RESOLVED","a short desc"),
                          (343325,"CLOSED",  "RESOLVED","a short desc")],
                 "bug_associations": [("bbbb", 343324),
                                      ("dddd", 343325)]
               }
    for bugId, statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla, signatureListFromBugzilla in sample2:
      bug.insert_or_update_bug_in_database(bugId, statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla, signatureListFromBugzilla, me.cur, true)
    self.verify_tables(correct2)

  def test_get_and_set_last_run_date(self):
    try:
      os.makedirs(self.testConfig.testPath)
    except OSError, x:
      if errno.EEXIST == x.errno: pass
      else: raise
    try:
      os.unlink(self.testConfig.persistentDataPathname)
    except OSError, x:
      pass
    def a_fixed_date():
      return dt.datetime(2009,05,04,15,10, tzinfo=UTC)
    assert bug.get_last_run_date(self.testConfig, a_fixed_date) == dt.datetime(2009, 4, 4, 15, 10, tzinfo=UTC)
    def another_fixed_date():
      return dt.datetime(2009,06,14,15,10, tzinfo=UTC)
    bug.save_last_run_date(self.testConfig, another_fixed_date)
    assert bug.get_last_run_date(self.testConfig) == another_fixed_date()
    try:
      os.unlink(self.testConfig.persistentDataPathname)
    except OSError, x:
      assert False, 'should have been able to delete the file: %s' % self.testConfig.persistentDataPathname
    os.rmdir(self.testConfig.testPath)


if __name__ == "__main__":
  unittest.main()
