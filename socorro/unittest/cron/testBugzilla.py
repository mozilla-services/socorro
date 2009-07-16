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

#from createTables import createCronTables, dropCronTables
import socorro.unittest.testlib.dbtestutil as dbtestutil
from   socorro.unittest.testlib.loggerForTest import TestingLogger
from   socorro.unittest.testlib.testDB import TestDB
import socorro.unittest.testlib.util as tutil

import cronTestconfig as testConfig

def makeBogusReports (connection, cursor, logger):
  # make some bogus data in the reports table
  reportsTable = sch.ReportsTable(logger)
                    # ( uuid,    client_crash_date,   date_processed,             product,   version,   build,   url,              install_age,   last_crash,   uptime,   email,   build_date,   user_id,   user_comments,   app_notes,   distributor,   distributor_version) values
  fakeReportData = [ (( "uuid1", None,                dt.datetime(2009, 05, 04),  "bogus",   "1.0",     "xxx",   "http://cnn.com", 100,           14,           10,       None,    None,         None,      "bogus",         "",          "",            ","), "BogusClass::bogus_signature (const char**, void *)"),
                     (( "uuid2", None,                dt.datetime(2009, 05, 04),  "bogus",   "1.0",     "xxx",   "http://cnn.com", 100,           14,           10,       None,    None,         None,      "bogus",         "",          "",            ","), "js3250.dll@0x6cb96"),
                     (( "uuid3", None,                dt.datetime(2009, 05, 04),  "bogus",   "1.0",     "xxx",   "http://cnn.com", 100,           14,           10,       None,    None,         None,      "bogus",         "",          "",            ","), "libobjc.A.dylib@0x1568c"),
                     (( "uuid4", None,                dt.datetime(2009, 05, 04),  "bogus",   "1.0",     "xxx",   "http://cnn.com", 100,           14,           10,       None,    None,         None,      "bogus",         "",          "",            ","), "nanojit::LIns::isTramp()"),
                     (( "uuid5", None,                dt.datetime(2009, 05, 04),  "bogus",   "1.0",     "xxx",   "http://cnn.com", 100,           14,           10,       None,    None,         None,      "bogus",         "",          "",            ","), "libobjc.A.dylib@0x1568c"),
                   ]
  try:
    altconn = psycopg2.connect(me.dsn)
    altcur = altconn.cursor()
  except Exception, x:
    print x
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
      print x
      connection.rollback()
  altconn.close()

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
  stderrLog = logging.StreamHandler()
  stderrLog.setLevel(10)
  me.fileLogger = logging.getLogger("bugzilla")
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
    print x
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
    #self.connection = psycopg2.connect(me.dsn)

    self.testConfig = configurationManager.Config([('t','testPath', True, './TEST-BUGZILLA', ''),
                                                  ('f','testFileName', True, 'lastrun.pickle', ''),
                                                  ('', 'daysIntoPast', True, 0),])
    self.testConfig["persistentDataPathname"] = os.path.join(self.testConfig.testPath, self.testConfig.testFileName)

  def tearDown(self):
    self.logger.clear()

  def do_find_signatures(self, testInput, correct):
    actual = bug.find_signatures(testInput)
    assert actual == correct, "expected %s, got %s" % (correct, actual)

  def test_find_signatures(self):
    d = {  }
    self.do_find_signatures(d, None)
    d = { "short_description": "short", "bug_id": "22", "bug_status": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, None)
    d = { "short_desc": "short", "bugger_id": "22", "bug_status": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, None)
    d = { "short_desc": "short", "bug_id": "22", "bug_status": "CLOSED", "revolution": "WONTFIX" }
    self.do_find_signatures(d, None)
    d = { "short_desc": "short", "bug_id": "22", "bug_statusizer": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, None)
    d = { "short_desc": "short", "bug_id": dt.datetime.now(), "bug_status": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, None)
    d = { "short_desc": "short", "bug_id": 'Amtrak', "bug_status": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, None)
    d = { "short_desc": "short", "bug_id": "22", "bug_status": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, (22, "CLOSED", "WONTFIX", "short", []))
    d = { "short_desc": "short [@ bogus_incomplete_signature", "bug_id": "22", "bug_status": "NEW", "resolution": "" }
    self.do_find_signatures(d, (22, "NEW", "", "short [@ bogus_incomplete_signature", []))
    d = { "short_desc": "short [@ complete_signature]", "bug_id": "22", "bug_status": "CLOSED", "resolution": "RESOLVED" }
    self.do_find_signatures(d, (22, "CLOSED", "RESOLVED", "short [@ complete_signature]", ["complete_signature"]))
    d = { "short_desc": "short [@ complete_signature]othertext[@  second_signature !@#$%^&*()_   ]  [ not_a_signature @ hey ]", "bug_id": "22", "bug_status": "OPEN", "resolution": "ASSIGNED" }
    self.do_find_signatures(d, (22, "OPEN", "ASSIGNED", "short [@ complete_signature]othertext[@  second_signature !@#$%^&*()_   ]  [ not_a_signature @ hey ]", ["complete_signature", "second_signature !@#$%^&*()_"]))
    d = { "short_desc": "short [@ libobjc.A.dylib@0x1568c]othertext[   @]  INVALIDthird_signature !@#$%^&*()_   ]  [ not_a_signature @ hey ]", "bug_id": "22", "bug_status": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, (22, "CLOSED", "WONTFIX", "short [@ libobjc.A.dylib@0x1568c]othertext[   @]  INVALIDthird_signature !@#$%^&*()_   ]  [ not_a_signature @ hey ]", ["libobjc.A.dylib@0x1568c"]))
    d = { "short_desc": "short [[@ not_one]][ @ not_two] [@ this_is bad too", "bug_id": "22", "bug_status": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, (22, "CLOSED", "WONTFIX", "short [[@ not_one]][ @ not_two] [@ this_is bad too", []))
    d = { "short_desc": "short [@ x.dll@0x123456 | free | not_free][ @ not_two] [@ goobers] [@[[[[[[[[[[[[[[[]]]]]]]]]]]]", "bug_id": "22", "bug_status": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, (22, "CLOSED", "WONTFIX", "short [@ x.dll@0x123456 | free | not_free][ @ not_two] [@ goobers] [@[[[[[[[[[[[[[[[]]]]]]]]]]]]", ['x.dll@0x123456 | free | not_free', 'goobers']))
    d = { "short_desc": "short []]]]]]]]]]]][@one]", "bug_id": "22", "bug_status": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, (22, "CLOSED", "WONTFIX", "short []]]]]]]]]]]][@one]", ['one']))
    d = { "short_desc": "short [@ lots of nesting [ 1 [ 2 [ 3 [ 4]]]]][@one]", "bug_id": "22", "bug_status": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, (22, "CLOSED", "WONTFIX", "short [@ lots of nesting [ 1 [ 2 [ 3 [ 4]]]]][@one]", ['lots of nesting [ 1 [ 2 [ 3 [ 4]]]]', 'one']))
    d = { "short_desc": "short crazy real signature:[@ CDiaPropertyStorage<CDiaLineNumber>::Functor<IDiaSymbol*, {[thunk]:`vcall'{12, {flat}}' }', 0}>::~Functor<IDiaSymbol*, {[thunk]:`vcall'{12, {flat}}' }', 0}>()]", "bug_id": "22", "bug_status": "CLOSED", "resolution": "WONTFIX" }
    self.do_find_signatures(d, (22, "CLOSED", "WONTFIX", "short crazy real signature:[@ CDiaPropertyStorage<CDiaLineNumber>::Functor<IDiaSymbol*, {[thunk]:`vcall'{12, {flat}}' }', 0}>::~Functor<IDiaSymbol*, {[thunk]:`vcall'{12, {flat}}' }', 0}>()]", ["""CDiaPropertyStorage<CDiaLineNumber>::Functor<IDiaSymbol*, {[thunk]:`vcall'{12, {flat}}' }', 0}>::~Functor<IDiaSymbol*, {[thunk]:`vcall'{12, {flat}}' }', 0}>()"""]))

  def test_bug_id_to_signature_association_iterator(self):
    csv = ['bug_id,"bug_severity","priority","op_sys","assigned_to","bug_status","resolution","short_desc"\n',
           '1,"critical","top","all","nobody","NEW",,"this comment, while bogus, has commas and no signature.  It should be ignored."',
           '2,"critical","top","all","nobody","CLOSED","WONTFIX","this comment has one signature [@ BogusClass::bogus_signature (const char**, void *)]"',
           '343324,"critical","top","all","nobody","ASSIGNED",,"[@ js3250.dll@0x6cb96] this comment has two signatures [@ libobjc.A.dylib@0x1568c]"',
           '343325,"critical","top","all","nobody","CLOSED","RESOLVED","[@ nanojit::LIns::isTramp()] this comment has one valid and one broken signature [@ libobjc.A.dylib@0x1568c"',
          ]
    correct = [ (1,     "NEW",     "",         "this comment, while bogus, has commas and no signature.  It should be ignored.", []),
                (2,     "CLOSED",  "WONTFIX",  "this comment has one signature [@ BogusClass::bogus_signature (const char**, void *)]", ["BogusClass::bogus_signature (const char**, void *)"]),
                (343324,"ASSIGNED","",         "[@ js3250.dll@0x6cb96] this comment has two signatures [@ libobjc.A.dylib@0x1568c]", ["js3250.dll@0x6cb96","libobjc.A.dylib@0x1568c"]),
                (343325,"CLOSED",  "RESOLVED", "[@ nanojit::LIns::isTramp()] this comment has one valid and one broken signature [@ libobjc.A.dylib@0x1568c", ["nanojit::LIns::isTramp()"]),
              ]
    for expected, actual in zip(bug.bug_id_to_signature_association_iterator(csv,iter), correct):
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

    me.cur = me.conn.cursor(cursor_factory=psy.LoggingCursor)
    me.cur.setLogger(me.fileLogger)

    psy.execute(me.cur, "delete from bug_status")
    me.cur.connection.commit()

    # test intial insert
    sample1 = [ (2,"CLOSED","WONTFIX","a short desc",["aaaa"]),
                (3,"NEW","","a short desc",[]),
                (343324,"ASSIGNED","","a short desc",["bbbb","cccc"]),
                (343325,"CLOSED","RESOLVED","a short desc",["dddd"]),
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
    sample2 = [ (2,"CLOSED","WONTFIX","a short desc",[]),
                (343324,"ASSIGNED","","a short desc",["bbbb"]),
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
    sample2 = [(343324,"CLOSED","RESOLVED","a short desc",["bbbb"]),
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
      return dt.datetime(2009,05,04,15,10)
    assert bug.get_last_run_date(self.testConfig, a_fixed_date) == dt.datetime(2009, 1, 24, 15, 10)
    def another_fixed_date():
      return dt.datetime(2009,06,14,15,10)
    bug.save_last_run_date(self.testConfig, another_fixed_date)
    assert bug.get_last_run_date(self.testConfig) == another_fixed_date()
    try:
      os.unlink(self.testConfig.persistentDataPathname)
    except OSError, x:
      assert False, 'should have been able to delete the file: %s' % self.testConfig.persistentDataPathname
    os.rmdir(self.testConfig.testPath)


if __name__ == "__main__":
  unittest.main()
