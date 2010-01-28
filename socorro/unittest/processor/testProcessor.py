"""
You must run this test module using nose (chant nosetests from the command line)
** There are some issues with nose, offset by the fact that it does multi-thread and setup_module better than unittest
 * This is NOT a unittest.TestCase ... it could be except that unittest screws up setup_module
 * nosetests may hang in some ERROR conditions. SIGHUP, SIGINT and SIGSTP are not noticed. SIGKILL (-9) works
 * You should NOT pass command line arguments to nosetests. You can pass them, but it causes trouble:
 *   Nosetests passes them into the test environment which breaks socorro's configuration behavior
 *   You can set NOSE_WHATEVER envariables prior to running if you need to. See nosetests --help
 *    some useful envariables:
 *      NOSE_VERBOSE=x
 *        where x in [0,     # Prints only 'OK' at end of test run
 *                    1,     # default: Per test: Prints one '.', 'F' or 'E': like unittest
 *                    x > 1, # Per Test: Prints (first comment line, else function name) then status (ok/FAIL/ERROR)
 *                   ]
 *      NOSE_WHERE=directory_path[,directory_path[,...]] : run only tests in these directories. Note commas
 *      NOSE_ATTR=attrspec[,attrspec ...] : run only tests for which at least one attrspec evaluates true.
 *         Accepts '!attr' and 'attr=False'. Does NOT accept natural python syntax ('atter != True', 'not attr')
 *      NOSE_NOCAPTURE=TrueValue : nosetests normally captures stdout and only displays it if the test has fail or error.
 *         print debugging works with this envariable, or you can instead print to stderr or use a logger
 *
 * With NOSE_VERBOSE > 1, you may see "functionName(self): (slow=N)" for some tests. N is the max seconds waiting
 *
 * Another warning: If one of the tests that has self.markLog() fails within the marked code, subsequent tests that depend
 *  on looking at the log will likely fail. Quick fix: in the failing test use this:
 *  try: everything after the first markLog(); finally: markLog()
 *
"""
import copy
import datetime as dt
import errno
import logging
import math
import os
import re
import shutil
import signal
import threading
import time
import traceback

import simplejson
import psycopg2
from nose.tools import *

import socorro.lib.ConfigurationManager as configurationManager
import socorro.lib.psycopghelper as psy
import socorro.database.postgresql as db_postgresql
import socorro.database.schema as schema
import socorro.database.cachedIdAccess as cia

import socorro.unittest.testlib.createJsonDumpStore as createJDS
import socorro.unittest.testlib.dbtestutil as dbtestutil
from   socorro.unittest.testlib.loggerForTest import TestingLogger
from   socorro.unittest.testlib.testDB import TestDB
import socorro.unittest.testlib.util as tutil
import processorTestconfig as testConfig

import socorro.processor.processor as processor

class DummyObjectWithExpectations(object):
  """a class that will accept a series of method calls with arguments, but will raise assertion
     errors if the calls and arguments are not what is expected.
  """
  def __init__(self):
    self._expected = []
    self.counter = 0
  def expect (self, attribute, args, kwargs, returnValue = None):
    self._expected.append((attribute, args, kwargs, returnValue))
  def __getattr__(self, attribute):
    def f(*args, **kwargs):
      try:
        attributeExpected, argsExpected, kwargsExpected, returnValue = self._expected[self.counter]
      except IndexError:
        assert False, "expected no further calls, but got '%s' with args: %s and kwargs: %s" % (attribute, args, kwargs)
      self.counter += 1
      assert attributeExpected == attribute, "expected attribute '%s', but got '%s'" % (attributeExpected, attribute)
      assert argsExpected == args, "expected '%s' arguments %s, \nbut got\n %s" % (attribute, argsExpected, args)
      assert kwargsExpected == kwargs, "expected '%s' keyword arguments %s, but got %s" % (attribute, kwargsExpected, kwargs)
      return returnValue
    return f

class Me: # not quite "self"
  """
  I need stuff to be initialized once per module. Rather than having a bazillion globals, lets just have 'me'
  """
  pass

me = None

loglineS = '^[1-9][0-9]{3}-[0-9]{2}-[0-9]{2}.*'
loglineRE = re.compile(loglineS)

def setup_module():
  global me
  if me:
    return
  # else initialize
  me = Me()
  me.markingTemplate = "MARK %s: %s"
  me.startMark = 'start'
  me.endMark = 'end'
  me.testDB = TestDB()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Processor')
  tutil.nosePrintModule(__file__)
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass
  knownTests = [x for x in dir(TestProcessor) if x.startswith('test')]
  me.logWasExtracted = dict( ((x,False) for x in knownTests) )
  processor.logger.setLevel(logging.DEBUG)
  me.logFilePathname = me.config.logFilePathname

  logfileDir = os.path.split(me.config.logFilePathname)[0]
  try:
    os.makedirs(logfileDir)
  except OSError,x:
    if errno.EEXIST != x.errno: raise
  f = open(me.config.logFilePathname,'w')
  f.close()

  fileLog = logging.FileHandler(me.logFilePathname, 'a')
  fileLog.setLevel(logging.DEBUG)
  fileLogFormatter = logging.Formatter(me.config.logFileLineFormatString)
  fileLog.setFormatter(fileLogFormatter)
  processor.logger.addHandler(fileLog)
  me.logger = TestingLogger(processor.logger)
  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)

# commented out because nosetests doesn't like the logger turned off before all the tests are run.
# def teardown_module():
#
#   global me
#   logging.shutdown()
#   try:
#     os.unlink(me.logFilePathname)
#   except OSError,x:
#     if errno.ENOENT != x.errno:
#       raise

class TestProcessor:
  markingLog = False
  def setUp(self):
    global me
    processor.logger = me.logger
    me.logger.clear()
    # processor.Processor() alters the config data in place. Put it back like it was every time
    me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Processor')
    myDir = os.path.split(__file__)[0]
    if not myDir: myDir = '.'
    replDict = {'testDir':'%s'%myDir}
    for i in me.config:
      try:
        me.config[i] = me.config.get(i)%(replDict)
      except:
        pass
    try:
      shutil.rmtree(me.config.storageRoot)
    except OSError:
      pass # ok if there is no such test directory
    try:
      shutil.rmtree(me.config.deferredStorageRoot)
    except OSError:
      pass # ok if there is no such test directory
    try:
      os.makedirs(me.config.storageRoot)
    except OSError, x:
      if errno.EEXIST == x.errno: pass
      else: raise
    try:
      os.makedirs(me.config.deferredStorageRoot)
    except OSError,x:
      if errno.EEXIST == x.errno: pass
      else: raise
    try:
      os.makedirs(me.config.processedDumpStoragePath)
    except OSError,x:
      if errno.EEXIST == x.errno: pass
      else: raise
    self.connection = psycopg2.connect(me.dsn)
    # blow away any database stuff, in case we crashed on previous run
    me.testDB.removeDB(me.config,me.logger)
    schema.partitionCreationHistory = set() # an 'orrible 'ack
    me.testDB.createDB(me.config,me.logger)
    # 0, 1,                2,             3,   4,      5,      6,    7,        8,  9,          10,        11,
    # id,client_crash_date,date_processed,uuid,product,version,build,signature,url,install_age,last_crash,uptime,
    # 12,      13,      14,    15,     16,     17,        18,   19,        20,     21,
    # cpu_name,cpu_info,reason,address,os_name,os_version,email,build_date,user_id,started_datetime,
    # 22,                23,     24,       25,             26,           27,       28,         29
    # completed_datetime,success,truncated,processor_notes,user_comments,app_notes,distributor,distributor_version,
    self.reportTableColumns =  [
      'id','client_crash_date','date_processed','uuid','product','version','build','signature','url',
      'install_age','last_crash','uptime','cpu_name','cpu_info','reason','address','os_name','os_version',
      'email','build_date','user_id','started_datetime','completed_datetime','success','truncated',
      'processor_notes','user_comments','app_notes','distributor','distributor_version',]
    self.maxTableColumnLength = max( (len(x) for x in self.reportTableColumns))
    cia.clearCache()

  def tearDown(self):
    global me
    #print "\ntearDown",db_postgresql.connectionStatus(self.connection)
    if TestProcessor.markingLog:
      me.logger.warn("AUTO-CLOSING the log marker")
      me.logger.info(me.markingTemplate%(TestProcessor.markingLog,me.endMark))
      TestProcessor.markingLog = False
    me.testDB.removeDB(me.config,me.logger)
    try:
      shutil.rmtree(me.config.storageRoot)
    except OSError:
      pass # ok if there is no such test directory
    try:
      shutil.rmtree(me.config.deferredStorageRoot)
    except OSError:
      pass # ok if there is no such test directory
    try:
      shutil.rmtree(me.config.processedDumpStoragePath)
    except OSError:
      pass # ok if there is no such test directory
    self.connection.close()

  def markLog(self):
    global me
    testName = traceback.extract_stack()[-2][2]
    if TestProcessor.markingLog:
      TestProcessor.markingLog = False
      me.logger.info(me.markingTemplate%(testName,me.endMark))
    else:
      TestProcessor.markingLog = testName
      me.logger.info(me.markingTemplate%(testName,me.startMark))

  def extractLogSegment(self):
    global me
    testName = traceback.extract_stack()[-2][2]
    if me.logWasExtracted[testName]:
      return []
    try:
      file = open(me.config.logFilePathname)
    except IOError,x:
      if errno.ENOENT != x.errno:
        raise
      else:
        return []

    me.logWasExtracted[testName] = True
    startTag = me.markingTemplate%(testName,me.startMark)
    stopTag = me.markingTemplate%(testName,me.endMark)
    lines = file.readlines()
    segment = []
    i = 0
    while i < len(lines):
      if not startTag in lines[i]:
        i += 1
        continue
      else:
        i += 1
        try:
          while not stopTag in lines[i]:
            segment.append(lines[i].strip())
            i += 1
        except IndexError:
          pass
      break
    return segment

  def testConstructor(self):
    """
    testConstructor(self):
      Constructor must fail if any of a lot of configuration details are missing
      Constructor must fail if no processors table in database
      Constructor must succeed if all config is present and a dead processor is found
    """
    global me
    requiredConfigs = [
      "databaseHost",
      "databaseName",
      "databaseUserName",
      "databasePassword",
      "storageRoot",
      "deferredStorageRoot",
      "jsonFileSuffix",
      "dumpFileSuffix",
      "processorCheckInTime",
      "processorCheckInFrequency",
      "processorId",
      "numberOfThreads",
      "batchJobLimit",
      'irrelevantSignatureRegEx',
      'prefixSignatureRegEx',
      ]

    cc = copy.copy(me.config)
    for rc in requiredConfigs:
      del(cc[rc])
      assert_raises(AssertionError,processor.Processor,cc)
    me.testDB.removeDB(me.config,me.logger)
    # Expect to fail if there is no processors table
    assert_raises(SystemExit,processor.Processor,me.config)
    schema.partitionCreationHistory = set() # an 'orrible 'ack
    me.testDB.createDB(me.config,me.logger)
    cur = self.connection.cursor()
    now = dbtestutil.datetimeNow(cur)
    then = now - dt.timedelta(minutes=10)
    dbtestutil.fillProcessorTable(cur,0,processorMap = {1:now,2:now,3:then,4:now})
    self.markLog()
    try:
      p = processor.Processor(me.config)
      assert 3 == p.processorId, "Expected to take over processor #3, but got %s"%(p.processorId)
    finally:
      self.markLog()
    seg = self.extractLogSegment()
    got2 = 0
    for line in seg:
      if 'will step in for' in line or 'stepping in for' in line or 'I am processor #' in line:
        if line.strip().endswith('3'):
          got2 += 1
        else:
          assert False, 'Expected only processor #3 to be taken over'
      if 'my priority jobs table is called' in line:
        assert 'priority_jobs_3' in line, 'Expect only the appropriate table to be mentioned. Got %s'%(line)
    assert got2 == 2, "Expected to see three lines mentioning the processor. Got %s"%(got3)

  def testConstructorTwice(self):
    """
    testConstructorTwice(self):
      Constructor must raise SystemExit when attempting to start two times from same process
    """
    global me
    originalProcId = me.config.processorId # Processor() alters this in place. Be sure to put it back...
    p1 = processor.Processor(me.config)
    me.config['processorId'] = originalProcId
    assert_raises(SystemExit,processor.Processor,me.config)

  def testConstructorAllProcessesLive(self):
    """
    testConstructorAllProcessesLive(self):
      If there are only live processes in the processes table, must create another one
    """
    global me
    dbtestutil.fillProcessorTable(self.connection.cursor(),3)
    p1 = processor.Processor(me.config)
    self.markLog()
    try:
      assert 3 < p1.processorId,'Expected to get the next available id, but got %s'%(p1.processorId)
    finally:
      self.markLog()

  def testConstructorInvalidId(self):
    """
    testConstructorInvalidId(self):
      If the config processId is non-integer string, not 'auto', then fail
      If the config processId is valid, but outside current range of running ids. then fail
    """
    global me
    me.config['processorId'] = 'invalidId'
    assert_raises(SystemExit,processor.Processor,me.config)
    me.config['processorId'] = '234'
    self.markLog()
    try:
      assert_raises(SystemExit,processor.Processor,me.config)
    finally:
      self.markLog()

  def testConstructorConfigLiveId(self):
    """
    testConstructorConfigLiveId(self):
      If the config processId is a valid id, but that id represents a live process, then fail
    """
    global me
    dbtestutil.fillProcessorTable(self.connection.cursor(),3)
    me.config['processorId'] = '2'
    self.markLog()
    try:
      assert_raises(SystemExit,processor.Processor,me.config)
    finally:
      self.markLog()

  class StubProcessor_start(processor.Processor):
    def __init__(self,config):
      super(TestProcessor.StubProcessor_start,self).__init__(config)
      me.logger.info("Constructed StubProcessor_start: extends Processor")
      self.jobTuple = (1,'someUuid',0)

    def incomingJobStream(self,databaseCursor):
      me.logger.info("#Yield#%s#",self.jobTuple)
      yield self.jobTuple
    def submitJobToThreads(self,databaseCursor,aJobTuple):
      me.logger.info("#Submitted#%s#",aJobTuple)
      assert self.jobTuple == aJobTuple, 'Expect submitted % == incoming %'%(self.jobTuple,aJobTuple)
      time.sleep(.09)
    def cleanup(self):
      me.logger.info("#Cleanup#void#")
      super(TestProcessor.StubProcessor_start,self).cleanup()

  def _runStartChild(self):
    global me
    try:
      theProcessor = TestProcessor.StubProcessor_start(me.config)
      theProcessor.start()
      assert False, 'Cannot get to this line: Parent will kill'
    # following sequence of except: handles both 2.4.x and 2.5.x hierarchy
    except SystemExit,x:
      me.logger.info("CHILD SystemExit in %s: %s [%s]"%(threading.currentThread().getName(),type(x),x))
      os._exit(0)
    except KeyboardInterrupt,x:
      me.logger.info("CHILD KeyboardInterrupt in %s: %s [%s]"%(threading.currentThread().getName(),type(x),x))
      os._exit(0)
    except Exception,x:
      me.logger.info("CHILD Exception in %s: %s [%s]"%(threading.currentThread().getName(),type(x),x))
      os._exit(0)

  def _pause1(self):
    time.sleep(.1)
    return True

  def testStart(self):
    """
    testStart(self):
    This test will probably run under 1 second.
    start does:
      until KeyboardInterrupt:
        get a job from incomingJobStream()
        submitJobToThreads(that job)
      self.cleanup()
    We stub out the three methods, with logging, examine the log to assure they are seen in order
    We cheat on the stopCondition: It is very difficult to get it right, so we just sleep(). Ugh.
    """
    global me
    self.markLog()
    try:
      tutil.runInOtherProcess(self._runStartChild, stopCondition=self._pause1, logger=me.logger)
    finally:
      self.markLog()
    seg = self.extractLogSegment()
    yields = 0
    submits = 0
    cleanups = 0
    recentYieldVal = ''
    for line in seg:
      if '- #' in line:
        assert 'INFO' in line, 'Expect only info logging from stub methods, but got %s'%line
        d0,what,val,d0 = line.split('#')
        if 'Cleanup' == what:
          assert yields > 0, 'must see at least one yield before cleanup, but saw none'
          assert submits > 0, 'must see at least one submit before cleanup, but saw none'
          cleanups += 1
        elif 'Submitted' == what:
          assert 0 == cleanups, 'must not see cleanup until after all submits'
          assert yields > submits, 'must see a yield before each submit but yields=%s, submits=%s'%(yields,submits)
          assert recentYieldVal == val, 'expect equal values but yielded %s submitted %s'%(recentYieldVal,val)
          submits += 1
        elif 'Yield' == what:
          assert 0 == cleanups, 'must not see cleanup until after all yields'
          assert yields == submits, 'all prior yields must have been submitted'
          recentYieldVal = val
          yields += 1
        else:
          assert False, 'Expect only Cleanup, Submitted and Yield lines'
    assert 1 == cleanups, 'Can only see one cleanup, but %s'%cleanups

  def testRespondToSIGHUP(self):
    """
    testRespondToSIGHUP(self):
    This test may run for a second or two
      We should notice a SIGHUP and die nicely. This is exactly like testStart except that we look
      for different logging events (ugh)
    """
    global me
    self.markLog()
    try:
      tutil.runInOtherProcess(self._runStartChild,logger=me.logger,signal=signal.SIGHUP)
    finally:
      self.markLog()
    seg = self.extractLogSegment()
    sighup = 0
    sigterm = 0
    for line in seg:
      if loglineRE.match(line):
        date,time,level,dash,msg = line.split(None,4)
        if msg.startswith('MainThread'):
          if 'SIGHUP detected' in msg: sighup += 1
          if 'SIGTERM detected' in msg: sigterm += 1
    assert 1 == sighup, 'Better see exactly one sighup event, got %d' % (sighup)
    assert 0 == sigterm, 'Better not see sigterm event, got %d' % (sigterm)

  def testRespondToSIGTERM(self):
    """
    testRespondToSIGTERM(self):
    This test may run for a second or two
      We should notice a SIGTERM and die nicely. This is exactly like testStart except that we look
      for different logging events (ugh)
    """
    global me
    self.markLog()
    try:
      tutil.runInOtherProcess(self._runStartChild,logger=me.logger,signal=signal.SIGTERM)
    finally:
      self.markLog()
    seg = self.extractLogSegment()
    sighup = 0
    sigterm = 0
    for line in seg:
      if loglineRE.match(line):
        date,time,level,dash,msg = line.split(None,4)
        if msg.startswith('MainThread'):
          if 'SIGTERM detected' in msg: sigterm += 1
          if 'SIGHUP detected' in msg: sighup += 1
    assert 1 == sigterm, 'Better see exactly one sigterm event, got %d' % (sigterm)
    assert 0 == sighup, 'Better not see sighup event, got %d' % (sighup)

  def testQuitCheck(self):
    """
    testQuitCheck(self):
    This test makes sure that the main loop notices when it has been told to quit.
    """
    global me
    p = processor.Processor(me.config)
    p.quit = True
    assert_raises(KeyboardInterrupt,p.quitCheck)

  def _quitter(self):
    time.sleep(self.timeTilQuit)
    self.p.quit = True

  def testResponsiveSleep(self):
    """
    testResponsiveSleep(self): (slow=3)
    This test may run for some few seconds. Shouldn't be more than 6 tops (and if so, it will have failed).
    Tests that the responsiveSleep method actually responds by raising KeyboardInterrupt.
    """
    global me
    p = processor.Processor(me.config)
    p.processorLoopTime = 1
    self.timeTilQuit = 2
    self.p = p
    _quitter = threading.Thread(name='Quitter', target=self._quitter)
    _quitter.start()
    assert_raises(KeyboardInterrupt,p.responsiveSleep,5)
    _quitter.join()

  def testCheckin(self):
    """
    testCheckin(self):
      checkin should update the internal and database last seen stamps if internal stamp is old enough
      checkin should do nothing if internal stamp is sufficiently young, regardless of db stamp
    """
    global me
    sqlS = "select lastseendatetime from processors where id = %s"
    sqlU = "UPDATE processors SET lastseendatetime = %s WHERE id = %s"
    dummyDT = dt.datetime(2006, 6, 6)
    cur = self.connection.cursor();
    nowDTd = dbtestutil.datetimeNow(cur)
    nowDTm = dt.datetime.now()
    p = processor.Processor(me.config)

    # Check initial state: Internal is very old, dbstamp is 'now'
    cur.execute(sqlS,(p.processorId,))
    self.connection.commit()
    dbStamp0 = cur.fetchone()[0] # sql:now() from p constructor
    procStamp0 = p.lastCheckInTimestamp # should be 1950
    assert procStamp0 < nowDTd,"Expect that constructed in-memory timestamp (%s) < 'now' (%s)"%(p.lastCheckInTimestamp,nowDT)
    assert nowDTd < dbStamp0,"Expect 'now' (%s) < processors.lastseendatetime (%s) at least a little bit"%(nowDT,dbStamp0)

    # Check that first call to checkin updates internal and database timestamps
    p.checkin()
    procStamp1 = p.lastCheckInTimestamp
    cur.execute(sqlS,(p.processorId,))
    dbStamp1 = cur.fetchone()[0]
    self.connection.commit()
    nowDT1 = dt.datetime.now()
    assert nowDTm < procStamp1
    assert procStamp1 < nowDT1
    assert nowDTm < dbStamp1
    assert dbStamp0 < dbStamp1
    assert dbStamp1 < nowDT1

    # Check that immediate subsequent checkin does nothing to internal or db stamp
    p.checkin()
    assert procStamp1 == p.lastCheckInTimestamp
    cur.execute(sqlS,(p.processorId,))
    assert dbStamp1 == cur.fetchone()[0]
    self.connection.commit()

    # Check that changing the database stamp still doesn't cause checkin to fire
    cur.execute(sqlU,(dummyDT,p.processorId,))
    self.connection.commit()
    cur.execute(sqlS,(p.processorId,))
    dbStamp1 = cur.fetchone()[0]
    assert dbStamp1 == dummyDT, 'It had better. But I got %s, not %s'%(dbStamp1,dummyDT)
    p.checkin()
    cur.execute(sqlS,(p.processorId,))
    dbStamp2 = cur.fetchone()[0]
    self.connection.commit()
    procStamp2 = p.lastCheckInTimestamp
    assert procStamp1 == procStamp2, 'Expect checkin does nothing, but prior: %s current: %s'%(procStamp1,procStamp2)
    assert dbStamp2 == dummyDT, 'Expect to get what was put (checkin looks at internal state), but %s != %s'%(dbStamp2,dummyDT)

    # Check that a change to the internal state without calling checkin is nilpotent
    p.lastCheckInTimestamp = dummyDT
    cur.execute(sqlS,(p.processorId,))
    dbStamp2 = cur.fetchone()[0]
    self.connection.commit()
    assert dbStamp2 == dummyDT, "changedinternal state but didn't call checkin yet: but %s != %s"%(dbStamp2,dummyDT)
    me.logger.clear()
    try:
      nowDT = dt.datetime.now()
      p.checkin()
      cur.execute(sqlS,(p.processorId,))
      dbStamp3 = cur.fetchone()[0]
      assert (dbStamp3 - nowDT).microseconds >= 0, 'Expect a little time to pass, but %s - %s'%(dbstamp3,nowDT)
      assert (dbStamp3 - nowDT).microseconds < 3000, 'Expect only a little time to pass, but %s - %s'%(dbstamp3,nowDT)
      p.checkin()
      cur.execute(sqlS,(p.processorId,))
      dbStamp4 = cur.fetchone()[0]
      assert dbStamp3 == dbStamp4, 'Expect that second checkin does nothing, but %s != %s'%(dbStamp3, dbStamp4)
    finally:
      self.connection.commit()
    # I expect someone to re-spell the log message to reflect reality, so lets do this kinda klunky. K?
    assert 1 == len(me.logger.buffer), 'Even though we ran checkin() two times, the second should just return quietly. Len=%s'%(len(me.logger.buffer))
    assert 'updating' in me.logger.buffer[0]
    assert 'processor' in me.logger.buffer[0]
    assert 'table registration' in me.logger.buffer[0]

  def testCleanup(self):
    """
    testCleanup(self):
      cleanup should remove table priority_jobs_1 (in this case). Test it did exist and was dropped
      prior to cleanup, processors.lastseendatetime should be nearly current. Test for that.
      cleanup should set our processors.lastseendatetime to at least a year ago (Code: January 1999)
    """
    global me
    p = processor.Processor(me.config)
    cur = self.connection.cursor()
    priorityTables = db_postgresql.tablesMatchingPattern(p.priorityJobsTableName,cur)
    assert 1 == len(priorityTables), 'Processor __init__ makes exactly one. But %s'%(str(priorityTables))
    assert priorityTables[0] == p.priorityJobsTableName, 'But got %s, not %s'%(priorityTables[0],p.priorityJobsTableName)
    nowDTd = dbtestutil.datetimeNow(cur)
    sqlS = "select lastseendatetime from processors where id = %s"
    cur.execute(sqlS,(p.processorId,))
    val = cur.fetchone();
    dbStamp0 = val[0]
    cur.connection.commit()
    assert dbStamp0 < nowDTd, 'constructed dt: %s then a moment later dt: %s'%(dbStamp0,nowDTd)
    assert (nowDTd - dbStamp0).seconds < 1, 'Expect only a little time to pass, but %s - %s'%(nowDTd,dbStamp0)
    p.cleanup()
    priorityTables = db_postgresql.tablesMatchingPattern(p.priorityJobsTableName,cur)
    assert 0 == len(priorityTables), "Expect cleanup removed p's priority jobs table. But %s"%(str(priorityTables))
    cur.execute(sqlS,(p.processorId,))
    self.connection.commit()
    dbStamp1 = cur.fetchone()[0]
    # as of 2009-Feb, the year is in fact 1999
    assert dbStamp1.year < nowDTd.year, 'at least. But dbStamp1: %s and nowDT: %s'%(dbStamp1,nowDTd)
    # Assume that someday a test of threadManager proves that calling its waitForCompletion() works.

  def _markJobDuringTesting(self, jobTuple):
    sql = "UPDATE jobs SET starteddatetime = %s WHERE id = %s"
    now = dt.datetime.now()
    cursor = self.connection.cursor()
    jobId = jobTuple[0]
    cursor.execute(sql,(now,jobId,))
    self.connection.commit()
    self._removeJobFromTables(jobTuple)

  def _removeJobFromTables(self, jobTuple):
    global me
    cursor = self.connection.cursor()
    jobUuid = jobTuple[1]
    tableNames = ('priorityjobs',self.processor.priorityJobsTableName)
    sql = "delete from %s where uuid = '%s';"
    for t in tableNames:
      try:
        cursor.execute(sql%(t,jobUuid))
        self.connection.commit()
      except Exception,x:
        me.logger.error("Unable to delete: %s: %s",type(x),x)
        self.connection.rollback()
        raise

  def _dumpJobTables(self, title):
    global me
    tableNames = ('jobs','priorityjobs',self.processor.priorityJobsTableName)
    sql = 'select * from %s'
    results = ['DUMP JOB TABLES WITH %s'%title]
    cur = self.connection.cursor()
    for tn in tableNames:
      cur.execute(sql%tn)
      results.append(' -- %s --'%tn)
      results.extend(cur.fetchall())
    self.connection.commit()
    for r in results:
      me.logger.debug(r)

  def incomingJobStreamTester(self):
    """
    Can be called directly for several tests, but must be in a thread for at least one. Hence the reliance
    on a variety of testing data as self attributes
    """
    global me
    ijs = self.processor.incomingJobStream(self.connection.cursor())
    expectedPriorityIds = getattr(self,'expectedPriorityIds',set())
    expectedNormalIds = getattr(self,'expectedNormalIds',set())
    seenPriorityIds = set()
    seenNormalIds = set()
    if not set() == expectedPriorityIds.intersection(expectedNormalIds):
      me.logger.error('expectedPriorityIds: %s should have nothing in common with expectedNormalIds: %s',expectedPriorityIds,expectedNormalIds)
    assert set() == expectedPriorityIds.intersection(expectedNormalIds)
    expectedJobCount = len(expectedPriorityIds|expectedNormalIds)

    handleJobFunction = getattr(self,'jobHandlingFunction', self._markJobDuringTesting)
    slowDownAmount = getattr(self,'slowDownAmount',0)
    seenJobCount = 0
    seenNormal = False
    try:
      while True:
        j = ijs.next()
        if j:
          if j[0] in expectedPriorityIds:
            if self.checkPriorityOrdering:
              if seenNormal:
                me.logger.error('%s - We should see all priority jobs before seeing any normal jobs but pri: %s vs norm %s and now %s',threading.currentThread().getName(),seenPriorityIds,seenNormalIds,j)
              assert not seenNormal
            seenPriorityIds.add(j[0])
          elif j[0] in expectedNormalIds:
            seenNormal = True
            seenNormalIds.add(j[0])
          else:
            me.logger.error('%s - Job %s was not expected as either priority or normal',threading.currentThread().getName(),j)
            assert False, "Job %s was not expected as either priority or normal"%(str(j))
          time.sleep(slowDownAmount)
          handleJobFunction(j)
          seenJobCount += 1
        if seenJobCount >= expectedJobCount:
          #me.logger.debug("TestLog - seenPriorityIds = %s :: %s",seenPriorityIds,threading.currentThread().getName())
          #me.logger.debug("TestLog - seenNormalIds = %s :: %s",seenNormalIds,threading.currentThread().getName())
          break
    except KeyboardInterrupt,x:
      me.logger.info("%s - Caught KeyboardInterrupt",threading.currentThread().getName())
    except Exception,x:
      me.logger.info("%s - Caught unexpected %s: %s",threading.currentThread().getName(),type(x),x)
      raise
    assert expectedNormalIds == seenNormalIds, 'But got expected: %s versus %s'%(expectedNormalIds,seenNormalIds)
    assert expectedPriorityIds == seenPriorityIds, 'But got expected: %s versus %s'%(expectedPriorityIds,seenPriorityIds)

  def testIncomingJobStream_NoJobs(self):
    """
    testProcessor:TestProcessor.testIncomingJobStream_NoJobs(self): (slow=3)
      If there are no jobs, should see 'no jobs to do' in the logfile once per processorLoopTime
      When we set quit=True, should see a KeyboardInterrupt exception
    """
    global me
    p = processor.Processor(me.config)
    self.processor = p
    p.processorLoopTime=1
    self.markLog()
    try:
      driver = threading.Thread(name="IncomingJobStreamDriver",target=self.incomingJobStreamTester)
      driver.start()
      driver.join(0.5 +p.processorLoopTime)
      p.quit = True
    finally:
      self.markLog()
      p.quit = True
    seg = self.extractLogSegment()
    gotjob=0
    caught=0
    nojob=0
    assert 2 <= len(seg), "Expect two 'no jobs' and no other log entries. Got %s"%(str(seg))
    for line in seg:
      if 'INFO' in line:
        if 'no jobs to do - sleeping' in line: nojob += 1
        if 'GOT A JOB' in line: gotjob += 1
        if 'CAUGHT KeyboardInterrupt' in line: caught += 1
    assert gotjob == 0, "Didn't have any jobs to stream, but found at least one in logs: %s"%(str(seg))
    assert caught == 0, "Expected no CAUGHT line, got %s\n%s"%(caught,str(seg))
    assert nojob == 2, "Expected two 'no jobs' lines, got %s\n%s"%(nojob,str(seg))

  def testIncomingJobStream_NormalJobs(self):
    """
    testIncomingJobStream_NormalJobs(self):
      expect that if there are items in jobs table, we will find them
    """
    global me
    cur = self.connection.cursor()
    p = processor.Processor(me.config)
    p.config['checkForPriorityFrequency'] = dt.timedelta(milliseconds=100)
    p.processorLoopTime = 1
    normalJobsExpected = 3
    dbtestutil.addSomeJobs(cur,{1:normalJobsExpected} ,logger=me.logger)
    self.expectedNormalIds = set(range(1,normalJobsExpected+1))
    self.processor = p
    try:
      self.incomingJobStreamTester()
    finally:
      p.quit = True

  def testIncomingJobStream_NormalAndPriorityJobs(self):
    """
    testIncomingJobStream_NormalAndPriorityJobs(self):
      expect jobs are treated as normal unless seen also in priority_jobs_N table (No backward compatible prioritization)
      expect jobs in priority_jobs_N table are treated as priority
      expect that jobs in priorityjobs table are not treated as priority: Monitor marks them into priority_jobs_N
      expect that every priority job is seen before any non-priority job
      do NOT expect any particular order within priority jobs nor within normal jobs
    """
    global me
    cur = self.connection.cursor()
    p = processor.Processor(me.config)
    priorityJobCountInJobs = 1 # set jobs table priority column, (but ignore it)
    priorityJobCountInOwnPriority = 2 # look in priority_jobs_1 table
    jobCountInPriority = 1 # look in priorityjobs table
    jobCountNormal = 2 # look in jobs table, but priority column is null/0
    sumJobCount = priorityJobCountInJobs+priorityJobCountInOwnPriority+jobCountInPriority+jobCountNormal
    dbtestutil.addSomeJobs(cur,{1:sumJobCount} ,logger=me.logger)
    cur.execute("SELECT id from jobs")
    jobIds = [x[0] for x in cur.fetchall()]
    self.connection.commit()
    expectedJobIds = [x for x in range(1,sumJobCount+1)]
    assert set(jobIds) == set(expectedJobIds), 'Setup assurance. But got expected % vs %s'%(str(expectedJobIds),str(jobIds))
    dbtestutil.setPriority(cur,jobIds[:priorityJobCountInJobs])
    self.expectedNormalIds = set(jobIds[:priorityJobCountInJobs])
    dbtestutil.setPriority(cur,jobIds[priorityJobCountInJobs:priorityJobCountInJobs+priorityJobCountInOwnPriority],p.priorityJobsTableName)
    self.expectedPriorityIds = set(jobIds[priorityJobCountInJobs:priorityJobCountInJobs+priorityJobCountInOwnPriority])
    dbtestutil.setPriority(cur,jobIds[priorityJobCountInJobs+priorityJobCountInOwnPriority:],'priorityjobs')
    self.expectedNormalIds.update(jobIds[priorityJobCountInJobs+priorityJobCountInOwnPriority:])
    self.checkPriorityOrdering = True
    self.processor = p
    me.logger.clear()
    self.incomingJobStreamTester()
    loggedPriorities = set()
    loggedNormals = set()
    for i in range(len(me.logger.buffer)):
      line = me.logger.buffer[i]
      level = me.logger.levels[i]
      assert level != logging.ERROR, 'Expect no ERROR logs, but %s'%line
      if 'MainThread' in line:
        if 'incomingJobStream yielding' in line:
          car,cdr = line.split('(',1)
          id = int(cdr[0])
          if 'priority' in car: loggedPriorities.add(id)
          if 'standard' in car: loggedNormals.add(id)
    assert self.expectedPriorityIds == loggedPriorities, 'But expected = %s vs %s'%(self.expectedPriorityIds,loggedPriorities)
    assert self.expectedNormalIds == loggedNormals, 'But expected = %s vs %s'%(self.expectedNormalIds,loggedNormals)

  def testIncomingJobStream_StopsForMore(self):
    """
    testIncomingJobStream_StopsForMore(self):
      with normal jobs running slow, a newly inserted priority job must be found before normals finish
    """
    global me
    cur = self.connection.cursor()
    p = processor.Processor(me.config)
    p.config['checkForPriorityFrequency'] = dt.timedelta(milliseconds=100)
    totalJobsExpected = 6
    data = dbtestutil.addSomeJobs(cur,{1:totalJobsExpected})
    cur.execute("SELECT id from jobs")
    jobIds = [ x[0] for x in cur.fetchall() ]
    ijs = p.incomingJobStream(cur)
    job = ijs.next()
    seenId = job[0]
    jobIds.remove(seenId)
    priIds = set( (jobIds[i] for i in range(0,len(jobIds),2)) )
    normIds = set(jobIds) - set(priIds)
    me.logger.debug("HERE ids:%s, pri:%s, norm:%s",jobIds,priIds,normIds)
    dbtestutil.setPriority(cur,priIds,p.priorityJobsTableName)
    cur.execute("select j.id,j.uuid,j.priority from jobs j, %s p where j.uuid = p.uuid"%p.priorityJobsTableName)
    for i in cur.fetchall():
      me.logger.debug("A PRI  %s",i)
    self.connection.commit()
    time.sleep(.5) # slow down enough to let the job-generator loop over
    for i in range(len(jobIds)):
      aJob = ijs.next()
      me.logger.debug("Job %s",aJob)
      if priIds:
        assert aJob[0] in priIds
        priIds.remove(aJob[0])
      else:
        assert aJob[0] in normIds, 'Expect %s in normIds: %s'%(aJob[0],str(normIds))

  class BogusThreadManager:
    def newTask(self,threadJob,data):
      global me
      me.logger.info("BogusThread - %s handling %s",threadJob,data)

  def testSubmitJobToThreads(self):
    """
    testSubmitJobToThreads(self):
      check that submitting a job sets jobs.starteddatetime to a reasonable value
      check that Processor's thread manager is in use
      check that we remark about queueing the appropriate job
    """
    cur = self.connection.cursor()
    p = processor.Processor(me.config)
    p.threadManager = TestProcessor.BogusThreadManager()
    cur = self.connection.cursor()
    dbtestutil.addSomeJobs(cur,{1:1} ,logger=me.logger)
    cur.execute('SELECT id,uuid,priority,starteddatetime from jobs')
    id,uuid,priority,startedDT = cur.fetchall()[0]
    self.connection.commit()
    assert id == 1, 'but %s'%id
    assert priority == 0, 'but %s'%priority
    assert not startedDT, 'but %s'%startedDT
    before = dt.datetime.now()
    me.logger.clear()
    p.submitJobToThreads(cur,(id,uuid,priority,))
    after = dt.datetime.now()
    cur.execute('SELECT id,uuid,priority,starteddatetime from jobs')
    id,uuid,priority,startedDT = cur.fetchall()[0]
    self.connection.commit()
    assert startedDT > before, 'but started %s, versus now: %s'%(startedDT, before)
    assert after > startedDT, 'but later %s, versus started: %s'%(after,startedDT)
    bogosity = 0
    queueing = 0
    for i in range(len(me.logger.buffer)):
      line = me.logger.buffer[i]
      if 'BogusThread' in line: bogosity += 1
      if 'MainThread' in line:
        if 'queuing job' in line:
          if 'job 1' in line:
            queueing += 1
          else:
            queueing = -99
    assert 1 == bogosity, 'Expect one logging line from the BogusThread Manager, but got %s'%bogosity
    assert 1 == queueing, 'Expect one logging line about queueing a job, and must be job 1. Got %s'%queueing

  def testProcessJob_NoStorage(self):
    """
    testProcessJob_NoStorage(self):
      check that we fail appropriately when there is no json file in expected location
    """
    global me
    cur = self.connection.cursor()
    p = processor.Processor(me.config)
    dbtestutil.addSomeJobs(cur,{1:1})
    sql = 'select id,uuid,owner,priority,queueddatetime,starteddatetime,completeddatetime,success,message from jobs'
    cur.execute(sql)
    data0 = cur.fetchall()
    self.connection.commit()
    me.logger.clear()
    p.processJob((data0[0][0],data0[0][1],data0[0][3],))
    errs = 0
    caught = 0
    id = 0
    for i in range(len(me.logger.buffer)):
      line = me.logger.buffer[i]
      level = me.logger.levels[i]
      if logging.ERROR == level:
        errs += 1
        if 'Caught Error:' in line and "UuidNotFoundException" in line:
          caught += 1
        if data0[0][1] in line:
          id += 1
    assert 2 == errs
    assert 1 == caught
    assert 1 == id

  def testProcessJob_JsonBadSyntax(self):
    """
    testProcessJob_JsonBadSyntax(self):
      check that we fail appropriately when the 'json' file doesn't actually contain json data
    """
    global me
    cur = self.connection.cursor()
    p = processor.Processor(me.config)
    dbtestutil.addSomeJobs(cur,{1:2})
    sql = 'select id,uuid,owner,priority,queueddatetime,starteddatetime,completeddatetime,success,message from jobs'
    cur.execute(sql)
    data0 = cur.fetchall()
    self.connection.commit()
    uuid0 = data0[0][1]
    uuid1 = data0[1][1]
    createJDS.createTestSet({uuid0:createJDS.jsonFileData[uuid0]},{'logger':me.logger},p.config.storageRoot)
    createJDS.createTestSet({uuid1:createJDS.jsonFileData[uuid1]},{'logger':me.logger,'jsonIsEmpty':True},p.config.deferredStorageRoot)

    me.logger.clear()
    # try a bad-syntax json file
    p.processJob((data0[0][0],uuid0,data0[0][3],))
    errs = 0
    caught = 0
    id = 0
    noJson = 0
    toplen = len(me.logger.buffer)
    for i in range(len(me.logger.buffer)):
      line = me.logger.buffer[i]
      level = me.logger.levels[i]
      if logging.ERROR == level:
        errs += 1
        if 'Caught Error:' in line:
          caught += 1
        if data0[0][1] in line:
          id += 1
        if 'No JSON object could be decoded' in line:
          noJson += 1
    assert 2 == errs
    assert 1 == caught
    assert 1 == noJson
    # try an empty json file
    p.processJob((data0[1][0],uuid1,data0[1][3],))
    for i in range(toplen,len(me.logger.buffer)):
      line = me.logger.buffer[i]
      level = me.logger.levels[i]
      if logging.ERROR == level:
        errs += 1
        if 'Caught Error:' in line:
          caught += 1
        if data0[0][1] in line:
          id += 1
        if 'No JSON object could be decoded' in line:
          noJson += 1
    assert 4 == errs,"but %s"%errs
    assert 2 == caught
    assert 2 == noJson
    assert 0 == id

  class StubProcessor_processJob(processor.Processor):
    def __init__(self, config):
      super(TestProcessor.StubProcessor_processJob, self).__init__(config)
      me.logger.info("Constructed StubProcessor_processJob: extends Processor")
      self.reportIdToReport = 1

    def insertReportIntoDatabase(self,threadLocalCursor,jobUuid,jsonDocument,jobPathname,date_processed,processorErrorMessages):
      me.logger.info("#jobUuid#%s#",jobUuid)
      me.logger.info("#jsonDocument#%s#", simplejson.dumps(jsonDocument))
      me.logger.info("#jobPathname#%s#",jobPathname)
      me.logger.info("#date_processed#%s#", date_processed)
      me.logger.info("#processorErrorMessages#%s#",processorErrorMessages)
      reportRecordAsDict = { "id": self.reportIdToReport,
                             "uuid": jobUuid,
                             "client_crash_date": dt.datetime.now(),
                             "date_processed": dt.datetime.now(),
                             'install_age': 'install_age',
                             'last_crash': 'last_crash',
                             'uptime': 'uptime',
                             'user_comments': 'user_comments',
                             'app_notes': 'app_notes',
                             'distributor': 'distributor',
                             'distributor_version': 'distributor_version',
                             'signaturedims_id':None,
                             'productdims_id':1,
                             'osdims_id':None,}
      return reportRecordAsDict

    def doBreakpadStackDumpAnalysis(self, reportId, jobUuid, dumpfilePathname, threadLocalCursor,date_processed, processorErrorMessages):
      assert self.reportIdToReport == reportId, 'Because that is what we told it, but got %s'%reportId
      return {"signature": "aSignature", "processor_notes": "some Processor notes", "truncated": False, "dump": "...the dump..."}

  def testProcessJob_LegalJson(self):
    """
    testProcessJob_LegalJson(self):
      test that we parse the (useless) test json file as expected.
    """
    global me
    cur = self.connection.cursor()
    # Avoid trying to insert into database or do breakpad stack dump analysis: Use StubProcessor
    p = TestProcessor.StubProcessor_processJob(me.config)
    dbtestutil.addSomeJobs(cur,{1:2})
    sql = 'select id,uuid,owner,priority,queueddatetime,starteddatetime,completeddatetime,success,message from jobs'
    cur.execute(sql)
    data0 = cur.fetchall()
    self.connection.commit()
    uuid0 = data0[0][1]
    uuid1 = data0[1][1]
    createJDS.createTestSet({uuid0:createJDS.jsonFileData[uuid0]},{'logger':me.logger,'jsonIsBogus':False},p.config.storageRoot)
    createJDS.createTestSet({uuid1:createJDS.jsonFileData[uuid1]},{'logger':me.logger,'jsonIsBogus':False},p.config.deferredStorageRoot)
    me.logger.clear()

    stamp0 = dt.datetime.now()
    p.processJob((data0[0][0],data0[0][1],data0[0][3],))
    p.processJob((data0[1][0],data0[1][1],data0[1][3],))

    stamp1 = dt.datetime.now()
    cur.execute(sql)
    data1 = cur.fetchall()
    self.connection.commit()
    for i in data0:
      assert i[5] == None #started
      assert i[6] == None #completed
      assert i[7] == None #success
    for i in data1:
      assert stamp0 < i[5] < stamp1 #started
      assert stamp0 < i[6] < stamp1 #completed
      assert i[7] #success

    errs = 0
    warns = 0
    caught = 0
    noJson = 0
    reportDates = 0
    buildDates = 0
    hashCount = 0
    for i in range(len(me.logger.levels)):
      line = me.logger.buffer[i]
      level = me.logger.levels[i]
      if 'No JSON object could be decoded' in line: noJson += 1
      if logging.WARNING == level:
        warns += 1
        if 'Caught Error:' in line: caught += 1
      if logging.ERROR == level: errs += 1
      if logging.INFO == level:
        if '#' in line:
          hashCount += 1
          d,key,val,dd = line.split('#')
          if key=='jobUuid': curUuid = val
          if key == 'jsonDocument' or key == 'jobPathname':
            assert curUuid in val, 'expected %s to be found in %s [%s]'%(curUuid,key,val)

    assert 0 == errs, 'expect 2 from each file got %s'%errs
    assert 0 == warns, 'expect none with replaced method, got %s'%warns
    assert 0 == caught, 'expect none with replaced method, got %s'%caught
    assert 0 == noJson, 'better not see any Json syntax issues, got%s'%noJson
    assert 10 == hashCount, 'expect 5 in each job, got %s'%hashCount

  def testDoBreakpadStackDumpAnalysis(self):
    """
    testDoBreakpadStackDumpAnalysis(self):
      check that the method in base Processor class raises an Exception
    """
    global me
    p = processor.Processor(me.config)
    assert_raises(Exception,p.doBreakpadStackDumpAnalysis,('','','','','','',))

  def testJsonPathForUuidInJsonDumpStorage(self):
    """
    testJsonPathForUuidInJsonDumpStorage(self):
      check that we find the file in either correct place
      check that we raise appropriate assertion if not fount
    """
    global me
    p = processor.Processor(me.config)
    data = dbtestutil.makeJobDetails({1:2})
    uuid0 = data[0][1]
    uuid1 = data[1][1]
    createJDS.createTestSet({uuid0:createJDS.jsonFileData[uuid0]},{'logger':me.logger},p.config.storageRoot)
    createJDS.createTestSet({uuid1:createJDS.jsonFileData[uuid1]},{'logger':me.logger},p.config.deferredStorageRoot)
    data0 = createJDS.jsonFileData[uuid0]
    data1 = createJDS.jsonFileData[uuid1]
    dy0 = ''.join(data0[0].split('-')[:3])
    dy1 = ''.join(data1[0].split('-')[:3])
    p0 = os.sep.join((p.config.storageRoot.rstrip(os.path.sep),dy0,'name',createJDS.jsonFileData[uuid0][2], uuid0+'.json'))
    p1 = os.sep.join((p.config.deferredStorageRoot.rstrip(os.path.sep),dy1,'name',createJDS.jsonFileData[uuid1][2], uuid1+'.json',))
    assert p0 == p.jsonPathForUuidInJsonDumpStorage(uuid0)
    assert p1 == p.jsonPathForUuidInJsonDumpStorage(uuid1)
    assert_raises(processor.UuidNotFoundException,p.jsonPathForUuidInJsonDumpStorage,createJDS.jsonBadUuid)

  def testDumpPathForUuidInJsonDumpStorage(self):
    """
    testDumpPathForUuidInJsonDumpStorage(self):
      check that we find the file in either correct place
      check that we raise appropriate assertion if not fount
    """
    global me
    p = processor.Processor(me.config)
    data = dbtestutil.makeJobDetails({1:2})
    uuid0 = data[0][1]
    uuid1 = data[1][1]
    createJDS.createTestSet({uuid0:createJDS.jsonFileData[uuid0]},{'logger':me.logger},p.config.storageRoot)
    createJDS.createTestSet({uuid1:createJDS.jsonFileData[uuid1]},{'logger':me.logger},p.config.deferredStorageRoot)
    data0 = createJDS.jsonFileData[uuid0]
    data1 = createJDS.jsonFileData[uuid1]
    dy0 = ''.join(data0[0].split('-')[:3])
    dy1 = ''.join(data1[0].split('-')[:3])
    p0 = os.sep.join((p.config.storageRoot.rstrip(os.path.sep),dy0,'name',createJDS.jsonFileData[uuid0][2], uuid0+'.dump'))
    p1 = os.sep.join((p.config.deferredStorageRoot.rstrip(os.path.sep),dy1,'name',createJDS.jsonFileData[uuid1][2], uuid1+'.dump',))
    assert p0 == p.dumpPathForUuidInJsonDumpStorage(uuid0)
    assert p1 == p.dumpPathForUuidInJsonDumpStorage(uuid1)
    assert_raises(processor.UuidNotFoundException,p.dumpPathForUuidInJsonDumpStorage,createJDS.jsonBadUuid)

  def testMoveJobFromLegacyToStandardStorage(self):
    """
    testMoveJobFromLegacyToStandardStorage(self):
      do nothing 'til you hear from somebody that you should have already done it.
    """
    assert True, "Expect this task is no longer used, and in any case it is tested elsewhere"

  def testGetJsonOrWarn(self):
    """
    testGetJsonOrWarn(self):
    """
    global me
    p = processor.Processor(me.config)
    me.logger.clear()
    messages = []
    val = p.getJsonOrWarn({},'any',messages)
    assert None == val
    assert 0 == len(me.logger.buffer)
    assert 1 == len(messages)
    assert 'WARNING: Json file missing any' == messages[0], "But got [%s]"%messages[0]
    messages = []
    val = p.getJsonOrWarn({'key':'too long'},'any',messages,333,3)
    assert 333 == val
    assert 0 == len(me.logger.buffer)
    assert 1 == len(messages)
    assert 'WARNING: Json file missing any' == messages[0], "But got [%s]"%messages[0]
    messages = []
    val = p.getJsonOrWarn({'key':'too long'},'key',messages,333,3)
    assert 'too' == val
    assert 0 == len(me.logger.buffer)
    assert 0 == len(messages)
    messages = []
    val = p.getJsonOrWarn(33,'key',messages,333,3)
    assert 1 == len(me.logger.buffer)
    assert logging.ERROR == me.logger.levels[0]
    assert "While extracting 'key' from jsonDoc" in me.logger.buffer[0], 'But log is %s'%me.logger.buffer[0]
    assert 1 == len(messages)
    assert "ERROR: jsonDoc['key']:" in messages[0], "but %s"%(str(messages))
    assert "unsubscriptable" in messages[0], "but %s"%(str(messages))

  def testInsertReportIntoDatabase_VariousBadFormat(self):
    """
    testInsertReportIntoDatabase_VariousBadFormat(self):
      check that we get appropriate errors for missing bits and pieces
      check that we get appropriate truncations for overlong fields
    """
    global me
    p = processor.Processor(me.config)
    data = dbtestutil.makeJobDetails({1:1})
    uuid = data[0][1]
    createJDS.createTestSet({uuid:createJDS.jsonFileData[uuid]},{'logger':me.logger},p.config.storageRoot)
    path = p.jsonPathForUuidInJsonDumpStorage(uuid)
    con,cur = p.databaseConnectionPool.connectionCursorPair()
    try:
      jsonDoc = {}
      messages = []
      now = dt.datetime.now()
      p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,messages)
      assert 5 == len(messages)
      expectedMessages = [
        "WARNING: Json file missing ProductName",
        "WARNING: Json file missing Version",
        "WARNING: Json file missing BuildID",
        "WARNING: Json file missing CrashTime",
        "WARNING: No 'client_crash_date' could be determined from the Json file"
        ]
      for i in range(5):
        assert expectedMessages[i] == messages[i],'Expected %s, got %s'%(expectedMessages[i],messages[i])
      cur.execute('select count(*) from reports where uuid = %s',(uuid,))
      con.commit()
      val = cur.fetchone()[0]
      assert 0 == val, 'but %s'%val

      product = 'bogus'
      version = '3.xBogus'
      buildId_notDate = '1966060699'
      jsonDoc = {'ProductName':product}
      messages = []
      p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,messages)
      expectedMessages = [
        "WARNING: Json file missing Version",
        "WARNING: Json file missing BuildID",
        "WARNING: Json file missing CrashTime",
        "WARNING: No 'client_crash_date' could be determined from the Json file"
        ]
      assert len(expectedMessages) == len(messages)
      for i in range(len(messages)):
        assert expectedMessages[i] == messages[i]
      cur.execute('select count(*) from reports where uuid = %s',(uuid,))
      con.commit()
      val = cur.fetchone()[0]
      assert 0 == val, 'but %s'%val

      jsonDoc = {'Version':version}
      messages = []
      p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,messages)
      expectedMessages = [
        "WARNING: Json file missing ProductName",
        "WARNING: Json file missing BuildID",
        "WARNING: Json file missing CrashTime",
        "WARNING: No 'client_crash_date' could be determined from the Json file"
        ]
      assert len(expectedMessages) == len(messages)
      for i in range(len(messages)):
        assert expectedMessages[i] == messages[i]
      cur.execute('select count(*) from reports where uuid = %s',(uuid,))
      con.commit()
      val = cur.fetchone()[0]
      assert 0 == val, 'but %s'%val

      jsonDoc = {'BuildID':buildId_notDate}
      messages = []
      p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,messages)
      expectedMessages = [
        "WARNING: Json file missing ProductName",
        "WARNING: Json file missing Version",
        "WARNING: Json file missing CrashTime",
        "WARNING: No 'client_crash_date' could be determined from the Json file",
        "WARNING: No 'build_date' could be determined from the Json file",
      ]
      assert len(expectedMessages) == len(messages)
      for i in range(len(messages)):
        assert expectedMessages[i] == messages[i], "at %s: Expected '%s' got '%s'"%(i,expectedMessages[i],messages[i])
      cur.execute('select count(*) from reports where uuid = %s',(uuid,))
      val = cur.fetchone()[0]
      con.commit()
      assert 0 == val, "but '%s'"%val

      jsonDoc = {'ProductName':product,'Version':version}
      messages = []
      p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,messages)
      con.commit()
      expectedMessages = [
        "WARNING: Json file missing BuildID",
        "WARNING: Json file missing CrashTime",
        "WARNING: No 'client_crash_date' could be determined from the Json file"
        ]
      assert len(expectedMessages) == len(messages)
      for i in range(len(messages)):
        assert expectedMessages[i] == messages[i]
      expectedData = [now.replace(microsecond=0),now,None,product,version,None,None]
      cur.execute('select client_crash_date,date_processed,build_date,product,version,os_name,os_version from reports where uuid = %s',(uuid,))
      val = cur.fetchall()[0]
      con.commit()
      for i in range(len(expectedData)):
        vi = val[i]
        if 0 == i : vi = dt.datetime.combine(vi.date(),vi.time())
        assert expectedData[i] == vi, 'At index %s: Expected %s, got %s'%(i,expectedData[i],vi)
      cur.execute('delete from reports where uuid = %s',(uuid,))
      con.commit()

      buildId_notDate = '1966060699'
      jsonDoc = {'ProductName':product,'Version':version,'BuildID':buildId_notDate}
      messages = []
      p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,messages)
      expectedMessages = [
        "WARNING: Json file missing CrashTime",
        "WARNING: No 'client_crash_date' could be determined from the Json file",
        "WARNING: No 'build_date' could be determined from the Json file",
        ]
      assert len(expectedMessages) == len(messages)
      for i in range(len(messages)):
        assert expectedMessages[i] == messages[i]
      expectedData = [now.replace(microsecond=0),now,product,version,None]
      cur.execute('select client_crash_date,date_processed,product,version,build_date from reports where uuid = %s',(uuid,))
      val = cur.fetchall()[0]
      con.commit()
      for i in range(len(expectedData)):
        vi = val[i]
        if 0 == i : vi = dt.datetime.combine(vi.date(),vi.time())
        assert expectedData[i] == vi, 'At index %s: Expected %s, got %s'%(i,expectedData[i],vi)
      cur.execute('delete from reports where uuid = %s',(uuid,))
      con.commit()

      product = 'a-terrifically-long-product-name'
      version = '1.2.3prebeta-98765'
      idparts = ['1989','11','12','13','-','beta1234',]
      buildId = ''.join(idparts)
      expectedBuildStamp = dt.datetime( *(int(x) for x in idparts[:4]) )
      jsonDoc = {'ProductName':product,'Version':version,'BuildID':buildId}
      messages = []
      p.insertReportIntoDatabase(cur,uuid,jsonDoc,path,now,messages)
      expectedMessages = [
        "WARNING: Json file missing CrashTime",
        "WARNING: No 'client_crash_date' could be determined from the Json file",
        ]
      assert len(expectedMessages) == len(messages)
      for i in range(len(messages)):
        assert expectedMessages[i] == messages[i]
      expectedData = [now.replace(microsecond=0),now,expectedBuildStamp,product[:30],version[:16]]
      cur.execute('select client_crash_date,date_processed,build_date,product,version from reports where uuid = %s',(uuid,))
      val = cur.fetchall()[0]
      con.commit()
      for i in range(len(expectedData)):
        vi = val[i]
        if 0 == i : vi = dt.datetime.combine(vi.date(),vi.time())
        assert expectedData[i] == vi, 'At index %s: Expected "%s", got "%s"'%(i,expectedData[i],vi)
      cur.execute('delete from reports where uuid = %s',(uuid,))
      con.commit()
    finally:
      p.databaseConnectionPool.cleanup()

  def testInsertReportIntoDatabase_CrashVsTimestamp(self):
    """
    testInsertReportIntoDatabase_CrashVsTimestamp(self):
      check that the appropriate date values are being committed to the database
    """
    global me
    p = processor.Processor(me.config)
    con,cur = p.databaseConnectionPool.connectionCursorPair()
    try:
      data = dbtestutil.makeJobDetails({1:4})
      uuid0 = data[0][1]
      uuid1 = data[1][1]
      uuid2 = data[2][1]
      uuid3 = data[3][1]
      what= {uuid0:createJDS.jsonFileData[uuid0],uuid1:createJDS.jsonFileData[uuid1], uuid2:createJDS.jsonFileData[uuid2], uuid3:createJDS.jsonFileData[uuid3]}
      createJDS.createTestSet(what,{'logger':me.logger},p.config.storageRoot)
      path0 = p.jsonPathForUuidInJsonDumpStorage(uuid0)
      path1 = p.jsonPathForUuidInJsonDumpStorage(uuid1)
      path2 = p.jsonPathForUuidInJsonDumpStorage(uuid2)
      path3 = p.jsonPathForUuidInJsonDumpStorage(uuid3)
      product = 'bogus'
      version = '3.xBogus'
      buildId = '1966060622'
      crashTime = '1234522800'
      timeStamp = str(int(crashTime)-60)
      startupTime = str(int(timeStamp)-60)
      installTime = str(int(timeStamp)-(24*60*60))
      jsonDoc0 = {'ProductName':product,'Version':version,'BuildID':buildId}
      jsonDoc1 = {'ProductName':product,'Version':version,'BuildID':buildId, 'CrashTime':crashTime,}
      jsonDoc2 = {'ProductName':product,'Version':version,'BuildID':buildId, 'timestamp':timeStamp,}
      jsonDoc3 = {'ProductName':product,'Version':version,'BuildID':buildId, 'CrashTime':crashTime, 'timestamp':timeStamp,}
      now = dt.datetime.now()
      messages = ["   == NONE"]
      p.insertReportIntoDatabase(cur,uuid0,jsonDoc0,path0,now,[])#messages)
      messages.append("   == CRASH ONLY")
      p.insertReportIntoDatabase(cur,uuid1,jsonDoc1,path1,now,[])#messages)
      messages.append("   == STAMP ONLY")
      p.insertReportIntoDatabase(cur,uuid2,jsonDoc2,path2,now,[])#messages)
      messages.append("   == BOTH")
      p.insertReportIntoDatabase(cur,uuid3,jsonDoc3,path2,now,[])#messages)
      messages.append("   == ALL DONE MESSAGES")
      # for i in messages:print i
      labels = ["\nnone","crash",'stamp','both']
      items = ['crash',"procd","age: ","last:","uptim","build",]
      expectedValues = [
        [now.replace(microsecond=0),now],
        [dt.datetime.fromtimestamp(int(crashTime)),now],
        [dt.datetime.fromtimestamp(int(timeStamp)),now],
        [dt.datetime.fromtimestamp(int(crashTime)),now],
        ]
      cur.execute("select client_crash_date,date_processed from reports where uuid in (%s,%s,%s,%s)",(uuid0,uuid1,uuid2,uuid3))
      val = cur.fetchall()
      for docIndex in range(len(val)):
        for dateIndex in range(len(val[docIndex])):
          value = val[docIndex][dateIndex]
          value = value.combine(value.date(),value.time())
          assert expectedValues[docIndex][dateIndex] == value, "But expected %s, got %s"%(expectedValues[docIndex][dateIndex],value)
      con.commit()
    finally:
      p.databaseConnectionPool.cleanup()

  def test_insertAdddonsIntoDatabase_addons_missing(self):
    p = processor.Processor(me.config)
    p.extensionsTable = DummyObjectWithExpectations()
    errorMessages = []
    assert p.insertAdddonsIntoDatabase('dummycursor', 1, {}, '2009-09-01', errorMessages) == []
    assert errorMessages == ['WARNING: Json file missing Add-ons']

  def test_insertAdddonsIntoDatabase_addons_empty(self):
    p = processor.Processor(me.config)
    p.extensionsTable = DummyObjectWithExpectations()
    errorMessages = []
    assert p.insertAdddonsIntoDatabase('dummycursor', 1, {"Add-ons":''}, '2009-09-01', errorMessages) == []
    assert errorMessages == []

  def test_insertAdddonsIntoDatabase_addons_normal_one(self):
    p = processor.Processor(me.config)
    p.extensionsTable = DummyObjectWithExpectations()
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 0, "{463F6CA5-EE3C-4be1-B7E6-7FEE11953374}", "3.0.5.1"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    errorMessages = []
    result = p.insertAdddonsIntoDatabase('dummycursor', 1, {"Add-ons":"{463F6CA5-EE3C-4be1-B7E6-7FEE11953374}:3.0.5.1"}, '2009-09-01', errorMessages)
    assert result == [["{463F6CA5-EE3C-4be1-B7E6-7FEE11953374}", "3.0.5.1"]], "got %s" % result
    assert errorMessages == []

  def test_insertAdddonsIntoDatabase_addons_normal_many(self):
    p = processor.Processor(me.config)
    p.extensionsTable = DummyObjectWithExpectations()
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 0, "{463F6CA5-EE3C-4be1-B7E6-7FEE11953374}", "3.0.5.1"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 1, "{CAFEEFAC-0016-0000-0007-ABCDEFFEDCBA}", "6.0.07"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 2, "moveplayer@movenetworks.com", "1.0.0.071101000055"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 3, "{3EC9C995-8072-4fc0-953E-4F30620D17F3}", "2.0.0.4"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 4, "{635abd67-4fe9-1b23-4f01-e679fa7484c1}", "1.6.5.200812101546"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 5, "{CAFEEFAC-0016-0000-0011-ABCDEFFEDCBA}", "6.0.11"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 6, "{972ce4c6-7e08-4474-a285-3208198ce6fd}", "3.0.6"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    errorMessages = []
    result = p.insertAdddonsIntoDatabase('dummycursor', 1, {"Add-ons":"{463F6CA5-EE3C-4be1-B7E6-7FEE11953374}:3.0.5.1,{CAFEEFAC-0016-0000-0007-ABCDEFFEDCBA}:6.0.07,moveplayer@movenetworks.com:1.0.0.071101000055,{3EC9C995-8072-4fc0-953E-4F30620D17F3}:2.0.0.4,{635abd67-4fe9-1b23-4f01-e679fa7484c1}:1.6.5.200812101546,{CAFEEFAC-0016-0000-0011-ABCDEFFEDCBA}:6.0.11,{972ce4c6-7e08-4474-a285-3208198ce6fd}:3.0.6"}, '2009-09-01', errorMessages)
    assert result == [["{463F6CA5-EE3C-4be1-B7E6-7FEE11953374}", "3.0.5.1"],
                      ["{CAFEEFAC-0016-0000-0007-ABCDEFFEDCBA}", "6.0.07"],
                      ["moveplayer@movenetworks.com", "1.0.0.071101000055"],
                      ["{3EC9C995-8072-4fc0-953E-4F30620D17F3}", "2.0.0.4"],
                      ["{635abd67-4fe9-1b23-4f01-e679fa7484c1}", "1.6.5.200812101546"],
                      ["{CAFEEFAC-0016-0000-0011-ABCDEFFEDCBA}", "6.0.11"],
                      ["{972ce4c6-7e08-4474-a285-3208198ce6fd}", "3.0.6"],
                      ], "got %s" % result
    assert errorMessages == []

  def test_insertAdddonsIntoDatabase_addons_normal_many_with_bad_one(self):
    p = processor.Processor(me.config)
    p.extensionsTable = DummyObjectWithExpectations()
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 0, "{463F6CA5-EE3C-4be1-B7E6-7FEE11953374}", "3.0.5.1"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 1, "{CAFEEFAC-0016-0000-0007-ABCDEFFEDCBA}", "6.0.07"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 2, "moveplayer@movenetworks.com", "1.0.0.071101000055"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 3, "{3EC9C995-8072-4fc0-953E-4F30620D17F3}", "2.0.0.4"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 4, "{635abd67-4fe9-1b23-4f01-e679fa7484c1}", "1.6.5.200812101546"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    p.extensionsTable.expect('insert', ('dummycursor', (1, '2009-09-01', 6, "{972ce4c6-7e08-4474-a285-3208198ce6fd}", "3.0.6"), p.databaseConnectionPool.connectToDatabase), {"date_processed": '2009-09-01'})
    errorMessages = []
    result = p.insertAdddonsIntoDatabase('dummycursor', 1, {"Add-ons":"{463F6CA5-EE3C-4be1-B7E6-7FEE11953374}:3.0.5.1,{CAFEEFAC-0016-0000-0007-ABCDEFFEDCBA}:6.0.07,moveplayer@movenetworks.com:1.0.0.071101000055,{3EC9C995-8072-4fc0-953E-4F30620D17F3}:2.0.0.4,{635abd67-4fe9-1b23-4f01-e679fa7484c1}:1.6.5.200812101546,{CAFEEFAC-0016-0000-0011-ABCDEFFEDCBA}6.0.11,{972ce4c6-7e08-4474-a285-3208198ce6fd}:3.0.6"}, '2009-09-01', errorMessages)
    assert result == [["{463F6CA5-EE3C-4be1-B7E6-7FEE11953374}", "3.0.5.1"],
                      ["{CAFEEFAC-0016-0000-0007-ABCDEFFEDCBA}", "6.0.07"],
                      ["moveplayer@movenetworks.com", "1.0.0.071101000055"],
                      ["{3EC9C995-8072-4fc0-953E-4F30620D17F3}", "2.0.0.4"],
                      ["{635abd67-4fe9-1b23-4f01-e679fa7484c1}", "1.6.5.200812101546"],
                      ["{972ce4c6-7e08-4474-a285-3208198ce6fd}", "3.0.6"],
                      ], "got %s" % result
    assert errorMessages == ['WARNING: "[\'{CAFEEFAC-0016-0000-0011-ABCDEFFEDCBA}6.0.11\']" is deficient as a name and version for an addon']

  def testMake_signature(self):
    """
    testMake_signature(self):
      check that function name removes spaces leading [*,&] and puts one space trailing [,]
      check that source is searched correctly for filename
        - if source and source_line: return 'source#source_line'
        - elif module_name: return 'module_name@instruction'
        - else: return '@instruction'
    """
    p = processor.Processor(me.config)
    for func,expected in { ' *foo':  '*foo',
                           '  &foo' : ' &foo',
                           '   ,foo':  '  , foo',
                           ' *&foo':  '*&foo',
                           ' & *foo':  '&*foo',
                           ' & * ,foo':'&*, foo',
                           ' foo &':  ' foo&',
                           'foo *':    'foo*',
                           'foo * ,&': 'foo*, &',
                           'foo ,& bar': 'foo, & bar',
                           '*foo&bar' : '*foo&bar',
                           'js_Interpret' : 'js_Interpret:123',
                           }.items():
      result = p.make_signature(None,func,None,'123',None)
      assert expected == result, 'Expected [%s], got [%s]'%(expected,result)
    for source,expected in {'C:': 'C:#LINE',
                            'C:\\': 'C:#LINE',
                            'C:\\a\\':'a#LINE',
                            'C:\\a':'a#LINE',
                            'C:\\a\\':'a#LINE',
                            'C:\\a\\b\\':'b#LINE',
                            '': '#LINE',
                            '\\': '#LINE',
                            '\\a\\':'a#LINE',
                            '\\a':'a#LINE',
                            '\\a\\':'a#LINE',
                            '\\a\\b\\':'b#LINE',
                            '/':'#LINE',
                            'a': 'a#LINE',
                            'a/':'a#LINE',
                            'a/b':'b#LINE',
                            '/a':'a#LINE',
                            '/a/':'a#LINE',
                            '/a/b/':'b#LINE',
                            '/a/b/c':'c#LINE',
                            }.items():
      result = p.make_signature(None,None,source,'LINE',None)
      assert expected == result, 'From [%s] expected [%s] but got [%s]'%(source,expected,result)

    modules = {('mod','LDa'): 'mod@LDa',
               (None,'LDa'):'@LDa',
               (0,12):'@12',
               ('mod',12): 'mod@12',
               ('mod',None): 'mod@None',
               }

    for (mname,instr),expected in modules.items():
      result = p.make_signature(mname,None,None,None,instr)
      assert expected == result, 'From [%s,%s] expected %s, got %s'%(mname,instr,expected,result)

  def testGenerateSignatureFromList(self):
    """
    testGenerateSignatureFromList(self):
      check that all and only 'legal' signatures are '|'.join(...)ed
      check that for irrelevantSignature patterns, they only participate if not the first.
      check that we stop after seeing an item with no valid signature
    """
    global me
    p = processor.Processor(me.config)
    p.prefixSignatureRegEx = re.compile('PFX_|sentinel_1') # bogus but easy
    fs='f'*150
    isLong = True
    aintLong = False
    testCases = [
      ([],                        '',aintLong),
      (['@0xaa','@0xbb'],         '',aintLong),
      (['@0xaa','PFX_1','@0xbb'],'PFX_1 | @0xbb',aintLong),
      (['PFX_0','@0xaa','@0xbb'],'PFX_0 | @0xaa | @0xbb',aintLong),
      (['PFX_1','PFX_2'],        'PFX_1 | PFX_2',aintLong),
      (['PFX_1','end','PFX_2'],  'PFX_1 | end',aintLong),
      (['PFX_1%s'%fs,'PFX_2%s'%fs,'end'],'PFX_1%s | PFX_2%s | end'%(fs,fs),isLong),
      (['a', 'b', 'c', 'sentinel_1', 'e', 'f'], 'sentinel_1 | e', aintLong),
      (['a', 'b', 'c', 'sentinel_2', 'e', 'f'], 'sentinel_2', aintLong),
      ]

    for aList,expected,isLong in testCases:
      result = p.generateSignatureFromList(aList)
      assert expected == result , 'From %s expected "%s" got "%s"'%(aList,expected,result)
      assert isLong == (len(result) > 255)
