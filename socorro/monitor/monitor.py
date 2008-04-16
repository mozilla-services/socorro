#! /usr/bin/env python

import psycopg2

import time
import datetime
import os
import os.path
import shutil
import signal
import sets
import threading

import logging

logger = logging.getLogger("monitor")

import socorro.lib.util



class Monitor (object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, configurationContext):
    super(Monitor, self).__init__()
    self.config = configurationContext
    signal.signal(signal.SIGTERM, Monitor.respondToSIGTERM)
    self.insertionLock = threading.RLock()
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
    logger.info("%s - SIGTERM detected", threading.currentThread().getName())
    raise KeyboardInterrupt
  
  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def ignoreDuplicateDatabaseInsert (exceptionType, exception, tracebackInfo):
    return exceptionType is psycopg2.IntegrityError
  
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
  def archiveCompletedJobFiles (self, jsonPathname, uuid, newFileExtension):
    logger.debug("%s - archiving %s", threading.currentThread().getName(), jsonPathname)
    newJsonPathname = ("%s/%s%s.%s" % (self.config.saveMinidumpsTo, uuid, self.config.jsonFileSuffix, newFileExtension)).replace('//','/')
    try:
      shutil.move(jsonPathname, newJsonPathname)
    except:
      socorro.lib.util.reportExceptionAndContinue(logger)
    try:
      dumpPathname = "%s%s" % (jsonPathname[:-len(self.config.jsonFileSuffix)], self.config.dumpFileSuffix)
      newDumpPathname = ("%s/%s%s.%s" % (self.config.saveMinidumpsTo, uuid, self.config.dumpFileSuffix, newFileExtension)).replace('//','/')
      logger.debug("%s - archiving %s", threading.currentThread().getName(), dumpPathname)
      shutil.move(dumpPathname, newDumpPathname)
    except:
      socorro.lib.util.reportExceptionAndContinue(logger)

  #-----------------------------------------------------------------------------------------------------------------
  def deleteCompletedJobFiles (self, jsonPathname, unused1, unused2):
    logger.debug("%s - deleting %s", threading.currentThread().getName(), jsonPathname)
    try:
      os.remove(jsonPathname)
    except:
      socorro.lib.util.reportExceptionAndContinue(logger) 
    try:
      dumpPathname = "%s%s" % (jsonPathname[:-len(self.config.jsonFileSuffix)], self.config.dumpFileSuffix)
      os.remove(dumpPathname)
    except:
      socorro.lib.util.reportExceptionAndContinue(logger)

  #-----------------------------------------------------------------------------------------------------------------
  def cleanUpCompletedAndFailedJobs (self, databaseConnection, aCursor):
    logger.debug("%s - dealing with completed and failed jobs", threading.currentThread().getName())
    # check the jobs table to and deal with the completed and failed jobs
    try:
      aCursor.execute("select id, pathname, uuid from jobs where success is False")
      fileDisposalFunction = (self.deleteCompletedJobFiles, self.archiveCompletedJobFiles)[self.config.saveFailedMinidumps]
      for jobId, jsonPathname, uuid in aCursor.fetchall():
        self.quitCheck()
        fileDisposalFunction(jsonPathname, uuid, "failed")
        aCursor.execute("delete from jobs where id = %s", (jobId,))
      fileDisposalFunction = (self.deleteCompletedJobFiles, self.archiveCompletedJobFiles)[self.config.saveProcessedMinidumps]
      aCursor.execute("select id, pathname, uuid from jobs where success is True")
      for jobId, jsonPathname, uuid in aCursor.fetchall():
        self.quitCheck()
        fileDisposalFunction(jsonPathname, uuid, "processed")
        aCursor.execute("delete from jobs where id = %s", (jobId,))
      databaseConnection.commit()
    except:
      databaseConnection.rollback()
      socorro.lib.util.reportExceptionAndContinue(logger)      
      
  #-----------------------------------------------------------------------------------------------------------------
  def cleanUpDeadProcessors (self, databaseConnection, aCursor):
    """ look for dead processors - delete the processor from the processors table and, via cascade, 
        delete its associated jobs.  The abandoned jobs will be picked up again by walking the dump 
        tree and assigned to other processors."""
    logger.debug("%s - looking for dead processors", threading.currentThread().getName())
    try:
      aCursor.execute("delete from processors where lastSeenDateTime < (now() - interval '%s')" % self.config.processorCheckInTime)
      databaseConnection.commit()
    except:
      socorro.lib.util.reportExceptionAndContinue(logger) 
      
  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def compareSecondOfSequence (x, y):
    return cmp(x[1], y[1])
  
  #-----------------------------------------------------------------------------------------------------------------
  def jobSchedulerIter(self, aCursor):
    """ This takes a snap shot of the state of the processors as well as the number of jobs assigned to each
        then acts as an iterator that returns a sequence of processor ids.  Order of ids returned will assure that
        jobs are assigned in a balanced manner
    """        
    logger.debug("%s - compiling list of active processors", threading.currentThread().getName())
    try:
      aCursor.execute("""select p.id, count(j.*) from processors p left join jobs j on p.id = j.owner group by p.id""")
      listOfProcessorIds = [[aRow[0], aRow[1]] for aRow in aCursor.fetchall()]  #processorId, numberOfAssignedJobs
      if not listOfProcessorIds:
        raise Monitor.NoProcessorsRegisteredException("There are no processors registered")    
      while True:
        # sort the list of (processorId, numberOfAssignedJobs) pairs
        listOfProcessorIds.sort(Monitor.compareSecondOfSequence)
        # the processor with the fewest jobs is about to be assigned a new job, so increment its count
        listOfProcessorIds[0][1] += 1
        # yield the processorId which had the fewest jobs
        yield listOfProcessorIds[0][0]
    except Monitor.NoProcessorsRegisteredException:
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger)
      
  #-----------------------------------------------------------------------------------------------------------------
  def directoryJudgedDeletable (self, pathname, subDirectoryList, fileList):
    if not (subDirectoryList or fileList) and pathname != self.config.storageRoot: #if both directoryList and fileList are empty
      #select an ageLimit from two options based on the if target directory name has a prefix of "dumpDirPrefix"
      ageLimit = (self.config.dateDirDelta, self.config.dumpDirDelta)[os.path.basename(pathname).startswith(self.config.dumpDirPrefix)]
      return (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(os.path.getmtime(pathname))) > ageLimit
    return False
  
  #-----------------------------------------------------------------------------------------------------------------
  def passJudgementOnDirectory(self, currentDirectory, subDirectoryList, fileList):
    logger.debug("%s - %s", threading.currentThread().getName(), currentDirectory)
    try:
      if self.directoryJudgedDeletable(currentDirectory, subDirectoryList, fileList):
        logger.debug("%s - removing - %s", threading.currentThread().getName(),  currentDirectory)
        os.rmdir(currentDirectory)
      else:
        logger.debug("%s - not eligible for deletion - %s", threading.currentThread().getName(),  currentDirectory)
    except Exception:
      socorro.lib.util.reportExceptionAndContinue(logger)
      
  #-----------------------------------------------------------------------------------------------------------------
  def queueJob (self, databaseConnection, databaseCursor, currentDirectory, aFileName, processorIdSequenceGenerator, priority=0):
    logger.debug("%s - priority %d queuing %s", threading.currentThread().getName(), priority, aFileName)
    try:
      jsonFilePathName = os.path.join(currentDirectory, aFileName)
      uuid = aFileName[:-len(self.config.jsonFileSuffix)]
      logger.debug("%s - trying to insert %s", threading.currentThread().getName(), uuid)
      processorIdAssignedToThisJob = processorIdSequenceGenerator.next()
      databaseCursor.execute("insert into jobs (pathname, uuid, owner, priority, queuedDateTime) values (%s, %s, %s, %s, %s)", 
                                 (jsonFilePathName, uuid, processorIdAssignedToThisJob, priority, datetime.datetime.now()))
      databaseConnection.commit()
      logger.debug("%s - assigned to processor %d", threading.currentThread().getName(), processorIdAssignedToThisJob)
    except:
      databaseConnection.rollback()
      socorro.lib.util.reportExceptionAndContinue(logger, logging.ERROR, Monitor.ignoreDuplicateDatabaseInsert)
      

  #-----------------------------------------------------------------------------------------------------------------
  def standardJobAllocationLoop(self):
    """
    """
    try:
      self.standardJobAllocationDatabaseConnection = psycopg2.connect(self.config.databaseDSN)
      self.standardJobAllocationCursor = self.standardJobAllocationDatabaseConnection.cursor()
    except:
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a database connection
    try:
      try:
        while (True):
          self.cleanUpCompletedAndFailedJobs(self.standardJobAllocationDatabaseConnection, self.standardJobAllocationCursor)
          self.quitCheck()
          self.cleanUpDeadProcessors(self.standardJobAllocationDatabaseConnection, self.standardJobAllocationCursor)
          self.quitCheck()
          processorIdSequenceGenerator = self.jobSchedulerIter(self.standardJobAllocationCursor)
          # walk the dump tree and assign jobs
          logger.debug("%s - beginning directory tree walk", threading.currentThread().getName())
          try:
            processorIdSequenceGenerator = self.jobSchedulerIter(self.standardJobAllocationCursor)
            for currentDirectory, directoryList, fileList in os.walk(self.config.storageRoot, topdown=False):
              self.quitCheck()
              self.passJudgementOnDirectory(currentDirectory, directoryList, fileList)
              for aFileName in fileList:
                self.quitCheck()
                if aFileName.endswith(self.config.jsonFileSuffix):
                  self.insertionLock.acquire()
                  try:
                    self.queueJob(self.standardJobAllocationDatabaseConnection, self.standardJobAllocationCursor, currentDirectory, aFileName, processorIdSequenceGenerator)
                  finally:
                    self.insertionLock.release()
          except KeyboardInterrupt:
            logger.debug("%s - inner QUITTING", threading.currentThread().getName())
            raise
          except:
            socorro.lib.util.reportExceptionAndContinue(logger)
          self.responsiveSleep(self.config.standardLoopDelay)
      except (KeyboardInterrupt, SystemExit):
        logger.debug("%s - outer QUITTING", threading.currentThread().getName())
        self.standardJobAllocationDatabaseConnection.rollback()
        self.quit = True
        raise
    finally:
      self.standardJobAllocationDatabaseConnection.close()
      logger.debug("%s - standardLoop done.", threading.currentThread().getName())

  #-----------------------------------------------------------------------------------------------------------------
  def getPriorityUuids(self, aCursor):
    aCursor.execute("select * from priorityJobs")
    dictionaryOfPriorityUuids = {}
    for aUuidRow in aCursor.fetchall():
      dictionaryOfPriorityUuids[aUuidRow[0]] = "%s%s" % (aUuidRow[0], self.config.jsonFileSuffix)
    return dictionaryOfPriorityUuids


  #-----------------------------------------------------------------------------------------------------------------
  def priorityJobAllocationLoop(self):
    try:
      self.priorityJobAllocationDatabaseConnection = psycopg2.connect(self.config.databaseDSN)
      self.priorityJobAllocationCursor = self.priorityJobAllocationDatabaseConnection.cursor()
    except:
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a database connection 
    try:
      try:
        while (True):
          self.quitCheck()
          priorityUuids = self.getPriorityUuids(self.priorityJobAllocationCursor)
          if priorityUuids:
            self.insertionLock.acquire()
            try:
              # walk the dump tree and assign jobs
              logger.debug("%s - beginning search for priority jobs", threading.currentThread().getName())
              try:
                processorIdSequenceGenerator = self.jobSchedulerIter(self.priorityJobAllocationCursor)
                #check for uuids already in the queue
                for uuid in priorityUuids.keys():
                  self.quitCheck()
                  self.priorityJobAllocationCursor.execute("select uuid from jobs where uuid = %s", (uuid,))
                  if self.priorityJobAllocationCursor.fetchall():
                    logger.info("%s - priority job %s was already in the queue - raising its priority", threading.currentThread().getName(), uuid)
                    self.priorityJobAllocationCursor.execute("update jobs set priority = priority + 1 where uuid = %s", (uuid,))
                    self.priorityJobAllocationCursor.execute("delete from priorityJobs where uuid = %s", (uuid,))
                    self.priorityJobAllocationDatabaseConnection.commit()
                    del priorityUuids[uuid]
                if priorityUuids: # only need to continue if we still have jobs to process
                  processorIdSequenceGenerator = self.jobSchedulerIter(self.priorityJobAllocationCursor)
                  for currentDirectory, directoryList, fileList in os.walk(self.config.storageRoot, topdown=False):
                    self.quitCheck()
                    for uuid, fileName in ((u, f) for u, f in priorityUuids.items() if f in fileList):
                      logger.info("%s - priority queuing %s", threading.currentThread().getName(), fileName)
                      self.queueJob(self.priorityJobAllocationDatabaseConnection, self.priorityJobAllocationCursor, currentDirectory, fileName, processorIdSequenceGenerator, 1)
                      self.priorityJobAllocationCursor.execute("delete from priorityJobs where uuid = %s", (uuid,))
                      self.priorityJobAllocationDatabaseConnection.commit()
                      del priorityUuids[uuid]
                  if priorityUuids:
                    for uuid in priorityUuids:
                      self.quitCheck()
                      logger.error("%s - priority uuid %s was never found",  threading.currentThread().getName(), uuid)
                      self.priorityJobAllocationCursor.execute("delete from priorityJobs where uuid = %s", (uuid,))
                      self.priorityJobAllocationDatabaseConnection.commit()
              except KeyboardInterrupt:
                logger.debug("%s - inner QUITTING", threading.currentThread().getName())
                raise
              except:
                self.priorityJobAllocationDatabaseConnection.rollback()
                socorro.lib.util.reportExceptionAndContinue(logger)
            finally:
              self.insertionLock.release()
          self.responsiveSleep(self.config.priorityLoopDelay)
      except (KeyboardInterrupt, SystemExit):
        logger.debug("%s - outer QUITTING", threading.currentThread().getName())
        self.priorityJobAllocationDatabaseConnection.rollback()
        self.quit = True
    finally:
      self.priorityJobAllocationDatabaseConnection.close()
      logger.debug("%s - priorityLoop done.", threading.currentThread().getName())

  #-----------------------------------------------------------------------------------------------------------------
  def start (self):
    priorityJobThread = threading.Thread(name="priorityLoopingThread", target=self.priorityJobAllocationLoop)
    priorityJobThread.start()

    try:
      try:
        self.standardJobAllocationLoop()
      finally:
        logger.debug("%s - waiting to join.", threading.currentThread().getName())
        priorityJobThread.join()
    except KeyboardInterrupt:
      raise SystemExit


      
    