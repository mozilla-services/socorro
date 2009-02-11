#! /usr/bin/env python

import psycopg2

import time
import datetime
import os
import os.path
import dircache
import shutil
import signal
import sets
import threading
import collections

import Queue

import logging

logger = logging.getLogger("monitor")

import socorro.lib.util
import socorro.lib.filesystem
import socorro.lib.psycopghelper as psy
import socorro.lib.JsonDumpStorage as jds
import socorro.lib.threadlib as thr

#=================================================================================================================
class UuidNotFoundException(Exception):
  pass

#=================================================================================================================
class Monitor (object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, config):
    super(Monitor, self).__init__()

    assert "databaseHost" in config, "databaseHost is missing from the configuration"
    assert "databaseName" in config, "databaseName is missing from the configuration"
    assert "databaseUserName" in config, "databaseUserName is missing from the configuration"
    assert "databasePassword" in config, "databasePassword is missing from the configuration"
    assert "storageRoot" in config, "storageRoot is missing from the configuration"
    assert "deferredStorageRoot" in config, "deferredStorageRoot is missing from the configuration"
    assert "jsonFileSuffix" in config, "jsonFileSuffix is missing from the configuration"
    assert "dumpFileSuffix" in config, "dumpFileSuffix is missing from the configuration"
    assert "processorCheckInTime" in config, "processorCheckInTime is missing from the configuration"
    assert "standardLoopDelay" in config, "standardLoopDelay is missing from the configuration"
    assert "cleanupJobsLoopDelay" in config, "cleanupJobsLoopDelay is missing from the configuration"
    assert "priorityLoopDelay" in config, "priorityLoopDelay is missing from the configuration"
    assert "saveSuccessfulMinidumpsTo" in config, "saveSuccessfulMinidumpsTo is missing from the configuration"
    assert "saveFailedMinidumpsTo" in config, "saveFailedMinidumpsTo is missing from the configuration"

    self.standardLoopDelay = config.standardLoopDelay.seconds
    self.cleanupJobsLoopDelay = config.cleanupJobsLoopDelay.seconds
    self.priorityLoopDelay = config.priorityLoopDelay.seconds

    self.databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)

    #self.createLegacyPriorityJobsTable()
    #self.legacySearchEventTrigger = threading.Event()
    #self.legacySearchEventTrigger.clear()

    self.config = config
    signal.signal(signal.SIGTERM, Monitor.respondToSIGTERM)
    signal.signal(signal.SIGHUP, Monitor.respondToSIGTERM)

    self.standardJobStorage = jds.JsonDumpStorage(root=self.config.storageRoot,
                                                  jsonSuffix=self.config.jsonFileSuffix,
                                                  dumpSuffix=self.config.dumpFileSuffix,
                                                  logger=logger)
    self.deferredJobStorage = jds.JsonDumpStorage(root=self.config.deferredStorageRoot,
                                                  jsonSuffix=self.config.jsonFileSuffix,
                                                  dumpSuffix=self.config.dumpFileSuffix,
                                                  logger=logger)
    self.successfulJobStorage = None
    if self.config.saveSuccessfulMinidumpsTo:
      self.successfulJobStorage = jds.JsonDumpStorage(root=self.config.saveSuccessfulMinidumpsTo,
                                                      jsonSuffix=self.config.jsonFileSuffix,
                                                      dumpSuffix=self.config.dumpFileSuffix,
                                                      logger=logger)
    self.failedJobStorage = None
    if self.config.saveFailedMinidumpsTo:
      self.failedJobStorage = jds.JsonDumpStorage(root=self.config.saveFailedMinidumpsTo,
                                                  jsonSuffix=self.config.jsonFileSuffix,
                                                  dumpSuffix=self.config.dumpFileSuffix,
                                                  logger=logger)

    self.quit = False

  #-----------------------------------------------------------------------------------------------------------------
  class NoProcessorsRegisteredException (Exception):
    pass

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def respondToSIGTERM(signalNumber, frame):
    """ these classes are instrumented to respond to a KeyboardInterrupt by cleanly shutting down.
        This function, when given as a handler to for a SIGTERM event, will make the program respond
        to a SIGTERM as neatly as it responds to ^C.
    """
    signame = 'SIGTERM'
    if signalNumber != signal.SIGTERM: signame = 'SIGHUP'
    logger.info("%s - %s detected", threading.currentThread().getName(),signame)
    raise KeyboardInterrupt

  #-----------------------------------------------------------------------------------------------------------------
  def quitCheck(self):
    if self.quit:
      raise KeyboardInterrupt

  #-----------------------------------------------------------------------------------------------------------------
  def responsiveSleep (self, seconds):
    for x in xrange(int(seconds)):
      self.quitCheck()
      time.sleep(1.0)

  #-----------------------------------------------------------------------------------------------------------------
  def getDatabaseConnectionPair (self):
    try:
      return self.databaseConnectionPool.connectionCursorPair()
    except psy.CannotConnectToDatabase:
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a database connection

  ##-----------------------------------------------------------------------------------------------------------------
  #def jsonPathForUuidInJsonDumpStorage(self, uuid):
    #try:
      #jsonPath = self.standardJobStorage.getJson(uuid)
    #except (OSError, IOError):
      #try:
        #jsonPath = self.deferredJobStorage.getJson(uuid)
      #except (OSError, IOError):
        #raise UuidNotFoundException("%s cannot be found in standard or deferred storage" % uuid)
    #return jsonPath

  ##-----------------------------------------------------------------------------------------------------------------
  #def dumpPathForUuidInJsonDumpStorage(self, uuid):
    #try:
      #dumpPath = self.standardJobStorage.getDump(uuid)
    #except (OSError, IOError):
      #try:
        #dumpPath = self.deferredJobStorage.getDump(uuid)
      #except (OSError, IOError):
        #raise UuidNotFoundException("%s cannot be found in standard or deferred storage" % uuid)
    #return dumpPath

  #-----------------------------------------------------------------------------------------------------------------
  def getStorageFor(self, uuid):
    try:
      self.standardJobStorage.getJson(uuid)
      return self.standardJobStorage
    except (OSError, IOError):
      try:
        self.deferredJobStorage.getJson(uuid)
        return self.deferredJobStorage
      except (OSError, IOError):
        raise UuidNotFoundException("%s cannot be found in standard or deferred storage" % uuid)

  #-----------------------------------------------------------------------------------------------------------------
  def removeUuidFromJsonDumpStorage(self, uuid, **kwargs):
    try:
      self.standardJobStorage.remove(uuid)
    except (jds.NoSuchUuidFound, OSError, IOError):
      try:
        self.deferredJobStorage.remove(uuid)
      except (jds.NoSuchUuidFound, OSError, IOError):
        raise UuidNotFoundException("%s cannot be found in standard or deferred storage" % uuid)

  #-----------------------------------------------------------------------------------------------------------------
  def cleanUpCompletedAndFailedJobs (self):
    logger.debug("%s - dealing with completed and failed jobs", threading.currentThread().getName())
    # check the jobs table to and deal with the completed and failed jobs
    databaseConnection, databaseCursor = self.getDatabaseConnectionPair()
    try:
      logger.debug("%s - starting loop", threading.currentThread().getName())
      saveSuccessfulJobs = bool(self.config.saveSuccessfulMinidumpsTo)
      saveFailedJobs = bool(self.config.saveFailedMinidumpsTo)
      databaseCursor.execute("select id, uuid, success from jobs where success is not NULL")
      logger.debug("%s - sql submitted", threading.currentThread().getName())
      for jobId, uuid, success in databaseCursor.fetchall():
        self.quitCheck()
        logger.debug("%s - checking %s, %s", threading.currentThread().getName(), uuid, success)
        try:
          currentStorageForThisUuid = self.getStorageFor(uuid)
          if success:
            if saveSuccessfulJobs:
              logger.debug("%s - saving %s", threading.currentThread().getName(), uuid)
              self.successfulJobStorage.transferOne(uuid, currentStorageForThisUuid, False, True, datetime.datetime.now())
          else:
            if saveFailedJobs:
              logger.debug("%s - saving %s", threading.currentThread().getName(), uuid)
              self.failedJobStorage.transferOne(uuid, currentStorageForThisUuid, False, True, datetime.datetime.now())
          logger.debug("%s - deleting %s", threading.currentThread().getName(), uuid)
          currentStorageForThisUuid.remove(uuid)
        except jds.NoSuchUuidFound:
          logger.warning("%s - %s wasn't found for cleanup.", threading.currentThread().getName(), uuid)
        except:
          socorro.lib.util.reportExceptionAndContinue(logger)
        databaseCursor.execute("delete from jobs where id = %s", (jobId,))
        databaseConnection.commit()
    except Exception, x:
      logger.debug("%s - it died: %s", threading.currentThread().getName(), x)
      databaseConnection.rollback()
      socorro.lib.util.reportExceptionAndContinue(logger)

  #-----------------------------------------------------------------------------------------------------------------
  def cleanUpDeadProcessors (self, aCursor):
    """ look for dead processors - find all the jobs of dead processors and assign them to live processors
        then delete the dead processors
    """
    logger.info("%s - looking for dead processors", threading.currentThread().getName())
    try:
      aCursor.execute("select now() - interval '%s'" % self.config.processorCheckInTime)
      threshold = aCursor.fetchall()[0][0]
      aCursor.execute("select id from processors where lastSeenDateTime < '%s'" % threshold)
      deadProcessors = aCursor.fetchall()
      if deadProcessors:
        logger.info("%s - found dead processor(s):", threading.currentThread().getName())
        for aDeadProcessorTuple in deadProcessors:
          logger.info("%s -   %d is dead", threading.currentThread().getName(), aDeadProcessorTuple[0])
        aCursor.execute("select id from processors where lastSeenDateTime >= '%s'" % threshold)
        liveProcessors = aCursor.fetchall()
        if not liveProcessors:
          raise Monitor.NoProcessorsRegisteredException("There are no processors registered")
        #
        # This code section to reassign jobs from dead processors is blocked because it is very slow
        #
        #numberOfLiveProcessors = len(liveProcessors)
        #aCursor.execute("select count(*) from jobs where owner in (select id from processors where lastSeenDateTime < '%s')" % threshold)
        #numberOfJobsAssignedToDeadProcesors = aCursor.fetchall()[0][0]
        #numberOfJobsPerNewProcessor = numberOfJobsAssignedToDeadProcesors / numberOfLiveProcessors
        #leftOverJobs = numberOfJobsAssignedToDeadProcesors % numberOfLiveProcessors
        #for aLiveProcessorTuple in liveProcessors:
          #aLiveProcessorId = aLiveProcessorTuple[0]
          #logger.info("%s - moving %d jobs from dead processors to procssor #%d", threading.currentThread().getName(), numberOfJobsPerNewProcessor + leftOverJobs, aLiveProcessorId)
          #aCursor.execute("""update jobs set owner = %s, starteddatetime = null where id in
                              #(select id from jobs where owner in
                                #(select id from processors where lastSeenDateTime < %s) limit %s)""", (aLiveProcessorId, threshold, numberOfJobsPerNewProcessor + leftOverJobs))
          #leftOverJobs = 0
        #logger.info("%s - removing all dead processors", threading.currentThread().getName())
        #aCursor.execute("delete from processors where lastSeenDateTime < '%s'" % threshold)
        #aCursor.connection.commit()
        ## remove dead processors' priority tables
        #for aDeadProcessorTuple in deadProcessors:
          #try:
            #aCursor.execute("drop table priority_jobs_%d" % aDeadProcessorTuple[0])
            #aCursor.connection.commit()
          #except:
            #logger.warning("%s - cannot clean up dead processor in database: the table 'priority_jobs_%d' may need manual deletion", threading.currentThread().getName(), aDeadProcessorTuple[0])
            #aCursor.connection.rollback()
    except Monitor.NoProcessorsRegisteredException:
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger)
    except:
      socorro.lib.util.reportExceptionAndContinue(logger)

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def compareSecondOfSequence (x, y):
    return cmp(x[1], y[1])

  #-----------------------------------------------------------------------------------------------------------------
  #@staticmethod
  #def secondOfSequence(x):
    #return x[1]

  #-----------------------------------------------------------------------------------------------------------------
  def jobSchedulerIter(self, aCursor):
    """ This takes a snap shot of the state of the processors as well as the number of jobs assigned to each
        then acts as an iterator that returns a sequence of processor ids.  Order of ids returned will assure that
        jobs are assigned in a balanced manner
    """
    logger.debug("%s - balanced jobSchedulerIter: compiling list of active processors", threading.currentThread().getName())
    try:
      sql = """select p.id, count(j.*) from processors p left join (select owner from jobs where success is null) as j on p.id = j.owner group by p.id;"""
      try:
        aCursor.execute(sql)
        logger.debug("%s - sql succeeded", threading.currentThread().getName())
      except psycopg2.ProgrammingError:
        logger.debug("%s - some other database transaction failed and didn't close properly.  Roll it back and try to continue.", threading.currentThread().getName())
        try:
          aCursor.connection.rollback()
          aCursor.execute(sql)
        except:
          logger.debug("%s - sql failed for the 2nd time - quit", threading.currentThread().getName())
          self.quit = True
          socorro.lib.util.reportExceptionAndAbort(logger)
      listOfProcessorIds = [[aRow[0], aRow[1]] for aRow in aCursor.fetchall()]  #processorId, numberOfAssignedJobs
      if not listOfProcessorIds:
        raise Monitor.NoProcessorsRegisteredException("There are no processors registered")
      while True:
        logger.debug("%s - sort the list of (processorId, numberOfAssignedJobs) pairs", threading.currentThread().getName())
        listOfProcessorIds.sort(Monitor.compareSecondOfSequence)
        # the processor with the fewest jobs is about to be assigned a new job, so increment its count
        listOfProcessorIds[0][1] += 1
        logger.debug("%s - yield the processorId which had the fewest jobs: %d", threading.currentThread().getName(), listOfProcessorIds[0][0])
        yield listOfProcessorIds[0][0]
    except Monitor.NoProcessorsRegisteredException:
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger)

  #-----------------------------------------------------------------------------------------------------------------
  def unbalancedJobSchedulerIter(self, aCursor):
    """ This generator returns a sequence of active processorId without regard to job balance
    """
    logger.debug("%s - unbalancedJobSchedulerIter: compiling list of active processors", threading.currentThread().getName())
    try:
      threshold = psy.singleValueSql( aCursor, "select now() - interval '%s'" % self.config.processorCheckInTime)
      aCursor.execute("select id from processors where lastSeenDateTime > '%s'" % threshold)
      listOfProcessorIds = [aRow[0] for aRow in aCursor.fetchall()]
      if not listOfProcessorIds:
        raise Monitor.NoProcessorsRegisteredException("There are no active processors registered")
      while True:
        for aProcessorId in listOfProcessorIds:
          yield aProcessorId
    except Monitor.NoProcessorsRegisteredException:
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger)

  #-----------------------------------------------------------------------------------------------------------------
  def queueJob (self, databaseCursor, uuid, processorIdSequenceGenerator, priority=0):
    logger.debug("%s - trying to insert %s", threading.currentThread().getName(), uuid)
    processorIdAssignedToThisJob = processorIdSequenceGenerator.next()
    databaseCursor.execute("insert into jobs (pathname, uuid, owner, priority, queuedDateTime) values (%s, %s, %s, %s, %s)",
                               ('', uuid, processorIdAssignedToThisJob, priority, datetime.datetime.now()))
    databaseCursor.connection.commit()
    logger.debug("%s - %s assigned to processor %d", threading.currentThread().getName(), uuid, processorIdAssignedToThisJob)
    return processorIdAssignedToThisJob

  #-----------------------------------------------------------------------------------------------------------------
  def queuePriorityJob (self, databaseCursor, uuid, processorIdSequenceGenerator):
    processorIdAssignedToThisJob = self.queueJob(databaseCursor, uuid, processorIdSequenceGenerator, priority=1)
    if processorIdAssignedToThisJob:
      databaseCursor.execute("insert into priority_jobs_%d (uuid) values ('%s')" % (processorIdAssignedToThisJob, uuid))
    databaseCursor.execute("delete from priorityJobs where uuid = %s", (uuid,))
    databaseCursor.connection.commit()
    return processorIdAssignedToThisJob

  #-----------------------------------------------------------------------------------------------------------------
  def standardJobAllocationLoop(self):
    """
    """
    try:
      try:
        while (True):
          databaseConnection, databaseCursor = self.getDatabaseConnectionPair()
          self.cleanUpDeadProcessors(databaseCursor)
          self.quitCheck()
          # walk the dump indexes and assign jobs
          logger.debug("%s - getting jobSchedulerIter", threading.currentThread().getName())
          processorIdSequenceGenerator = self.jobSchedulerIter(databaseCursor)
          logger.debug("%s - beginning index scan", threading.currentThread().getName())
          try:
            logger.debug("%s - starting destructiveDateWalk", threading.currentThread().getName())
            for uuid in self.standardJobStorage.destructiveDateWalk():
              try:
                logger.debug("%s - looping: %s", threading.currentThread().getName(), uuid)
                self.quitCheck()
                self.queueJob(databaseCursor, uuid, processorIdSequenceGenerator)
              except KeyboardInterrupt:
                logger.debug("%s - inner detects quit", threading.currentThread().getName())
                self.quit = True
                raise
              except:
                socorro.lib.util.reportExceptionAndContinue(logger)
            logger.debug("%s - ended destructiveDateWalk", threading.currentThread().getName())
          except:
            socorro.lib.util.reportExceptionAndContinue(logger)
          logger.debug("%s - end of loop - about to sleep", threading.currentThread().getName())
          self.quitCheck()
          self.responsiveSleep(self.standardLoopDelay)
      except (KeyboardInterrupt, SystemExit):
        logger.debug("%s - outer detects quit", threading.currentThread().getName())
        databaseConnection.rollback()
        self.quit = True
        raise
    finally:
      databaseConnection.close()
      logger.debug("%s - standardLoop done.", threading.currentThread().getName())

  #-----------------------------------------------------------------------------------------------------------------
  def getPriorityUuids(self, aCursor):
    aCursor.execute("select * from priorityJobs")
    setOfPriorityUuids = sets.Set()
    for aUuidRow in aCursor.fetchall():
      setOfPriorityUuids.add(aUuidRow[0])
    return setOfPriorityUuids

  #-----------------------------------------------------------------------------------------------------------------
  def lookForPriorityJobsAlreadyInQueue(self, databaseCursor, setOfPriorityUuids):
    # check for uuids already in the queue
    for uuid in list(setOfPriorityUuids):
      self.quitCheck()
      try:
        prexistingJobOwner = psy.singleValueSql(databaseCursor, "select owner from jobs where uuid = '%s'" % uuid)
        logger.info("%s - priority job %s was already in the queue, assigned to %d - raising its priority", threading.currentThread().getName(), uuid, prexistingJobOwner)
        try:
          databaseCursor.execute("insert into priority_jobs_%d (uuid) values ('%s')" % (prexistingJobOwner, uuid))
        except psycopg2.ProgrammingError:
          logger.debug("%s - %s assigned to dead processor %d - wait for reassignment", threading.currentThread().getName(), uuid, prexistingJobOwner)
          # likely that the job is assigned to a dead processor
          # skip processing it this time around - by next time hopefully it will have been
          # re assigned to a live processor
          databaseCursor.connection.rollback()
          setOfPriorityUuids.remove(uuid)
          continue
        databaseCursor.execute("update jobs set priority = priority + 1 where uuid = %s", (uuid,))
        databaseCursor.execute("delete from priorityJobs where uuid = %s", (uuid,))
        databaseCursor.connection.commit()
        setOfPriorityUuids.remove(uuid)
      except psy.SQLDidNotReturnSingleValue:
        #logger.debug("%s - priority job %s was not already in the queue", threading.currentThread().getName(), uuid)
        pass

  #-----------------------------------------------------------------------------------------------------------------
  def uuidInJsonDumpStorage(self, uuid):
    try:
      uuidPath = self.standardJobStorage.getJson(uuid)
      self.standardJobStorage.markAsSeen(uuid)
    except (OSError, IOError):
      try:
        uuidPath = self.deferredJobStorage.getJson(uuid)
        self.deferredJobStorage.markAsSeen(uuid)
      except (OSError, IOError):
        return False
    return True

  #-----------------------------------------------------------------------------------------------------------------
  def lookForPriorityJobsInJsonDumpStorage(self, databaseCursor, setOfPriorityUuids):
    # check for jobs in symlink directories
    logger.debug("%s - starting lookForPriorityJobsInJsonDumpStorage", threading.currentThread().getName())
    processorIdSequenceGenerator = None
    for uuid in list(setOfPriorityUuids):
      logger.debug("%s - looking for %s", threading.currentThread().getName(), uuid)
      if self.uuidInJsonDumpStorage(uuid):
        logger.info("%s - priority queuing %s", threading.currentThread().getName(), uuid)
        if not processorIdSequenceGenerator:
          logger.debug("%s - about to get unbalancedJobScheduler", threading.currentThread().getName())
          processorIdSequenceGenerator = self.unbalancedJobSchedulerIter(databaseCursor)
          logger.debug("%s - unbalancedJobScheduler successfully fetched", threading.currentThread().getName())
        processorIdAssignedToThisJob = self.queuePriorityJob(databaseCursor, uuid, processorIdSequenceGenerator)
        logger.info("%s - %s assigned to %d", threading.currentThread().getName(), uuid, processorIdAssignedToThisJob)
        setOfPriorityUuids.remove(uuid)
        databaseCursor.execute("delete from priorityJobs where uuid = %s", (uuid,))
        databaseCursor.connection.commit()

  #-----------------------------------------------------------------------------------------------------------------
  def priorityJobsNotFound(self, databaseCursor, setOfPriorityUuids, priorityTableName="priorityJobs"):
    # we've failed to find the uuids anywhere
    for uuid in setOfPriorityUuids:
      self.quitCheck()
      logger.error("%s - priority uuid %s was never found",  threading.currentThread().getName(), uuid)
      databaseCursor.execute("delete from %s where uuid = %s" % (priorityTableName, "%s"), (uuid,))
      databaseCursor.connection.commit()

  #-----------------------------------------------------------------------------------------------------------------
  def priorityJobAllocationLoop(self):
    logger.info("%s - priorityJobAllocationLoop starting.", threading.currentThread().getName())
    symLinkIndexPath = os.path.join(self.config.storageRoot, "index")
    deferredSymLinkIndexPath = os.path.join(self.config.deferredStorageRoot, "index")
    try:
      try:
        while (True):
          #self.legacySearchEventTrigger.clear()
          databaseConnection, databaseCursor = self.getDatabaseConnectionPair()
          try:
            self.quitCheck()
            setOfPriorityUuids = self.getPriorityUuids(databaseCursor)
            if setOfPriorityUuids:
              logger.debug("%s - beginning search for priority jobs", threading.currentThread().getName())
              self.lookForPriorityJobsAlreadyInQueue(databaseCursor, setOfPriorityUuids)
              self.lookForPriorityJobsInJsonDumpStorage(databaseCursor, setOfPriorityUuids)
              #self.queuePriorityJobsForSearchInLegacyStorage(databaseCursor, setOfPriorityUuids)
              self.priorityJobsNotFound(databaseCursor, setOfPriorityUuids)
          except KeyboardInterrupt:
            logger.debug("%s - inner detects quit", threading.currentThread().getName())
            raise
          except:
            databaseConnection.rollback()
            socorro.lib.util.reportExceptionAndContinue(logger)
          self.quitCheck()
          #self.legacySearchEventTrigger.clear()
          logger.debug("%s - sleeping", threading.currentThread().getName())
          self.responsiveSleep(self.priorityLoopDelay)
      except (KeyboardInterrupt, SystemExit):
        logger.debug("%s - outer detects quit", threading.currentThread().getName())
        databaseConnection.rollback()
        self.quit = True
    finally:
      #self.legacySearchEventTrigger.set()
      logger.info("%s - priorityLoop done.", threading.currentThread().getName())

  #-----------------------------------------------------------------------------------------------------------------
  def jobCleanupLoop (self):
    logger.info("%s - jobCleanupLoop starting.", threading.currentThread().getName())
    try:
      try:
        logger.info("%s - sleeping first.", threading.currentThread().getName())
        self.responsiveSleep(self.cleanupJobsLoopDelay)
        while True:
          logger.info("%s - beginning jobCleanupLoop cycle.", threading.currentThread().getName())
          self.cleanUpCompletedAndFailedJobs()
          self.responsiveSleep(self.cleanupJobsLoopDelay)
      except (KeyboardInterrupt, SystemExit):
        logger.debug("%s - got quit message", threading.currentThread().getName())
        self.quit = True
      except:
        socorro.lib.util.reportExceptionAndContinue(logger)
    finally:
      logger.info("%s - jobCleanupLoop done.", threading.currentThread().getName())

  #-----------------------------------------------------------------------------------------------------------------
  # legacy storage section: these routines are temporary for the transition between file system storage techniques
  #-----------------------------------------------------------------------------------------------------------------

  ##-----------------------------------------------------------------------------------------------------------------
  #def createLegacyPriorityJobsTable (self):
    #logger.debug("%s - createLegacyPriorityJobsTable starting.", threading.currentThread().getName())
    #databaseConnection, databaseCursor = self.getDatabaseConnectionPair()
    #try:
      #databaseCursor.execute("create table legacy_priority_jobs (uuid varchar)")
      #databaseConnection.commit()
      #logger.debug("%s - legacy_priority_jobs table created", threading.currentThread().getName())
    #except:
      ##socorro.lib.util.reportExceptionAndContinue(logger)
      #logger.warning("%s - can't create legacy_priority_jobs table, it probably already exists (this is OK)", threading.currentThread().getName())
      #databaseConnection.rollback()

  ##-----------------------------------------------------------------------------------------------------------------
  #def queuePriorityJobsForSearchInLegacyStorage(self, databaseCursor, setOfPriorityUuids):
    ## check for jobs in symlink directories
    #logger.debug("%s - starting queuePriorityJobsForSearchInLegacyStorage", threading.currentThread().getName())
    #if setOfPriorityUuids:
      #processorIdSequenceGenerator = None
      #for uuid in list(setOfPriorityUuids):
        #setOfPriorityUuids.remove(uuid)
        #databaseCursor.execute("delete from priorityjobs where uuid = %s", (uuid,))
        #databaseCursor.execute("insert into legacy_priority_jobs (uuid) values (%s)", (uuid,))
      #databaseCursor.connection.commit()
      #logger.debug("%s - triggering legacy search event", threading.currentThread().getName())
      #self.legacySearchEventTrigger.set()

  ##-----------------------------------------------------------------------------------------------------------------
  #def legacyStoragePriorityJobSearchLoop (self):
    #logger.debug("%s - starting legacyStoragePriorityJobSearchLoop", threading.currentThread().getName())
    #symLinkIndexPath = os.path.join(self.config.storageRoot, "index")
    #deferredSymLinkIndexPath = os.path.join(self.config.deferredStorageRoot, "index")
    #try:
      #try:
        #while (True):
          #try:
            #logger.debug("%s - waiting for legacySearchEventTrigger", threading.currentThread().getName())
            #self.legacySearchEventTrigger.wait()
            #logger.debug("%s - received legacySearchEventTrigger", threading.currentThread().getName())
            #self.quitCheck()
            #databaseConnection, databaseCursor = self.getDatabaseConnectionPair()
            #processorIdSequenceGenerator = None
            #setOfPriorityUuids = sets.Set([x[0] for x in psy.execute(databaseCursor, "select * from legacy_priority_jobs")])
            #if setOfPriorityUuids:
              #logger.debug("%s - about get unbalancedJobScheduler", threading.currentThread().getName())
              #processorIdSequenceGenerator = self.unbalancedJobSchedulerIter(databaseCursor)
              #logger.debug("%s - unbalancedJobScheduler successfully fetched", threading.currentThread().getName())
              #self.searchForPriorityJobsInLegacyStorage(setOfPriorityUuids, processorIdSequenceGenerator, symLinkIndexPath, 1)
              #self.searchForPriorityJobsInLegacyStorage(setOfPriorityUuids, processorIdSequenceGenerator, deferredSymLinkIndexPath, 2)
              #self.priorityJobsNotFound(databaseCursor, setOfPriorityUuids, "legacy_priority_jobs")
          #except KeyboardInterrupt:
            #self.quit = True
            #raise
          #except psy.CannotConnectToDatabase:
            #socorro.lib.util.reportExceptionAndAbort(logger)
          #except:
            #socorro.lib.util.reportExceptionAndContinue(logger)
      #except (KeyboardInterrupt, SystemExit):
        #logger.debug("%s - quit detected", threading.currentThread().getName())
        ##databaseConnection.rollback()
        #self.quit = True
    #finally:
      ##databaseConnection.close()
      #logger.info("%s - legacy search loop done.", threading.currentThread().getName())

  ##-----------------------------------------------------------------------------------------------------------------
  #def searchForPriorityJobsInLegacyStorage(self, priorityUuids, processorIdSequenceGenerator, symLinkIndexPath, searchDepth):
    ## check for jobs in legacy symlink directories
    #threadName = threading.currentThread().getName()
    #logger.debug("%s - starting searchForPriorityJobsInLegacyStorage in %s", threadName, symLinkIndexPath)
    #if not priorityUuids:
      #return
    #try:
      #for path, file, currentDirectory in socorro.lib.filesystem.findFileGenerator(symLinkIndexPath,lambda x: os.path.isdir(x[2]),maxDepth=searchDepth,directorySortFunction=lambda x,y:-cmp(x,y)):  # list all directories
        #if not priorityUuids:
          #break
        #for uuid in list(priorityUuids):
          #logger.debug("%s - looking for %s", threadName, uuid)
          #self.quitCheck()
          #absoluteSymLinkPathname = os.path.join(currentDirectory, "%s.symlink" % uuid)
          #logger.debug("%s -         as %s", threadName, absoluteSymLinkPathname)
          #try:
            #relativeJsonPathname = os.readlink(absoluteSymLinkPathname)
            #absoluteJsonPathname = os.path.normpath(os.path.join(currentDirectory, relativeJsonPathname))
            #absoluteDumpPathname = "%s%s" % (absoluteJsonPathname[:-len(self.config.jsonFileSuffix)], self.config.dumpFileSuffix)
          #except OSError:
            #logger.debug("%s -         Not it...", threadName)
            #continue
          #logger.debug("%s -         FOUND", threadName)
          #logger.info("%s - priority queuing %s", threadName, absoluteJsonPathname)
          #try:
            #self.standardJobStorage.copyFrom(uuid, absoluteJsonPathname, absoluteDumpPathname, "legacy", datetime.datetime.now(), False, True)
            #databaseConnection, databaseCursor = self.getDatabaseConnectionPair()
            #processorIdAssignedToThisJob = self.queuePriorityJob(databaseCursor, uuid, processorIdSequenceGenerator)
            #logger.info("%s - %s assigned to %d", threadName, uuid, processorIdAssignedToThisJob)
          #except IOError, x:
            #logger.warning("%s - unable to process %s because %s", threadName, uuid, x)
          #logger.warning("%s - about to remove %s from legacy_priority_jobs", threadName, uuid)
          #databaseCursor.execute("delete from legacy_priority_jobs where uuid = %s", (uuid,))
          #databaseCursor.connection.commit()
          #priorityUuids.remove(uuid)
    #except OSError, x:
      #logger.warning("%s - searchForPriorityJobsInLegacyStorage had trouble: %s", threadName, x)

  ## end of legacy storage section
  #-----------------------------------------------------------------------------------------------------------------

  #-----------------------------------------------------------------------------------------------------------------
  def start (self):
    priorityJobThread = threading.Thread(name="priorityLoopingThread", target=self.priorityJobAllocationLoop)
    priorityJobThread.start()
    jobCleanupThread = threading.Thread(name="jobCleanupThread", target=self.jobCleanupLoop)
    jobCleanupThread.start()
    #legacySearchThread = threading.Thread(name="legacySearchThread", target=self.legacyStoragePriorityJobSearchLoop)
    #legacySearchThread.start()
    try:
      try:
        self.standardJobAllocationLoop()
      finally:
        logger.debug("%s - waiting to join.", threading.currentThread().getName())
        priorityJobThread.join()
        jobCleanupThread.join()
        #legacySearchThread.join()
        # we're done - kill all the database connections
        logger.debug("%s - calling databaseConnectionPool.cleanup().", threading.currentThread().getName())
        self.databaseConnectionPool.cleanup()
    except KeyboardInterrupt:
      logger.debug("%s - KeyboardInterrupt.", threading.currentThread().getName())
      raise SystemExit



