"""
You must run this test module using nose (chant nosetests from the command line)
** There are some issues with nose, offset by the fact that it does multi-thread and setup_module better than unittest
 * This is NOT a unittest.TestCase ... it could be except that unittest screws up setup_module
 * nosetests may hang in some ERROR conditions. SIGHUP, SIGINT and SIGSTP are not noticed. SIGKILL (-9) works
 * You should NOT pass command line arguments to nosetests. You can pass them, but it causes trouble:
 *   Nosetests passes them into the test environment which breaks socorro's configuration behavior
 *   You can set NOSE_WHATEVER envariables prior to running if you need to. See nosetests --help
 *    some useful envariables:
 *      NOSE_VERBOSE=x where x in [0,      # Prints only 'OK' at end of test run
 *                                 1,      # default: Prints one '.' per test like unittest
 *                                 x >= 2, # Prints first comment line if exists, else the function name per test
 *                                ]
 *      NOSE_WHERE=directory_path[,directoroy_path[,...]] : run only tests in these directories. Note commas
 *      NOSE_ATTR=attrspec[,attrspec ...] : run only tests for which at least one attrspec evaluates true. 
 *         Accepts '!attr' and 'attr=False'. Does NOT accept natural python syntax ('atter != True', 'not attr')
 *      NOSE_NOCAPTURE=TrueValue : nosetests normally captures stdout and only displays it if the test has fail or error.
 *         print debugging works with this envariable, or you can instead print to stderr or use a logger
 *
 * With NOSE_VERBOSE > 1, you may see "functionName(self): (slow=N)" for some tests. N is the max seconds waiting
"""
import copy
import datetime as dt
import errno
import logging
import logging.handlers
import os
import shutil
import signal
import threading
import time
import traceback

import psycopg2

from nose.tools import *

import socorro.lib.ConfigurationManager as configurationManager
import socorro.monitor.monitor as monitor

import socorro.unittest.testlib.createJsonDumpStore as createJDS
import socorro.unittest.testlib.dbtestutil as dbtestutil
from   socorro.unittest.testlib.testDB import TestDB
from   socorro.unittest.testlib.util import runInOtherProcess

import monitorTestconfig as testConfig
import socorro.database.schema as schema

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
  # else initialize
  # print "MODULE setup"
  me = Me()
  me.markingTemplate = "MARK %s: %s"
  me.startMark = 'start'
  me.endMark = 'end'
  me.testDB = TestDB()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Monitor')
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass
  knownTests = [x for x in dir(TestMonitor) if x.startswith('test')]
  me.logWasExtracted = {}
  for t in knownTests:
    me.logWasExtracted[t] = False
  me.logger = monitor.logger
  me.logger.setLevel(logging.DEBUG)
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
  me.logger.addHandler(fileLog)
  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                   me.config.databaseUserName,me.config.databasePassword)

def teardown_module():
  global me
  logging.shutdown()
  try:
    os.unlink(me.logFilePathname)
  except OSError,x:
    if errno.ENOENT != x.errno:
      raise

class TestMonitor:
  markingLog = False

  def setUp(self):
    global me
    self.connection = psycopg2.connect(me.dsn)

    # just in case there was a crash on prior run
    me.testDB.removeDB(me.config,me.logger)
    me.testDB.createDB(me.config,me.logger)

  def tearDown(self):
    global me
    me.testDB.removeDB(me.config,me.logger)
    try:
      shutil.rmtree(me.config.storageRoot)
    except OSError,x:
      pass
    try:
      shutil.rmtree(me.config.deferredStorageRoot)
    except OSError,x:
      pass
    try:
      if me.config.saveSuccessfulMinidumpsTo:
        shutil.rmtree(me.config.saveSuccessfulMinidumpsTo)
    except OSError,x:
      pass
    try:
      if me.config.saveFailedMinidumpsTo:
        shutil.rmtree(me.config.saveFailedMinidumpsTo)
    except OSError,x:
      pass

  def markLog(self):
    global me
    testName = traceback.extract_stack()[-2][2]
    if TestMonitor.markingLog:
      TestMonitor.markingLog = False
      me.logger.info(me.markingTemplate%(testName,me.endMark))
      # print (' ==== <<%s>> '+me.markingTemplate)%(os.getpid(),testName,me.endMark) #DEBUG
    else:
      TestMonitor.markingLog = True
      me.logger.info(me.markingTemplate%(testName,me.startMark))
      # print (' ==== <<%s>> '+me.markingTemplate)%(os.getpid(),testName,me.startMark) #DEBUG

  def extractLogSegment(self):
    global me
    testName = traceback.extract_stack()[-2][2]
    # print ' ==== <<%s>> EXTRACTING: %s (%s)'%(os.getpid(),testName,me.logWasExtracted[testName]) #DEBUG
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
      Constructor must succeed if all config is present
      Constructor should never log anything
    """
    # print 'TEST: testConstructor'
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
      "standardLoopDelay",
      "cleanupJobsLoopDelay",
      "priorityLoopDelay",
      "saveSuccessfulMinidumpsTo",
      "saveFailedMinidumpsTo",
      ]
    cc = copy.copy(me.config)
    self.markLog()
    for rc in requiredConfigs:
      del(cc[rc])
      try:
        m = monitor.Monitor(cc)
        assert False, "expected to raise some kind of exception for missing %s" % (rc)
      except Exception,x:
        pass
      cc[rc] = me.config[rc]
    monitor.Monitor(me.config) # expect this to work. If it raises an error, we'll see it
    self.markLog()
    assert [] == self.extractLogSegment(), 'expected no logging for constructor call (success or failure) but %s'%(str(self.extractLogSegment()))

  def runStartChild(self):
    global me
    try:
      m = monitor.Monitor(me.config)
      m.start()
      me.logger.fail("This line forces a wrong count in later assertions: We expected a SIGTERM before getting here.")
    except BaseException,x:
      me.logger.info("CHILD Exception in %s: %s [%s]"%(threading.currentThread().getName(),type(x),x))
      os._exit(0)

  def testStart(self):
    """
    testStart(self): (slow=2)
    This test may run for a second or two
    start does:
      a lot of logging ... and there really isn't much else to test, so we are testing that. Ugh.
      For this one, we won't pay attention to what stops the threads
    """
    global me
    self.markLog()
    runInOtherProcess(self.runStartChild)
    self.markLog()
    seg = self.extractLogSegment()

    dateWalk = 0
    connectionClosed = 0

    priorityConnect = 0
    priorityQuit = 0
    priorityDone = 0

    cleanupStart = 0
    cleanupQuit = 0
    cleanupDone = 0

    for i in seg:
      date,tyme,level,dash,msg = i.split(None,4)
      if msg.startswith('MainThread'):
        if 'connection' in msg and 'closed' in msg: connectionClosed += 1
        if 'destructiveDateWalk' in msg: dateWalk += 1
      elif msg.startswith('priorityLoopingThread'):
        if 'connecting to database' in msg: priorityConnect += 1
        if 'detects quit' in msg: priorityQuit += 1
        if 'priorityLoop done' in msg: priorityDone += 1
      elif msg.startswith('jobCleanupThread'):
        if 'jobCleanupLoop starting' in msg: cleanupStart += 1
        if 'got quit' in msg: cleanupQuit += 1
        if 'jobCleanupLoop done' in msg: cleanupDone += 1
    assert 2 == dateWalk, 'expect logging for start and end of destructiveDateWalk, got %d'%(dateWalk)
    assert 2 == connectionClosed, 'expect two connection close messages, got %d' %(connectionClosed)
    assert 1 == priorityConnect, 'priorityLoop had better connect to database exactly once, got %d' %(priorityConnect)
    assert 1 == priorityQuit, 'priorityLoop should detect quit exactly once, got %d' %(priorityQuit)
    assert 1 == priorityDone, 'priorityLoop should report self done exactly once, got %d' %(priorityDone)
    assert 1 == cleanupStart, 'jobCleanup should report start exactly once, got %d' %(cleanupStart)
    assert 1 == cleanupQuit, 'jobCleanup should report quit exactly once, got %d' %(cleanupQuit)
    assert 1 == cleanupDone, 'jobCleanup should report done exactly once, got %d' %(cleanupDone)

  def testRespondToSIGHUP(self):
    """
    testRespondToSIGHUP(self): (slow=1)
    This test may run for a second or two
      We should notice a SIGHUP and die nicely. This is exactly like testStart except that we look
      for different logging events (ugh)
    """
    global me
    self.markLog()
    runInOtherProcess(self.runStartChild,logger=me.logger,signal=signal.SIGHUP)
    self.markLog()
    seg = self.extractLogSegment()
    kbd = 0
    sighup = 0
    sigterm = 0
    for line in seg:
      date,tyme,level,dash,msg = line.split(None,4)
      if msg.startswith('MainThread'):
        if 'KeyboardInterrupt' in msg: kbd += 1
        if 'SIGHUP detected' in msg: sighup += 1
        if 'SIGTERM detected' in msg: sigterm += 1
    assert 1 == kbd, 'Better see exactly one keyboard interrupt, got %d' % (kbd)
    assert 1 == sighup, 'Better see exactly one sighup event, got %d' % (sighup)
    assert 0 == sigterm, 'Better not see sigterm event, got %d' % (sigterm)
     
  def testRespondToSIGTERM(self):
    """
    testRespondToSIGTERM(self): (slow=1)
    This test may run for a second or two
      We should notice a SIGTERM and die nicely. This is exactly like testStart except that we look
      for different logging events (ugh)
    """
    global me
    self.markLog()
    runInOtherProcess(self.runStartChild,signal=signal.SIGTERM)
    self.markLog()
    seg = self.extractLogSegment()
    kbd = 0
    sighup = 0
    sigterm = 0
    for line in seg:
      date,tyme,level,dash,msg = line.split(None,4)
      if msg.startswith('MainThread'):
        if 'KeyboardInterrupt' in msg: kbd += 1
        if 'SIGTERM detected' in msg: sigterm += 1
        if 'SIGHUP detected' in msg: sighup += 1
    assert 1 == kbd, 'Better see exactly one keyboard interrupt, got %d' % (kbd)
    assert 1 == sigterm, 'Better see exactly one sigterm event, got %d' % (sigterm)
    assert 0 == sighup, 'Better not see sighup event, got %d' % (sighup)
     
  def testQuitCheck(self):
    """
    testQuitCheck(self):
    This test makes sure that the main loop notices when it has been told to quit.
    """
    global me
    mon = monitor.Monitor(me.config)
    mon.quit = True
    assert_raises(KeyboardInterrupt,mon.quitCheck)

  def quitter(self):
    time.sleep(self.timeTilQuit)
    self.mon.quit = True
  
  def testResponsiveSleep(self):
    """
    testResponsiveSleep(self): (slow=4)
    This test may run for some few seconds. Shouldn't be more than 6 tops (and if so, it will have failed).
    Tests that the responsiveSleep method actually responds by raising KeyboardInterrupt.
    """
    global me
    mon = monitor.Monitor(me.config)
    self.timeTilQuit = 2
    self.mon = mon
    quitter = threading.Thread(name='Quitter', target=self.quitter)
    quitter.start()
    assert_raises(KeyboardInterrupt,mon.responsiveSleep,5)
    quitter.join()

  def testGetDatabaseConnectionPair(self):
    """
    testGetDatabaseConnectionPair(self):
    test that the wrapper for psycopghelper.DatabaseConnectionPool works as expected
    """
    # print 'TEST: testGetDatabaseConnectionPair'
    global me
    mon = monitor.Monitor(me.config)
    tcon,tcur = mon.getDatabaseConnectionPair()
    mcon,mcur = mon.databaseConnectionPool.connectionCursorPair()
    assert tcon == mcon
    assert tcur == mcur

  def testGetStorageFor(self):
    """
    testGetStorageFor(self):
    Test that the wrapper for JsonDumpStorage doesn't twist things incorrectly
    """
    global me
    self.markLog()
    createJDS.createTestSet(createJDS.jsonFileData,jsonKwargs={'logger':me.logger},rootDir=me.config.storageRoot)
    createJDS.createTestSet(createJDS.jsonMoreData,jsonKwargs={'logger':me.logger},rootDir=me.config.deferredStorageRoot)
    mon = monitor.Monitor(me.config)
    assert_raises(monitor.UuidNotFoundException,mon.getStorageFor,'nothing')
    expected = me.config.storageRoot.rstrip(os.sep)
    got = mon.getStorageFor('0bba929f-8721-460c-dead-a43c20071025').root
    assert expected == got, 'Expected [%s] got [%s]'%(expected,got)

    expected = me.config.deferredStorageRoot.rstrip(os.sep)
    got = mon.getStorageFor('29adfb61-f75b-11dc-b6be-001320081225').root
    assert expected == got, 'Expected [%s] got [%s]'%(expected,got)
    self.markLog()
    assert [] == self.extractLogSegment(), 'expected no logging for this test'

  def testRemoveBadUuidFromJsonDumpStorage(self):
    """
    testRemoveBadUuidFromJsonDumpStorage(self):
    This just wraps JsonDumpStorage. Assure we aren't futzing up the wrap (fail with non-exist uuid)
    """
    global me
    createJDS.createTestSet(createJDS.jsonFileData,jsonKwargs={'logger':me.logger},rootDir=me.config.storageRoot)
    mon = monitor.Monitor(me.config)
    badUuid = '0bad0bad-0bad-6666-9999-0bad20001025'
    assert_raises(monitor.UuidNotFoundException,mon.removeUuidFromJsonDumpStorage,badUuid)
    
  def testRemoveGoodUuidFromJsonDumpStorage(self):
    """
    testRemoveGoodUuidFromJsonDumpStorage(self):
    This really just wraps JsonDumpStorage call. Assure we aren't futzing up the wrap (succeed with existing uuids)
    """
    global me
    createJDS.createTestSet(createJDS.jsonFileData,jsonKwargs={'logger':me.logger},rootDir=me.config.storageRoot)
    createJDS.createTestSet(createJDS.jsonMoreData,jsonKwargs={'logger':me.logger},rootDir=me.config.deferredStorageRoot)
    mon = monitor.Monitor(me.config)
    goodUuid = '0b781b88-ecbe-4cc4-dead-6bbb20081225';
    # this should work the first time...
    mon.removeUuidFromJsonDumpStorage(goodUuid)
    # ... and then fail the second time
    assert_raises(monitor.UuidNotFoundException,mon.removeUuidFromJsonDumpStorage, goodUuid)
    
  def testCompareSecondOfSequence(self):
    """
    testCompareSecondOfSequence(self):
    Not much to test, but do it
    """
    x = (1,10)
    y = (10,1)
    assert cmp(x,y) < 0 # check assumptions about cmp...
    assert monitor.Monitor.compareSecondOfSequence(x,y) > 0
    assert cmp(y,x) > 0
    assert monitor.Monitor.compareSecondOfSequence(y,x) < 0
    
  def testJobSchedulerIterNoProcs(self):
    """
    testJobSchedulerIterNoProcs(self):
    Assure that attempts at balanced scheduling with no processor raises monitor.NoProcessorsRegisteredException
    """
    global me
    m = monitor.Monitor(me.config)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    iter = m.jobSchedulerIter(dbCur)
    assert_raises(SystemExit,iter.next)
 
#   def testJobScheduleIter_AllOldProcessors(self):
#     """
#     testJobScheduleIter_AllOldProcessors(self):
#     If we have only old processors, we should fail (but as of 2009-january, don't: Test is commented out)
#     """
#     global me
#     m = monitor.Monitor(me.config)
#     dbCon,dbCur = m.getDatabaseConnectionPair()
#     stamp = dt.datetime.now() - dt.timedelta(minutes=10)
#     dbtestutil.fillProcessorTable(dbCur, 5, stamp=stamp)
#     iter = m.jobSchedulerIter(dbCur)
#     assert_raises(WhatKind? iter.next)

  def testJobSchedulerIterGood(self):
    """
    testJobSchedulerIterGood(self):
    Plain vanilla test of the balanced job scheduler.
    """
    global me
    numProcessors = 15
    dbtestutil.fillProcessorTable(self.connection.cursor(),numProcessors)
    m = monitor.Monitor(me.config)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    iter = m.jobSchedulerIter(dbCur)
    num = 0
    hits = dict(((1+x,0) for x in range (numProcessors)))
    for id in iter:
      num += 1
      hits[int(id)] += 1
      if num >= numProcessors: break
    for i in range(numProcessors):
      assert hits[i+1] == 1, 'At index %d, got count %d'%(i+1, hits[i+1])
    for id in iter:
      num += 1
      hits[int(id)] += 1
      if num >= 3*numProcessors: break
    for i in range(numProcessors):
      assert hits[i+1] == 3, 'At index %d, got count %d'%(i+1, hits[i+1])

  def getCurrentProcessorList(self):
    """Useful for figuring out what is there before we call some method or other."""
    global me
    sql = "select p.id, count(j.*) from processors p left join (select owner from jobs where success is null) as j on p.id = j.owner group by p.id;"
    m = monitor.Monitor(me.config)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    dbCur.execute(sql);
    return [(aRow[0], aRow[1]) for aRow in dbCur.fetchall()]  #processorId, numberOfAssignedJobs

  def testJobScheduleIter_StartUnbalanced(self):
    """
    testJobScheduleIter_StartUnbalanced(self):
    Assure that an unbalanced start eventually produces balanced result
    """
    numProcessors = 5
    dbtestutil.fillProcessorTable(self.connection.cursor(),numProcessors)
    m = monitor.Monitor(me.config)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    dbtestutil.addSomeJobs(dbCur,dict([(1+x,1+x) for x in range(numProcessors)]),logger=me.logger)
    iter = m.jobSchedulerIter(dbCur)
    num = 0
    hits = dict(((1+x,0) for x in range (numProcessors)))
    for id in iter:
      num += 1
      hits[int(id)] += 1
      me.logger.debug('HIT on %d: %d'%(id,hits[id]))
      if num >= 3*numProcessors: break
    for i in range(numProcessors):
      assert hits[i+1] == 5 - i, 'Expected num hits to be count down sequence from 5 to 1, but at idx %d, got %d'%(i+1,hits[i+1])
      me.logger.debug('ONE: At index %d, got count %d'%(i+1, hits[i+1]))

#   def testJobScheduleIter_SomeOldProcessors(self):
#     """
#     testJobScheduleIter_SomeOldProcessors(self):
#     If we have some old processors, be sure we don't see them in the iter
#     As of 2009-January, that is not the case, so we have commented this test.
#     """
#     global me
#     m = monitor.Monitor(me.config)
#     dbCon,dbCur = m.getDatabaseConnectionPair()
#     now = dt.datetime.now()
#     then = now - dt.timedelta(minutes=10)
#     dbtestutil.fillProcessorTable(dbCur, None, processorMap = {1:then,2:then,3:now,4:then,5:then })
#     iter = m.jobScheduleIter(dbCur)
#     hits = dict(((x,0) for x in range (1,6)))
#     num = 0;
#     for id in iter:
#       num += 1
#       hits[int(id)] += 1
#       if num > 3: break
#     for i in (1,2,4,5):
#       assert hits[i] == 0, 'Expected that no old processors would be used in the iterator'
#     assert hits[3] == 4, 'Expected that all the iterations would choose the one live processor'

  def testUnbalancedJobSchedulerIterNoProcs(self):
    """
    testUnbalancedJobSchedulerIterNoProcs(self):
    With no processors, we will get a system exit
    """
    global me
    m = monitor.Monitor(me.config)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    iter = m.unbalancedJobSchedulerIter(dbCur)
    assert_raises(SystemExit, iter.next)

  def testUnbalancedJobSchedulerIter_AllOldProcs(self):
    """
    testUnbalancedJobSchedulerIter_AllOldProcs(self):
    With only processors that are too old, we will get a system exit
    """
    global me
    m = monitor.Monitor(me.config)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    stamp = dt.datetime.now() - dt.timedelta(minutes=10)
    dbtestutil.fillProcessorTable(dbCur, 5, stamp=stamp)
    iter = m.unbalancedJobSchedulerIter(dbCur)
    assert_raises(SystemExit, iter.next)

  def testUnbalancedJobSchedulerIter_SomeOldProcs(self):
    """
    testUnbalancedJobSchedulerIter_SomeOldProcs(self):
    With some processors that are too old, we will get only the young ones in some order
    """
    global me
    m = monitor.Monitor(me.config)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    now = dt.datetime.now()
    then = now - dt.timedelta(minutes=10)
    dbtestutil.fillProcessorTable(dbCur, None, processorMap = {1:then,2:then,3:now,4:then,5:then })
    iter = m.unbalancedJobSchedulerIter(dbCur)
    hits = dict(((x,0) for x in range (1,6)))
    num = 0;
    for id in iter:
      num += 1
      hits[int(id)] += 1
      if num > 3: break
    for i in (1,2,4,5):
      assert hits[i] == 0, 'Expected that no old processors would be used in the iterator'
    assert hits[3] == 4, 'Expected that all the iterations would choose the one live processor'

  def testUnbalancedJobSchedulerIter(self):
    """
    testUnbalancedJobSchedulerIter(self):
    With an unbalanced load on the processors, each processor still gets the same number of hits
    """
    global me
    numProcessors = 5
    loopCount = 3
    dbtestutil.fillProcessorTable(self.connection.cursor(),numProcessors)
    m = monitor.Monitor(me.config)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    dbtestutil.addSomeJobs(dbCur,{1:12},logger=me.logger)
    iter = m.unbalancedJobSchedulerIter(dbCur)
    num = 0
    hits = dict(((1+x,0) for x in range (numProcessors)))
    for id in iter:
      num += 1
      hits[int(id)] += 1
      if num >= loopCount*numProcessors: break
    for i in range(numProcessors):
      assert hits[i+1] == loopCount, 'expected %d for processor %d, but got %d'%(loopCount,i+1,hits[i+1])

  def setJobSuccess(self, cursor, idTimesAndSuccessSeq):
    global me
    sql = "UPDATE jobs SET starteddatetime = %s, completeddatetime = %s, success = %s WHERE id = %s"
    for row in idTimesAndSuccessSeq:
      if row[2]: row[2] = True
      if not row[2]: row[2] = False
    cursor.executemany(sql,idTimesAndSuccessSeq)
    cursor.connection.commit()
    sql = 'SELECT id, uuid, success FROM jobs ORDER BY id'
    cursor.execute(sql)
    return cursor.fetchall()

  def jobsAllocated(self):
    global me
    m = monitor.Monitor(me.config)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    sql = "SELECT count(*) from jobs"
    dbCur.execute(sql)
    return dbCur.fetchone()[0]

  def testCleanUpCompletedAndFailedJobs_WithSaves(self):
    """
    testCleanUpCompletedAndFailedJobs_WithSaves(self):
    The default config asks for successful and failed jobs to be saved
    """
    global me
    dbtestutil.fillProcessorTable(self.connection.cursor(),4)
    m = monitor.Monitor(me.config)
    createJDS.createTestSet(createJDS.jsonFileData,jsonKwargs={'logger':me.logger},rootDir=me.config.storageRoot)
    runInOtherProcess(m.standardJobAllocationLoop, stopCondition=(lambda : self.jobsAllocated() == 14))
    started = dt.datetime.now()
    completed = started + dt.timedelta(microseconds=100)
    idTimesAndSuccessSeq = [
      [started,completed,True,1],
      [started,completed,True,3],
      [started,completed,True,5],
      [started,completed,True,11],
      [started,None,False,2],
      [started,None,False,4],
      [started,None,False,8],
      [started,None,False,12],
      ]
    dbCon,dbCur = m.getDatabaseConnectionPair()
    jobdata = self.setJobSuccess(dbCur,idTimesAndSuccessSeq)
    m.cleanUpCompletedAndFailedJobs()
    successSave = set()
    failSave = set()
    expectSuccessSave = set()
    expectFailSave = set()
    remainBehind = set()
    for dir, dirs, files in os.walk(me.config.storageRoot):
      remainBehind.update(os.path.splitext(x)[0] for x in files)
    for d in idTimesAndSuccessSeq:
      if d[2]:
        expectSuccessSave.add(d[3])
      else:
        expectFailSave.add(d[3])
    for dir,dirs,files in os.walk(me.config.saveSuccessfulMinidumpsTo):
      successSave.update((os.path.splitext(x)[0] for x in files))
    for dir,dirs,files in os.walk(me.config.saveFailedMinidumpsTo):
      failSave.update((os.path.splitext(x)[0] for x in files))
    for x in jobdata:
      if None == x[2]:
        assert not x[1] in failSave and not x[1] in successSave, "if we didn't set success state for %s, then it wasn't copied"%(x[1])
        assert x[1] in remainBehind, "if we didn't set success state for %s, then it should remain behind"%(x[1])
        assert not x[0] in expectFailSave and not x[0] in expectSuccessSave, "database should match expectatations for id=%s"%(x[0])
      elif True == x[2]:
        assert  not x[1] in failSave and x[1] in successSave, "if we set success for %s, it is copied to %s"%(x[1],me.config.saveSussessfulMinidumpsTo)
        assert not x[0] in expectFailSave and x[0] in expectSuccessSave, "database should match expectatations for id=%s"%(x[0])
        assert not x[1] in remainBehind, "if we did set success state for %s, then it should not remain behind"%(x[1])
      elif False == x[2]:
        assert  x[1] in failSave and not x[1] in successSave, "if we set failure for %s, it is copied to %s"%(x[1],me.config.saveFailedMinidumpsTo)
        assert  x[0] in expectFailSave and not x[0] in expectSuccessSave, "database should match expectatations for id=%s"%(x[0])
        assert not x[1] in remainBehind, "if we did set success state for %s, then it should not remain behind"%(x[1])
    
  def testCleanUpCompletedAndFailedJobs_WithoutSaves(self):
    """
    testCleanUpCompletedAndFailedJobs_WithoutSaves(self):
    First, dynamically set config to not save successful or failed jobs. They are still removed from the file system
    """
    global me
    cc = copy.copy(me.config)
    dbtestutil.fillProcessorTable(self.connection.cursor(),4)
    for conf in ['saveSuccessfulMinidumpsTo','saveFailedMinidumpsTo']:
      cc[conf] = ''
    m = monitor.Monitor(cc)
    createJDS.createTestSet(createJDS.jsonFileData,jsonKwargs={'logger':me.logger},rootDir=me.config.storageRoot)
    runInOtherProcess(m.standardJobAllocationLoop, stopCondition=(lambda : self.jobsAllocated() == 14))
    started = dt.datetime.now()
    completed = started + dt.timedelta(microseconds=100)
    idTimesAndSuccessSeq = [
      [started,completed,True,1],
      [started,completed,True,3],
      [started,completed,True,5],
      [started,completed,True,11],
      [started,None,False,2],
      [started,None,False,4],
      [started,None,False,8],
      [started,None,False,12],
      ]
    dbCon,dbCur = m.getDatabaseConnectionPair()
    jobdata = self.setJobSuccess(dbCur,idTimesAndSuccessSeq)
    m.cleanUpCompletedAndFailedJobs()
    successSave = set()
    failSave = set()
    expectSuccessSave = set()
    expectFailSave = set()
    for d in idTimesAndSuccessSeq:
      if d[2]:
        expectSuccessSave.add(d[3])
      else:
        expectFailSave.add(d[3])
    for dir,dirs,files in os.walk(me.config.saveSuccessfulMinidumpsTo):
      successSave.update((os.path.splitext(x)[0] for x in files))
    for dir,dirs,files in os.walk(me.config.saveFailedMinidumpsTo):
      failSave.update((os.path.splitext(x)[0] for x in files))
    remainBehind = set()
    for dir, dirs, files in os.walk(me.config.storageRoot):
      remainBehind.update(os.path.splitext(x)[0] for x in files)
    assert len(successSave) == 0, "We expect not to save any successful jobs with this setting"
    assert len(failSave) == 0, "We expect not to save any failed jobs with this setting"
    for x in jobdata:
      if None ==  x[2]:
        assert  not x[0] in expectFailSave and not x[0] in expectSuccessSave, "database should match expectatations for id=%s"%(x[0])
        assert x[1] in remainBehind, "if we didn't set success state for %s, then it should remain behind"%(x[1])
      elif True ==  x[2]:
        assert not x[1] in remainBehind, "if we did set success state for %s, then it should not remain behind"%(x[1])
        assert not x[0] in expectFailSave and x[0] in expectSuccessSave, "database should match expectatations for id=%s"%(x[0])
      elif False == x[2]:
        assert not x[1] in remainBehind, "if we did set success state for %s, then it should not remain behind"%(x[1])
        assert x[0] in expectFailSave and not x[0] in expectSuccessSave, "database should match expectatations for id=%s"%(x[0])
    
  def testCleanUpDeadProcessors_AllDead(self):
    """
    testCleanUpDeadProcessors(self):
    As of 2009-01-xx, Monitor.cleanUpDeadProcessors(...) does nothing except write to a log file
    ... and fail if there are no live processors
    """
    global me
    m = monitor.Monitor(me.config)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    now = dt.datetime.now()
    then = now - dt.timedelta(minutes=10)
    dbtestutil.fillProcessorTable(dbCur, None, processorMap = {1:then,2:then,3:then,4:then,5:then })
    assert_raises(SystemExit,m.cleanUpDeadProcessors, dbCur)

  def testQueueJob(self):
    """
    testQueueJob(self):
      make sure jobs table starts empty
      make sure returned values reflect database values
      make sure assigned processors are correctly reflected
      make sure duplicate uuid is caught, reported, and work continues
    """
    global me
    m = monitor.Monitor(me.config)
    sql = 'SELECT pathname,uuid,owner from jobs;'
    numProcessors = 4
    dbtestutil.fillProcessorTable(self.connection.cursor(),numProcessors)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    procIdGenerator = m.jobSchedulerIter(dbCur)
    dbCur.execute(sql)
    beforeJobsData = dbCur.fetchall()
    assert 0 == len(beforeJobsData), 'There should be no queued jobs before we start our run'
    expectedHits = dict(((1+x,0) for x in range (numProcessors)))
    mapper = {}
    hits = dict(((1+x,0) for x in range (numProcessors)))
    for uuid,data in createJDS.jsonFileData.items():
      procId = m.queueJob(dbCur,uuid,procIdGenerator)
      expectedHits[procId] += 1;
      mapper[uuid] = procId
    dbCur.execute(sql)
    afterJobsData = dbCur.fetchall()
    for row in afterJobsData:
      hits[row[2]] += 1
      #me.logger.debug("ASSERT %s == %s for index %s"%(mapper.get(row[1],'WHAT?'), row[2], row[1]))
      assert mapper[row[1]] == row[2], 'Expected %s from %s but got %s'%(mapper.get(row[1],"WOW"),row[1],row[2])
    for key in expectedHits.keys():
      #me.logger.debug("ASSERTING %s == %s for index %s"%(expectedHits.get(key,'BAD KEY'),hits.get(key,'EVIL KEY'),key))
      assert expectedHits[key] == hits[key], "Expected count of %s for %s, but got %s"%(expectedHits[key],key,hits[key])
    self.markLog()
    dupUuid = createJDS.jsonFileData.keys()[0]
    try:
      procId = m.queueJob(dbCur,dupUuid,procIdGenerator)
      assert False, "Expected that IntegrityError would be raised queue-ing %s  but it wasn't"%(dupUuid)
    except psycopg2.IntegrityError:
      pass
    except Exception,x:
      assert False, "Expected that only IntegrityError would be raised, but got %s: %s"%(type(x),x)
    self.markLog()
      
  def testQueuePriorityJob(self):
    """
    testQueuePriorityJob(self):
    queuePriorityJob does:
      removes job uuid from priorityjobs table (if possible)
      add uuid to priority_jobs_NNN table for NNN the processor id
      add uuid, id, etc to jobs table with priority > 0
    """
    global me
    m = monitor.Monitor(me.config)
    numProcessors = 4
    dbtestutil.fillProcessorTable(self.connection.cursor(),numProcessors)
    data = dbtestutil.makeJobDetails({1:2,2:2,3:3,4:3})
    dbCon,dbCur = m.getDatabaseConnectionPair()
    procIdGenerator = m.jobSchedulerIter(dbCur)
    insertSql = "INSERT into priorityjobs (uuid) VALUES (%s);"
    uuidToId = {}
    for tup in data:
      uuidToId[tup[1]] = tup[2]
    uuids = uuidToId.keys()
    for uuid in uuids:
      if uuidToId[uuid]%2:
        dbCur.execute(insertSql,[uuid])
    dbCon.commit()
    countSql = "SELECT count(*) from %s;"
    dbCur.execute(countSql%('priorityjobs'))
    priorityJobCount = dbCur.fetchone()[0]
    dbCur.execute(countSql%('jobs'))
    jobCount = dbCur.fetchone()[0]
    eachPriorityJobCount = {}
    for uuid in uuids:
      procId = m.queuePriorityJob(dbCur,uuid, procIdGenerator)
      dbCur.execute('SELECT count(*) from jobs where jobs.priority > 0')
      assert dbCur.fetchone()[0] == 1 + jobCount, 'Expect that each queuePriority will increase jobs table by one'
      jobCount += 1
      try:
        eachPriorityJobCount[procId] += 1
      except KeyError:
        eachPriorityJobCount[procId] = 1
      if uuidToId[uuid]%2:
        dbCur.execute(countSql%('priorityjobs'))
        curCount = dbCur.fetchone()[0]
        assert curCount == priorityJobCount -1, 'Expected to remove one job from priorityjobs for %s'%uuid
        priorityJobCount -= 1
    for id in eachPriorityJobCount.keys():
      dbCur.execute(countSql%('priority_jobs_%s'%id))
      count = dbCur.fetchone()[0]
      assert eachPriorityJobCount[id] == count, 'Expected that the count %s added to id %s matches %s found'%(eachPriorityJobCount[id],id,count)

  def testGetPriorityUuids(self):
    """
    testGetPriorityUuids(self):
      Check that we find none if the priorityjobs table is empty
      Check that we find as many as we put into priorityjobs table
    """
    global me
    m = monitor.Monitor(me.config)
    count = len(m.getPriorityUuids(self.connection.cursor()))
    assert 0 == count, 'Expect no priorityjobs unless they were added. Got %d'%(count)
    data = dbtestutil.makeJobDetails({1:2,2:2,3:3,4:3})
    insertSql = "INSERT into priorityjobs (uuid) VALUES (%s);"
    self.connection.cursor().executemany(insertSql,[ [x[1]] for x in data ])
    self.connection.commit()
    count = len(m.getPriorityUuids(self.connection.cursor()))
    assert len(data) == count,'expect same count in data as priorityJobs, got %d'%(count)
    self.connection.close()
    
  def testLookForPriorityJobsAlreadyInQueue(self):
    """
    testLookForPriorityJobsAlreadyInQueue(self):
      Check that we erase jobs from priorityjobs table if they are there
      Check that we increase by one the priority in jobs table
      Check that we add job (only) to appropriate priority_jobs_NNN table
      Check that attempting same uuid again raises IntegrityError
    """
    global me
    numProcessors = 5
    dbtestutil.fillProcessorTable(self.connection.cursor(),numProcessors)
    m = monitor.Monitor(me.config)
    data = dbtestutil.makeJobDetails({1:2,2:2,3:3,4:3,5:2})
    dbCon,dbCur = m.getDatabaseConnectionPair()
    procIdGenerator = m.jobSchedulerIter(dbCur)
    insertSql = "INSERT into priorityjobs (uuid) VALUES (%s);"
    updateSql = "UPDATE jobs set priority = 1 where uuid = %s;"
    allUuids = [x[1] for x in data]
    priorityJobUuids = [];
    missingUuids = []
    uuidToProcId = {}
    for counter in range(len(allUuids)):
      uuid = allUuids[counter]
      if 0 == counter % 3: # add to jobs and priorityjobs table
        uuidToProcId[uuid] = m.queueJob(dbCur,data[counter][1],procIdGenerator)
        priorityJobUuids.append((uuid,))
      elif 1 == counter % 3: # add to jobs table only
        uuidToProcId[uuid] = m.queueJob(dbCur,data[counter][1],procIdGenerator)
      else: # 2== counter %3 # don't add anywhere
        missingUuids.append(uuid)
    dbCur.executemany(insertSql,priorityJobUuids)
    dbCon.commit()
    for uuid in priorityJobUuids:
      dbCur.execute(updateSql,(uuid,))
    self.markLog()
    m.lookForPriorityJobsAlreadyInQueue(dbCur,allUuids)
    self.markLog()
    seg = self.extractLogSegment()
    for line in seg:
      date,tyme,level,dash,thr,ddash,msg = line.split(None,6)
      assert thr == 'MainThread','Expected only MainThread log lines, got[%s]'%(line)
      uuid = msg.split()[2]
      assert not uuid in missingUuids, 'Found %s that should not be in missingUuids'%(uuid)
      assert uuid in uuidToProcId.keys(), 'Found %s that should be in uuidToProcId'%(uuid)
    countSql = "SELECT count(*) from %s;"
    dbCur.execute(countSql%('priorityjobs'))
    priCount = dbCur.fetchone()[0]
    assert 0 == priCount, 'Expect that all the priority jobs are removed, but found %s'%(priCount)
    countSql = "SELECT count(*) from priority_jobs_%s WHERE uuid = %%s;"
    for uuid,procid in uuidToProcId.items():
      dbCur.execute(countSql%(procid),(uuid,))
      priCount = dbCur.fetchone()[0]
      assert priCount == 1, 'Expect to find %s in priority_jobs_%s exactly once'%(uuid,procid)
      for badid in range(1,numProcessors+1):
        if badid == procid: continue
        dbCur.execute(countSql%(badid),(uuid,))
        badCount = dbCur.fetchone()[0]
        assert 0 == badCount, 'Expect to find %s ONLY in other priority_jobs_NNN, found it in priority_jobs_%s'%(uuid,badid)
    for uuid,procid in uuidToProcId.items():
      try:
        m.lookForPriorityJobsAlreadyInQueue(dbCur,(uuid,))
        assert False, 'Expected line above would raise IntegrityError or InternalError'
      except psycopg2.IntegrityError,x:
        dbCon.rollback()
      except:
        assert False, 'Expected only IntegrityError from the try block'

  def testUuidInJsonDumpStorage(self):
    """
    testUuidInJsonDumpStorage(self):
    Test that the wrapper for JsonDumpStorage isn't all twisted up:
      assure we find something in normal and deferred storage, and miss something that isn't there
      do NOT test that the 'markAsSeen' actually works: That should be testJsonDumpStorage's job
    """
    global me
    m = monitor.Monitor(me.config)
    createJDS.createTestSet(createJDS.jsonFileData,jsonKwargs={'logger':me.logger},rootDir=me.config.storageRoot)
    createJDS.createTestSet(createJDS.jsonMoreData,jsonKwargs={'logger':me.logger},rootDir=me.config.deferredStorageRoot)
    self.markLog()
    badUuid = '0bad0bad-0bad-6666-9999-0bad20001025'
    goodUuid = '0bba929f-8721-460c-dead-a43c20071025'
    defUuid = '29adfb61-f75b-11dc-b6be-001320081225'
    assert m.uuidInJsonDumpStorage(goodUuid), 'Dunno how that happened'
    assert m.uuidInJsonDumpStorage(defUuid), 'Dunno how that happened'
    assert not m.uuidInJsonDumpStorage(badUuid), 'Dunno how that happened'
    self.markLog()
    seg = self.extractLogSegment()
    assert [] == seg, "Shouldn't log for success or failure"
    
  def testLookForPriorityJobsInJsonDumpStorage(self):
    """
    testLookForPriorityJobsInJsonDumpStorage(self):
      assure that we can find each uuid in standard and deferred storage
      assure that we do not find any bogus uuid
      assure that found uuids are added to jobs table with priority 1, and priority_jobs_NNN table for processor id NNN
    """
    global me
    m = monitor.Monitor(me.config)
    createJDS.createTestSet(createJDS.jsonFileData,jsonKwargs={'logger':me.logger},rootDir=me.config.storageRoot)
    createJDS.createTestSet(createJDS.jsonMoreData,jsonKwargs={'logger':me.logger},rootDir=me.config.deferredStorageRoot)
    normUuids = createJDS.jsonFileData.keys()
    defUuids =  createJDS.jsonMoreData.keys()
    allUuids = []
    allUuids.extend(normUuids)
    allUuids.extend(defUuids)
    badUuid = '0bad0bad-0bad-6666-9999-0bad20001025'
    dbCon,dbCur = m.getDatabaseConnectionPair()
    numProcessors = 5
    dbtestutil.fillProcessorTable(self.connection.cursor(),numProcessors)
    self.markLog()
    m.lookForPriorityJobsInJsonDumpStorage(dbCur,allUuids)
    assert [] == allUuids, 'Expect that all the uuids were found and removed from the looked for "set"'
    m.lookForPriorityJobsInJsonDumpStorage(dbCur,(badUuid,))
    self.markLog()
    seg = self.extractLogSegment()
    getIdAndPrioritySql = "SELECT owner,priority from jobs WHERE uuid = %s"
    getCountSql = "SELECT count(*) from %s"
    idCounts = dict( ( (x,0) for x in range(1,numProcessors+1) ) )
    allUuids.extend(normUuids)
    allUuids.extend(defUuids)
    for uuid in allUuids:
      dbCur.execute(getIdAndPrioritySql,(uuid,))
      procid,pri = dbCur.fetchone()
      assert 1 == pri, 'Expected priority of 1 for %s, but got %s'%(uuid,pri)
      idCounts[procid] += 1
    dbCur.execute(getIdAndPrioritySql,(badUuid,))
    assert not dbCur.fetchone(), "Expect to get None entries in jobs table for badUuid"
    for id,expectCount in idCounts.items():
      dbCur.execute(getCountSql%('priority_jobs_%s'%id))
      seenCount = dbCur.fetchone()[0]
      assert expectCount == seenCount, 'Expected %s, got %s as count in priority_jobs_%s'%(expectCount,seenCount,id)

  def testPriorityJobsNotFound(self):
    """
    testPriorityJobsNotFound(self):
      for each uuid, log an error and remove the uuid from the provided table
    """
    global me
    m = monitor.Monitor(me.config)
    dbCon,dbCur = m.getDatabaseConnectionPair()
    dropBogusSql = "DROP TABLE IF EXISTS bogus;"
    createBogusSql = "CREATE TABLE bogus (uuid varchar(55));"
    insertBogusSql = "INSERT INTO bogus (uuid) VALUES ('NOPE'), ('NEVERMIND');"
    countSql = "SELECT count(*) from %s"
    dbCur.execute(dropBogusSql)
    dbCon.commit()
    dbCur.execute(createBogusSql)
    dbCon.commit()
    dbCur.execute(insertBogusSql)
    dbCon.commit()
    dbCur.execute(countSql%('bogus'))
    bogusCount0 = dbCur.fetchone()[0]
    assert 2 == bogusCount0
    self.markLog()
    m.priorityJobsNotFound(dbCur,['NOPE','NEVERMIND'])
    dbCur.execute(countSql%('bogus'))
    bogusCount1 = dbCur.fetchone()[0]
    assert 2 == bogusCount1, 'Expect uuids deleted, if any, from priorityjobs by default'
    m.priorityJobsNotFound(dbCur,['NOPE','NEVERMIND'], 'bogus')
    dbCur.execute(countSql%('bogus'))
    bogusCount2 = dbCur.fetchone()[0]
    assert 0 == bogusCount2, 'Expect uuids deleted from bogus when it is specified'
    self.markLog()
    dbCur.execute(dropBogusSql)
    dbCon.commit()
    neverCount = 0
    nopeCount = 0
    seg = self.extractLogSegment()
    for line in seg:
      if " - MainThread - priority uuid" in line:
        if 'NOPE was never found' in line: nopeCount += 1
        if 'NEVERMIND was never found' in line: neverCount += 1
    assert 2 == neverCount
    assert 2 == nopeCount
