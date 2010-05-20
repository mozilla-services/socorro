#! /usr/bin/env python

import psycopg2

import time
import datetime
import os
import os.path
import dircache
import shutil
import signal
import threading
import collections

import Queue

import logging

logger = logging.getLogger("monitor")

import socorro.lib.util
import socorro.lib.filesystem
import socorro.lib.psycopghelper as psy
import socorro.database.database as sdb
import socorro.lib.JsonDumpStorage as jds
import socorro.lib.threadlib as thr
import socorro.lib.ooid as ooid
import socorro.collector.crashstorage as cstore
import socorro.hbase.hbaseClient as hbc

#=================================================================================================================
class UuidNotFoundException(Exception):
  pass

#=================================================================================================================
class Monitor (object):
  _config_requirements = ("databaseHost",
                          "databaseName",
                          "databaseUserName",
                          "databasePassword",
                          "processorCheckInTime",
                          "standardLoopDelay",
                          "cleanupJobsLoopDelay",
                          "priorityLoopDelay",
                          "crashStorageClass",
                         )
  _hbase_config_requirements = ("hbaseHost",
                                "hbasePort",
                               )
  _nfs_config_requirements = ("storageRoot",
                              "deferredStorageRoot",
                              "dumpDirPrefix",
                              "dumpPermissions",
                              "dirPermissions",
                              "dumpGID",
                              "saveSuccessfulMinidumpsTo",
                              "saveFailedMinidumpsTo",
                              "jsonFileSuffix",
                              "dumpFileSuffix",
                             )

  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, config, logger=logger, sdb=sdb, cstore=cstore, signal=signal):
    super(Monitor, self).__init__()
    config.logger = logger

    for x in Monitor._config_requirements:
      assert x in config, '%s missing from configuration' % x

    if config.crashStorageClass == 'CrashStorageSystemForNFS':
      for x in Monitor._nfs_config_requirements:
        assert x in config, '%s missing from configuration' % x
    else:
      for x in Monitor._hbase_config_requirements:
        assert x in config, '%s missing from configuration' % x
    self.crashStorePool = cstore.CrashStoragePool(config)

    self.sdb = sdb

    self.standardLoopDelay = config.standardLoopDelay.seconds
    self.cleanupJobsLoopDelay = config.cleanupJobsLoopDelay.seconds
    self.priorityLoopDelay = config.priorityLoopDelay.seconds

    self.databaseConnectionPool = self.sdb.DatabaseConnectionPool(config, logger)

    self.config = config
    signal.signal(signal.SIGTERM, Monitor.respondToSIGTERM)
    signal.signal(signal.SIGHUP, Monitor.respondToSIGTERM)

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
      connection = self.databaseConnectionPool.connection()
      cursor = connection.cursor()
      return (connection, cursor)
    except self.sdb.CannotConnectToDatabase:
      self.quit = True
      self.databaseConnectionPool.cleanup()
      socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a database connection

  #-----------------------------------------------------------------------------------------------------------------
  def cleanUpCompletedAndFailedJobs (self):
    logger.debug("%s - dealing with completed and failed jobs", threading.currentThread().getName())
    # check the jobs table to and deal with the completed and failed jobs
    databaseConnection, databaseCursor = self.getDatabaseConnectionPair()
    try:
      logger.debug("%s - starting loop", threading.currentThread().getName())
      databaseCursor.execute("delete from jobs where id = %s", (jobId,))
      databaseConnection.commit()
      logger.debug("%s - end of this cleanup iteration", threading.currentThread().getName())
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
      logger.info("%s - threshold %s", threading.currentThread().getName(), self.config.processorCheckInTime)
      threshold = psy.singleValueSql(aCursor, "select now() - interval '%s' * 2" % self.config.processorCheckInTime)
      #sql = "select id from processors where lastSeenDateTime < '%s'" % (threshold,)
      #logger.info("%s - dead processors sql: %s", threading.currentThread().getName(), sql)
      aCursor.execute("select id from processors where lastSeenDateTime < '%s'" % (threshold,))
      deadProcessors = aCursor.fetchall()
      aCursor.connection.commit()
      logger.info("%s - dead processors: %s", threading.currentThread().getName(), str(deadProcessors))
      if deadProcessors:
        logger.info("%s - found dead processor(s):", threading.currentThread().getName())
        for aDeadProcessorTuple in deadProcessors:
          logger.info("%s -   %d is dead", threading.currentThread().getName(), aDeadProcessorTuple[0])
        stringOfDeadProcessorIds = ", ".join([str(x[0]) for x in deadProcessors])
        logger.info("%s - getting list of live processor(s):", threading.currentThread().getName())
        aCursor.execute("select id from processors where lastSeenDateTime >= '%s'" % threshold)
        liveProcessors = aCursor.fetchall()
        if not liveProcessors:
          raise Monitor.NoProcessorsRegisteredException("There are no processors registered")
        numberOfLiveProcessors = len(liveProcessors)
        logger.info("%s - getting range of queued date for jobs associated with dead processor(s):", threading.currentThread().getName())
        aCursor.execute("select min(queueddatetime), max(queueddatetime) from jobs where owner in (%s)" % stringOfDeadProcessorIds)
        earliestDeadJob, latestDeadJob = aCursor.fetchall()[0]
        if earliestDeadJob is not None and latestDeadJob is not None:
          timeIncrement = (latestDeadJob - earliestDeadJob) / numberOfLiveProcessors
          for x, liveProcessorId in enumerate(liveProcessors):
            lowQueuedTime = x * timeIncrement + earliestDeadJob
            highQueuedTime = (x + 1) * timeIncrement + earliestDeadJob
            logger.info("%s - assigning jobs from %s to %s to processor %s:", threading.currentThread().getName(), str(lowQueuedTime), str(highQueuedTime), liveProcessorId)
            # why is the range >= at both ends? the range must be inclusive, the risk of moving a job twice is low and consequences low, too.
            # 1st step: take any jobs of a dead processor that were in progress and reset them to unprocessed
            aCursor.execute("""update jobs
                                  set starteddatetime = NULL
                               where
                                  %%s >= queueddatetime
                                  and queueddatetime >= %%s
                                  and owner in (%s)
                                  and success is NULL""" % stringOfDeadProcessorIds, (highQueuedTime, lowQueuedTime))
            # 2nd step: take all jobs of a dead processor and give them to a new owner
            aCursor.execute("""update jobs
                                  set owner = %%s
                               where
                                  %%s >= queueddatetime
                                  and queueddatetime >= %%s
                                  and owner in (%s)""" % stringOfDeadProcessorIds, (liveProcessorId, highQueuedTime, lowQueuedTime))
            aCursor.connection.commit()
        #3rd step - transfer stalled priority jobs to new processor
        for deadProcessorTuple in deadProcessors:
          logger.info("%s - re-assigning priority jobs from processor %d:", threading.currentThread().getName(), deadProcessorTuple[0])
          try:
            aCursor.execute("""insert into priorityjobs (uuid) select uuid from priority_jobs_%d""" % deadProcessorTuple)
            aCursor.connection.commit()
          except:
            aCursor.connection.rollback()
        logger.info("%s - removing all dead processors", threading.currentThread().getName())
        aCursor.execute("delete from processors where lastSeenDateTime < '%s'" % threshold)
        aCursor.connection.commit()
        # remove dead processors' priority tables
        for aDeadProcessorTuple in deadProcessors:
          try:
            aCursor.execute("drop table priority_jobs_%d" % aDeadProcessorTuple[0])
            aCursor.connection.commit()
          except:
            logger.warning("%s - cannot clean up dead processor in database: the table 'priority_jobs_%d' may need manual deletion", threading.currentThread().getName(), aDeadProcessorTuple[0])
            aCursor.connection.rollback()
    except Monitor.NoProcessorsRegisteredException:
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger, showTraceback=False)
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
      sql = """select
                  p.id,
                  count(j.owner)
               from
                  processors p left join jobs j on p.id = j.owner
                                                   and p.lastSeenDateTime > now() - interval %s
                                                   and j.success is null
              group by p.id"""
      try:
        aCursor.execute(sql, (self.config.processorCheckInTime,) )
        logger.debug("%s - sql succeeded", threading.currentThread().getName())
        aCursor.connection.commit()
      except psycopg2.ProgrammingError:
        logger.debug("%s - some other database transaction failed and didn't close properly.  Roll it back and try to continue.", threading.currentThread().getName())
        try:
          aCursor.connection.rollback()
          aCursor.execute(sql)
        except:
          logger.debug("%s - sql failed for the 2nd time - quit", threading.currentThread().getName())
          self.quit = True
          aCursor.connection.rollback()
          socorro.lib.util.reportExceptionAndAbort(logger)
      listOfProcessorIds = [[aRow[0], aRow[1]] for aRow in aCursor.fetchall()]  #processorId, numberOfAssignedJobs
      logger.debug("%s - listOfProcessorIds: %s", threading.currentThread().getName(), str(listOfProcessorIds))
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
    try:
      databaseCursor.execute("insert into jobs (pathname, uuid, owner, priority, queuedDateTime) values (%s, %s, %s, %s, %s)",
                             ('', uuid, processorIdAssignedToThisJob, priority, datetime.datetime.now()))
      logger.debug("%s - executed insert for %s",threading.currentThread().getName(), uuid)
      databaseCursor.connection.commit()
    except:
      databaseCursor.connection.rollback()
      raise
    logger.debug("%s - %s assigned to processor %d", threading.currentThread().getName(), uuid, processorIdAssignedToThisJob)
    return processorIdAssignedToThisJob

  #-----------------------------------------------------------------------------------------------------------------
  def queuePriorityJob (self, databaseCursor, uuid, processorIdSequenceGenerator):
    processorIdAssignedToThisJob = self.queueJob(databaseCursor, uuid, processorIdSequenceGenerator, priority=1)
    if processorIdAssignedToThisJob:
      databaseCursor.execute("insert into priority_jobs_%d (uuid) values ('%s')" % (processorIdAssignedToThisJob, uuid))
    databaseCursor.execute("delete from priorityjobs where uuid = %s", (uuid,))
    databaseCursor.connection.commit()
    return processorIdAssignedToThisJob

  #-----------------------------------------------------------------------------------------------------------------
  def standardJobAllocationLoop(self):
    """
    """
    try:
      crashStorage = self.crashStorePool.crashStorage()
    except hbc.NoConnectionException:
      self.quit = True
      logger.critical("%s - hbase is gone! hbase is gone!", threading.currentThread().getName())
      socorro.lib.util.reportExceptionAndAbort(logger)
    except Exception:
      self.quit = True
      socorro.lib.util.reportExceptionAndContinue(logger)
      raise
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
            for uuid in crashStorage.newUuids():
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
          except hbc.FatalException:
            raise
          except:
            socorro.lib.util.reportExceptionAndContinue(logger, loggingLevel=logging.CRITICAL)
          logger.debug("%s - end of loop - about to sleep", threading.currentThread().getName())
          self.quitCheck()
          self.responsiveSleep(self.standardLoopDelay)
      except hbc.FatalException, x:
        logger.debug("%s - somethings gone horribly wrong with HBase", threading.currentThread().getName())
        socorro.lib.util.reportExceptionAndContinue(logger, loggingLevel=logging.CRITICAL)
        databaseConnection.rollback()
        self.quit = True
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
    aCursor.execute("select * from priorityjobs;")
    setOfPriorityUuids = set()
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
        logger.info("%s - priority job %s was already in the queue, assigned to %d", threading.currentThread().getName(), uuid, prexistingJobOwner)
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
        databaseCursor.execute("delete from priorityjobs where uuid = %s", (uuid,))
        databaseCursor.connection.commit()
        setOfPriorityUuids.remove(uuid)
      except psy.SQLDidNotReturnSingleValue:
        #logger.debug("%s - priority job %s was not already in the queue", threading.currentThread().getName(), uuid)
        pass

  #-----------------------------------------------------------------------------------------------------------------
  def lookForPriorityJobsInDumpStorage(self, databaseCursor, setOfPriorityUuids):
    # check for jobs in symlink directories
    logger.debug("%s - starting lookForPriorityJobsInDumpStorage", threading.currentThread().getName())
    processorIdSequenceGenerator = None
    for uuid in list(setOfPriorityUuids):
      logger.debug("%s - looking for %s", threading.currentThread().getName(), uuid)
      if self.crashStorePool.crashStorage().uuidInStorage(uuid):
        logger.info("%s - priority queuing %s", threading.currentThread().getName(), uuid)
        if not processorIdSequenceGenerator:
          logger.debug("%s - about to get unbalancedJobScheduler", threading.currentThread().getName())
          processorIdSequenceGenerator = self.unbalancedJobSchedulerIter(databaseCursor)
          logger.debug("%s - unbalancedJobScheduler successfully fetched", threading.currentThread().getName())
        processorIdAssignedToThisJob = self.queuePriorityJob(databaseCursor, uuid, processorIdSequenceGenerator)
        logger.info("%s - %s assigned to %d", threading.currentThread().getName(), uuid, processorIdAssignedToThisJob)
        setOfPriorityUuids.remove(uuid)
        databaseCursor.execute("delete from priorityjobs where uuid = %s", (uuid,))
        databaseCursor.connection.commit()

  #-----------------------------------------------------------------------------------------------------------------
  def priorityJobsNotFound(self, databaseCursor, setOfPriorityUuids, priorityTableName="priorityjobs"):
    # we've failed to find the uuids anywhere
    for uuid in setOfPriorityUuids:
      self.quitCheck()
      logger.error("%s - priority uuid %s was never found",  threading.currentThread().getName(), uuid)
      databaseCursor.execute("delete from %s where uuid = %s" % (priorityTableName, "%s"), (uuid,))
      databaseCursor.connection.commit()

  #-----------------------------------------------------------------------------------------------------------------
  def priorityJobAllocationLoop(self):
    logger.info("%s - priorityJobAllocationLoop starting.", threading.currentThread().getName())
    #symLinkIndexPath = os.path.join(self.config.storageRoot, "index")
    #deferredSymLinkIndexPath = os.path.join(self.config.deferredStorageRoot, "index")
    try:
      try:
        while (True):
          databaseConnection, databaseCursor = self.getDatabaseConnectionPair()
          try:
            self.quitCheck()
            setOfPriorityUuids = self.getPriorityUuids(databaseCursor)
            if setOfPriorityUuids:
              logger.debug("%s - beginning search for priority jobs", threading.currentThread().getName())
              self.lookForPriorityJobsAlreadyInQueue(databaseCursor, setOfPriorityUuids)
              self.lookForPriorityJobsInDumpStorage(databaseCursor, setOfPriorityUuids)
              self.priorityJobsNotFound(databaseCursor, setOfPriorityUuids)
          except KeyboardInterrupt:
            logger.debug("%s - inner detects quit", threading.currentThread().getName())
            raise
          except hbc.FatalException:
            raise
          except:
            databaseConnection.rollback()
            socorro.lib.util.reportExceptionAndContinue(logger)
          self.quitCheck()
          logger.debug("%s - sleeping", threading.currentThread().getName())
          self.responsiveSleep(self.priorityLoopDelay)
      except hbc.FatalException, x:
        logger.debug("%s - somethings gone horribly wrong with HBase", threading.currentThread().getName())
        socorro.lib.util.reportExceptionAndContinue(logger, loggingLevel=logging.CRITICAL)
        databaseConnection.rollback()
        self.quit = True
      except (KeyboardInterrupt, SystemExit):
        logger.debug("%s - outer detects quit", threading.currentThread().getName())
        databaseConnection.rollback()
        self.quit = True
    finally:
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
  def start (self):
    priorityJobThread = threading.Thread(name="priorityLoopingThread", target=self.priorityJobAllocationLoop)
    priorityJobThread.start()
    jobCleanupThread = threading.Thread(name="jobCleanupThread", target=self.jobCleanupLoop)
    jobCleanupThread.start()
    try:
      try:
        self.standardJobAllocationLoop()
      finally:
        logger.debug("%s - waiting to join.", threading.currentThread().getName())
        priorityJobThread.join()
        jobCleanupThread.join()
        # we're done - kill all the database connections
        logger.debug("%s - calling databaseConnectionPool.cleanup().", threading.currentThread().getName())
        self.databaseConnectionPool.cleanup()
        self.crashStorePool.cleanup()
    except KeyboardInterrupt:
      logger.debug("%s - KeyboardInterrupt.", threading.currentThread().getName())
      raise SystemExit



