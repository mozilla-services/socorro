import unittest

import copy
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

import socorro.lib.ConfigurationManager as configurationManager
import socorro.monitor.monitor as monitor

import socorro.unittest.lib.createJsonDumpStore as createJDS

import monitorTestconfig as testConfig
from createMonitorDB import CreateMonitorDB

cc = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Monitor')

class Me(): # not quite "self"
  """I need setUpOncePerClass() that runs only once for the whole test class. Not only does unittest not provide that, it actively
  perverts my needs by replacing the TestMonitor instance with each iteration of TestMonitor.testSomething(). To work around that,
  I'll use the Me class instance to hold attributes, and the class to hold the instance. Jeez.
  """
  me = None

markingTemplate = "MARK %s: %s"
startMark = 'start'
endMark = 'end'

class TestMonitor(unittest.TestCase):
  """
  This uses an 'orrible 'ack to circumvent the otherwise helpful unittest which runs each test in a new instance of the TestMonitor class
  static method startOnce() is a 'run once per test class' method that offloads data to Me.me... in a better world it would be setUpClass()
  static method stopOnce() is the balancing method for startOnce(). We use introspection on TestMonitor to find out how many tests will
  run, and call stopOnce() after the last test has run.
  setUp() and tearDown() do the expected once-per-test initialization and cleanup, and trigger startOnce() and stopOnce() when needed
  """
  markingLog = False
  @staticmethod
  def startOnce():
    """ the 'orrible 'ack itself, part one"""
    if not Me.me:
      #print "STARTING ONCE"
      Me.me = Me()
      me = Me.me
      me.createMonitorDB = CreateMonitorDB()
      me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Monitor')
      knownTests = [x for x in dir(TestMonitor) if x.startswith('test')]
      me.testsLeftToRun = len(knownTests)
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
    else:
      pass #print 'SKIPPING THE START at count %d'%Me.me.testsLeftToRun

  @staticmethod
  def stopOnce():
    """the 'orrible 'ack itself; part two"""
    me = Me.me
    if me.testsLeftToRun > 0:
      pass
    else:
      logging.shutdown()
      try:
        os.unlink(me.logFilePathname)
      except OSError,x:
        if errno.ENOENT != x.errno:
          raise

  def setUp(self):
    TestMonitor.startOnce()
    me = Me.me
    # these are cut-n-pasted from testJsonDumpStorage
    self.jsonFileData = {
      '0bba61c5-dfc3-43e7-87e6-8afd20071025': ('2007-10-25-05-04','webhead02','0b/ba/61/c5','2007/10/25/05/00/webhead02_0'),
      '0bba929f-8721-460c-8e70-a43c20071025': ('2007-10-25-05-04','webhead02','0b/ba/92/9f','2007/10/25/05/00/webhead02_0'),
      '0b9ff107-8672-4aac-8b75-b2bd20081225': ('2008-12-25-05-00','webhead01','0b/9f/f1/07','2008/12/25/05/00/webhead01_0'),
      '22adfb61-f75b-11dc-b6be-001320081225': ('2008-12-25-05-01','webhead01','22/ad/fb/61','2008/12/25/05/00/webhead01_0'),
      'b965de73-ae90-a935-1357-03ae20081225': ('2008-12-25-05-04','webhead01','b9/65/de/73','2008/12/25/05/00/webhead01_0'),
      '0b781b88-ecbe-4cc4-893f-6bbb20081225': ('2008-12-25-05-05','webhead01','0b/78/1b/88','2008/12/25/05/05/webhead01_0'),
      '0b8344d6-9021-4db9-bf34-a15320081225': ('2008-12-25-05-06','webhead01','0b/83/44/d6','2008/12/25/05/05/webhead01_0'),
      '0b94199b-b90b-4683-a38a-411420081226': ('2008-12-26-05-21','webhead01','0b/94/19/9b','2008/12/26/05/20/webhead01_0'),
      '0b9eedc3-9a79-4ce2-83eb-155920081226': ('2008-12-26-05-24','webhead01','0b/9e/ed/c3','2008/12/26/05/20/webhead01_0'),
      '0b9fd6da-27e4-46aa-bef3-3deb20081226': ('2008-12-26-05-25','webhead02','0b/9f/d6/da','2008/12/26/05/25/webhead02_0'),
      '0ba32a30-2476-4724-b825-de17e3081125': ('2008-11-25-05-00','webhead02','0b/a3/2a','2008/11/25/05/00/webhead02_0'),
      '0bad640f-5825-4d42-b96e-21b8e3081125': ('2008-11-25-05-04','webhead02','0b/ad/64','2008/11/25/05/00/webhead02_0'),
      '0bae7049-bbff-49f2-b408-7e9fe2081125': ('2008-11-25-05-05','webhead02','0b/ae','2008/11/25/05/05/webhead02_0'),
      '0baf1b4d-dad3-4d35-ae7e-b9dce2081125': ('2008-11-25-05-06','webhead02','0b/af','2008/11/25/05/05/webhead02_0'),
    }
    # these are cut-n-pasted from testJsonDumpStorage
    self.jsonMoreData =  {
      '28adfb61-f75b-11dc-b6be-001320081225': ('2008-12-25-05-01','webhead01','28/ad/fb/61','2008/12/25/05/00'),
      '29adfb61-f75b-11dc-b6be-001320081225': ('2008-12-25-05-00','webhead01','29/ad/fb/61','2008/12/25/05/00'),
    }

    self.connection = psycopg2.connect(me.dsn)
    #print "SETUP: ",self.connection
    cursor = self.connection.cursor()
    me.createMonitorDB.createDB(cursor=cursor)

  def tearDown(self):
    me = Me.me
    me.testsLeftToRun -= 1
    #print "TearDown: COUNT %d"%me.testsLeftToRun
    me.createMonitorDB.dropDB(dsn=Me.me.dsn)
    try:
      shutil.rmtree(me.config.storageRoot)
    except OSError,x:
      pass
    try:
      shutil.rmtree(me.config.deferredStorageRoot)
    except OSError,x:
      pass
    TestMonitor.stopOnce()

  def markLog(self):
    me = Me.me
    testName = traceback.extract_stack()[-2][2]
    if TestMonitor.markingLog:
      TestMonitor.markingLog = False
      me.logger.info(markingTemplate%(testName,endMark))
      #print (' ==== <<%s>> '+markingTemplate)%(os.getpid(),testName,endMark) #DEBUG
    else:
      TestMonitor.markingLog = True
      me.logger.info(markingTemplate%(testName,startMark))
      #print (' ==== <<%s>> '+markingTemplate)%(os.getpid(),testName,startMark) #DEBUG

  def extractLogSegment(self):
    testName = traceback.extract_stack()[-2][2]
    #print ' ==== <<%s>> EXTRACTING: %s (%s)'%(os.getpid(),testName,Me.me.logWasExtracted[testName]) #DEBUG
    if Me.me.logWasExtracted[testName]:
      return []
    try:
      file = open(Me.me.config.logFilePathname)
    except IOError,x:
      if errno.ENOENT != x.errno:
        raise
      else:
        return []
      
    Me.me.logWasExtracted[testName] = True
    startTag = markingTemplate%(testName,startMark)
    stopTag = markingTemplate%(testName,endMark)
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
    self.markLog()
    me = Me.me
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
    for rc in requiredConfigs:
      del(cc[rc])
      try:
        m = monitor.Monitor(cc)
        assert False, "expected to raise AssertionError for missing %s"%rc
      except Exception,x:
        pass
      cc[rc] = me.config[rc]
    monitor.Monitor(me.config) # expect this to work. If it raises an error, we'll see it
    self.markLog()
    assert [] == self.extractLogSegment(), 'expected no logging for constructor call (success or failure)'

  def testStart(self):
    self.markLog()
    me = Me.me
    time.sleep(.1)
    pid = os.fork()
    if(pid):
      me.logger.info("Parent/Child PIDs: (%s/%s)"%(os.getpid(),pid))
      #print "PARENT: __testStart()__ id/Child PIDs: (%s/%s)"%(os.getpid(),pid) #DEBUG
      time.sleep(.1)
      os.kill(pid,signal.SIGTERM)
      while True:
        wpid,info = os.wait()
        if wpid == pid: break
    else: # I am the child process
      #print "CHILD:  __testStart()__ parent/self PIDs: (%s/%s)"%(os.getppid(),os.getpid()) #DEBUG
      try:
        m = monitor.Monitor(Me.me.config)
        m.start()
        assert False, "Never expect to get to this line (Parent will kill -SIGTERM)"
      except BaseException,x:
        me.logger.info("CHILD Exception in %s: %s [%s]"%(threading.currentThread().getName(),type(x),x))
        os._exit(0)
    self.markLog()
    seg = self.extractLogSegment()
    assert 27 == len(seg), "Careful calculation. (Or else a debug run) indicates we should have precisely 27 items here. But got %d"%(len(seg))
    info = 0
    debug = 0
    main = 0
    priorityLooping = 0
    jobCleanup = 0
    other = 0
    foundSigterm = False
    foundSighup = False
    for i in seg:
      date,tyme,level,dash,msg = i.split(None,4)
      #print 'DEBUG d:%s, L:%s, M:%s'%(date,level,msg)
      if level == 'INFO': info += 1
      if level == 'DEBUG': debug += 1
      if msg.startswith('MainThread'):
        main += 1
        if 'SIGTERM detected' in msg: foundSigterm = True
        if 'SIGHUP detected' in msg: foundSighup = True
      elif msg.startswith('priorityLooping'): priorityLooping += 1
      elif msg.startswith('jobCleanup'): jobCleanup += 1
      else: other += 1
    assert foundSigterm
    assert not foundSighup
    assert 11 == info
    assert 16 == debug
    assert 16 == main
    assert 5 == priorityLooping
    assert 4 == jobCleanup
    assert 2 == other

  def testRespondToSIGHUP(self):
    self.markLog()
    me = Me.me
    time.sleep(.1)
    pid = os.fork()
    if(pid):
      me.logger.info("Parent/Child PIDs: (%s/%s)"%(os.getpid(),pid))
      #print "PARENT: __testStart()__ id/Child PIDs: (%s/%s)"%(os.getpid(),pid) #DEBUG
      time.sleep(.1)
      os.kill(pid,signal.SIGHUP)
      while True:
        wpid,info = os.wait()
        if wpid == pid: break
    else: # I am the child process
      #print "CHILD:  __testStart()__ parent/self PIDs: (%s/%s)"%(os.getppid(),os.getpid()) #DEBUG
      try:
        m = monitor.Monitor(Me.me.config)
        m.start()
        assert False, "Never expect to get to this line (Parent will kill -SIGTERM)"
      except BaseException,x:
        me.logger.info("CHILD Exception in %s: %s [%s]"%(threading.currentThread().getName(),type(x),x))
        os._exit(0)
    self.markLog()
    seg = self.extractLogSegment()
    assert 27 == len(seg), "Careful calculation. (Or else a debug run) indicates we should have precisely 27 items here. Got %d"%(len(seg))
    info = 0
    debug = 0
    main = 0
    priorityLooping = 0
    jobCleanup = 0
    other = 0
    foundSigterm = False
    foundSighup = False
    for i in seg:
      date,tyme,level,dash,msg = i.split(None,4)
      #print 'DEBUG d:%s, L:%s, M:%s'%(date,level,msg)
      if level == 'INFO': info += 1
      if level == 'DEBUG': debug += 1
      if msg.startswith('MainThread'):
        main += 1
        if 'SIGTERM' in msg: foundSigterm = True
        if 'SIGHUP' in msg: foundSighup = True
      elif msg.startswith('priorityLooping'): priorityLooping += 1
      elif msg.startswith('jobCleanup'): jobCleanup += 1
      else: other += 1
    assert not foundSigterm
    assert foundSighup
    assert 11 == info
    assert 16 == debug
    assert 16 == main
    assert 5 == priorityLooping
    assert 4 == jobCleanup
    assert 2 == other
     
  def testQuitCheck(self):
    self.markLog()
    mon = monitor.Monitor(Me.me.config)
    mon.quit = True
    try:
      mon.quitCheck()
      assert False, 'Expected monitor to raise a KeyboardInterrupt, not ignore us'
    except KeyboardInterrupt,x:
      pass
    except BaseException, x:
      assert False, 'Expected monitor to raise a KeyboardInterrupt, not %s: %s'%(type(x),x)
    self.markLog()
    assert [] == self.extractLogSegment()

  def quitter(self):
    time.sleep(self.timeTilQuit)
    self.mon.quit = True
  
  def testResponsiveSleep(self):
    self.markLog()
    mon = monitor.Monitor(Me.me.config)
    self.timeTilQuit = 2
    self.mon = mon
    quitter = threading.Thread(name='Quitter', target=self.quitter)
    quitter.start()
    try:
      mon.responsiveSleep(5)
      assert False, 'expected to have a KeyboardInterrupt raised'
    except KeyboardInterrupt:
      pass
    quitter.join()
    self.markLog()
    assert [] == self.extractLogSegment()

  def testGetDatabaseConnectionPair(self):
    me = Me.me
    self.markLog()
    mon = monitor.Monitor(me.config)
    tcon,tcur = mon.getDatabaseConnectionPair()
    mcon,mcur = mon.databaseConnectionPool.connectionCursorPair()
    self.markLog()
    seg = self.extractLogSegment()
    assert tcon == mcon
    assert tcur == mcur
    assert 1 == len(seg)
    assert 'INFO' in seg[0]
    assert 'connecting to database' in seg[0]

  def testGetStorageFor(self):
    self.markLog()
    createJDS.createTestSet(self.jsonFileData,jsonKwargs={'logger':Me.me.logger},rootDir=Me.me.config.storageRoot)
    createJDS.createTestSet(self.jsonMoreData,jsonKwargs={'logger':Me.me.logger},rootDir=Me.me.config.deferredStorageRoot)
    mon = monitor.Monitor(Me.me.config)
    try:
      mon.getStorageFor('nothing')
      assert False,'Expected to throw UuidNotFoundException'
    except monitor.UuidNotFoundException,x:
      pass
    expected = Me.me.config.storageRoot.rstrip(os.sep)
    got = mon.getStorageFor('0bba929f-8721-460c-8e70-a43c20071025').root
    assert expected == got, 'Expected [%s] got [%s]'%(expected,got)

    expected = Me.me.config.deferredStorageRoot.rstrip(os.sep)
    got = mon.getStorageFor('29adfb61-f75b-11dc-b6be-001320081225').root
    assert expected == got, 'Expected [%s] got [%s]'%(expected,got)
    self.markLog()
    assert [] == self.extractLogSegment(), 'expected no logging for this test'

  def testRemoveBadUuidFromJsonDumpStorage(self):
    self.markLog()
    createJDS.createTestSet(self.jsonFileData,jsonKwargs={'logger':Me.me.logger},rootDir=Me.me.config.storageRoot)
    mon = monitor.Monitor(Me.me.config)
    badUuid = '0bad0bad-0bad-6666-9999-0bad20001025'
    try:
      mon.removeUuidFromJsonDumpStorage(badUuid)
      assert False, 'Expected to raise UuidNotFounException in line above'
    except monitor.UuidNotFoundException:
      pass
    except Exception,x:
      assert False, 'Expected to catch UuidNotFounException, not %s (%s)'%(type(x),x)
    self.markLog()
    seg = self.extractLogSegment()
    #print "\n  --","\n  -- ".join(seg)
    assert 12 == len(seg), 'Expected 12, got %d'%(len(seg))
    warnings = 0
    debugs = 0
    for line in seg:
      assert 'MainThread' in line, 'Expected all the messages from main thread'
      assert badUuid in line, 'Expected that all messages are about the bad uuid, but got %s'%line
      if 'DEBUG' in line: debugs += 1
      if 'WARNING' in line: warnings += 1
    assert warnings == 2, 'Expected a "totally unknown" warning from storage and deferred storage'
    assert debugs == 10, 'Expected 5 each warnings about missing or not unlinkable from storage and deferred storage'
    
  def testRemoveGoodUuidFromJsonDumpStorage(self):
    self.markLog()
    createJDS.createTestSet(self.jsonFileData,jsonKwargs={'logger':Me.me.logger},rootDir=Me.me.config.storageRoot)
    createJDS.createTestSet(self.jsonMoreData,jsonKwargs={'logger':Me.me.logger},rootDir=Me.me.config.deferredStorageRoot)
    mon = monitor.Monitor(Me.me.config)
    goodUuid = '0b781b88-ecbe-4cc4-893f-6bbb20081225';
    mon.removeUuidFromJsonDumpStorage(goodUuid)
    # expect no exception here
    try:
      # but here is a duplicate removal. Expect trouble
      mon.removeUuidFromJsonDumpStorage(goodUuid)
      assert False, 'Expected to get UuidNotFounException in line above'
    except monitor.UuidNotFoundException:
      pass
    except:
      assert False, 'Expected to get UuidNotFounException not %s (%s)'%(type(x),x)
    self.markLog()
    seg = self.extractLogSegment()
    
    assert 12 == len(seg), 'Expected 12, got %d'%(len(seg))
    warnings = 0
    debugs = 0
    for line in seg:
      assert 'MainThread' in line, 'Expected all the messages from main thread'
      assert goodUuid in line, 'Expected that all messages are about the duplicate uuid, but got %s'%line
      if 'DEBUG' in line: debugs += 1
      if 'WARNING' in line: warnings += 1
    assert warnings == 2, 'Expected a "totally unknown" warning from storage and deferred storage'
    assert debugs == 10, 'Expected 5 each warnings about missing or not unlinkable from storage and deferred storage'
      
  def testCompareSecondOfSequence(self):
    self.markLog()
    x = (1,10)
    y = (10,1)
    assert cmp(x,y) < 0 # check assumptions about cmp...
    assert monitor.Monitor.compareSecondOfSequence(x,y) > 0
    assert cmp(y,x) > 0
    assert monitor.Monitor.compareSecondOfSequence(y,x) < 0
    self.markLog()
    
#   def testCleanUpCompletedAndFailedJobs(self):
#     self.markLog()
#     self.markLog()
#   def testCleanUpDeadProcessors(self):
#     self.markLog()
#     self.markLog()
#   def testJobSchedulerIter(self):
#     self.markLog()
#     self.markLog()
#   def testUnbalancedSchedulerIter(self):
#     self.markLog()
#     self.markLog()
#   def testQueueJob(self):
#     self.markLog()
#     self.markLog()
#   def testQueuePriorityJob(self):
#     self.markLog()
#     self.markLog()
#   def testStandardJobAllocationLoop(self):
#     self.markLog()
#     self.markLog()
#   def testGetPriorityUuids(self):
#     self.markLog()
#     self.markLog()
#   def testLookForPriorityJobsAlreadyInQueue(self):
#     self.markLog()
#     self.markLog()
#   def testUuidInJsonDumpStorage(self):
#     self.markLog()
#     self.markLog()
#   def testLookForPriorityJobsInJsonDumpStorage(self):
#     self.markLog()
#     self.markLog()
#   def testPriorityJobsNotFound(self):
#     self.markLog()
#     self.markLog()
#   def testPriorityJobAllocationLoop(self):
#     self.markLog()
#     self.markLog()
#   def testJobCleanupLoop(self):
#     self.markLog()
#     self.markLog()
  
if __name__ == "__main__":
  unittest.main()

