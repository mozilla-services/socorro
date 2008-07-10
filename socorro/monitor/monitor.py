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

import logging

logger = logging.getLogger("monitor")

import socorro.lib.util
import socorro.lib.filesystem



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
        logger.info("%s - found dead processor(s)", threading.currentThread().getName())
        aCursor.execute("select id from processors where lastSeenDateTime >= '%s'" % threshold)
        liveProcessors = aCursor.fetchall()
        if not liveProcessors:
          raise Monitor.NoProcessorsRegisteredException("There are no processors registered")
        def liveProcessorGenerator():
          while True:
            for aRow in liveProcessors:
              yield aRow[0]
        aCursor.execute("select id from jobs where owner in (select id from processors where lastSeenDateTime < '%s')" % threshold)
        rowCounter = 1
        for jobIdTuple, newProcessorId in zip(aCursor.fetchall(), liveProcessorGenerator()):
          logger.info("%s - reassignment: job %d to processor %d", threading.currentThread().getName(), jobIdTuple[0], newProcessorId)
          aCursor.execute("update jobs set owner = %s where id = %s", (newProcessorId, jobIdTuple[0]))
          rowCounter += 1
          if rowCounter % 1000:
            databaseConnection.commit()
        logger.info("%s - removing all dead processors", threading.currentThread().getName())
        aCursor.execute("delete from processors where lastSeenDateTime < '%s'" % threshold)
        databaseConnection.commit()
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
  @staticmethod
  def secondOfSequence(x):
    return x[1]

  #-----------------------------------------------------------------------------------------------------------------
  def jobSchedulerIter(self, aCursor):
    """ This takes a snap shot of the state of the processors as well as the number of jobs assigned to each
        then acts as an iterator that returns a sequence of processor ids.  Order of ids returned will assure that
        jobs are assigned in a balanced manner
    """
    logger.debug("%s - compiling list of active processors", threading.currentThread().getName())
    try:
      sql = """select p.id, count(j.*) from processors p left join jobs j on p.id = j.owner group by p.id"""
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
  def directoryJudgedDeletable (self, pathname, subDirectoryList, fileList):
    if not (subDirectoryList or fileList) and pathname != self.config.storageRoot: #if both directoryList and fileList are empty
      #select an ageLimit from two options based on the if target directory name has a prefix of "dumpDirPrefix"
      ageLimit = (self.config.dateDirDelta, self.config.dumpDirDelta)[os.path.basename(pathname).startswith(self.config.dumpDirPrefix)]
      logger.debug("%s - agelimit: %s dir age: %s", threading.currentThread().getName(), ageLimit, (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(os.path.getmtime(pathname))))
      return (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(os.path.getmtime(pathname))) > ageLimit
    return False

  #-----------------------------------------------------------------------------------------------------------------
  def passJudgementOnDirectory(self, currentDirectory, subDirectoryList, fileList):
    #logger.debug("%s - %s", threading.currentThread().getName(), currentDirectory)
    try:
      if self.directoryJudgedDeletable(currentDirectory, subDirectoryList, fileList):
        logger.debug("%s - removing - %s", threading.currentThread().getName(),  currentDirectory)
        os.rmdir(currentDirectory)
      else:
        logger.debug("%s - not eligible for deletion - %s", threading.currentThread().getName(),  currentDirectory)
    except Exception:
      socorro.lib.util.reportExceptionAndContinue(logger)

  #-----------------------------------------------------------------------------------------------------------------
  def queueJob (self, databaseConnection, databaseCursor, currentDirectory, aFileName, symLinkPathname, processorIdSequenceGenerator, priority=0):
    logger.debug("%s - priority %d queuing %s", threading.currentThread().getName(), priority, aFileName)
    try:
      jsonFilePathName = os.path.join(currentDirectory, aFileName)
      uuid = aFileName[:-len(self.config.jsonFileSuffix)]
      logger.debug("%s - trying to insert %s", threading.currentThread().getName(), uuid)
      processorIdAssignedToThisJob = processorIdSequenceGenerator.next()
      databaseCursor.execute("insert into jobs (pathname, uuid, owner, priority, queuedDateTime) values (%s, %s, %s, %s, %s)",
                                 (jsonFilePathName, uuid, processorIdAssignedToThisJob, priority, datetime.datetime.now()))
      databaseConnection.commit()
      os.unlink(symLinkPathname)
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
    mostRecentFileSystemDatePath = self.config.fileSystemDateThreshold
    mostRecentFileSystemDatePathMagnitude = Monitor.calculateDatePathMagnitude(mostRecentFileSystemDatePath)
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
            for symLinkCurrentDirectory, symLinkName, symLinkPathname in socorro.lib.filesystem.findFileGenerator(os.path.join(self.config.storageRoot, "index"), acceptanceFunction=self.isSymLinkOfProperAge):
              logger.debug("%s - found symbolic link: %s", threading.currentThread().getName(), symLinkPathname)
              pathname = os.readlink(symLinkPathname)
              currentDirectory, filename = os.path.split(pathname)
              currentDirectory = os.path.join(self.config.storageRoot, currentDirectory[6:]) # convert relative path to absolute
              logger.debug("%s - walking - found: %s referring to: %s/%s", threading.currentThread().getName(), symLinkPathname, currentDirectory, filename)
              self.quitCheck()
              self.insertionLock.acquire()
              try:
                self.queueJob(self.standardJobAllocationDatabaseConnection, self.standardJobAllocationCursor, currentDirectory, filename, symLinkPathname, processorIdSequenceGenerator)
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
  @staticmethod
  def calculateDatePathMagnitude (path):
    """returns a list of all the directory names that consist entirely of digits converted to integers.
    """
    splitPath = path.split('/')
    magnitudeList = []
    for x in splitPath:
      try:
        magnitudeList.append(int(x))
      except ValueError:
        pass
    return magnitudeList


  #-----------------------------------------------------------------------------------------------------------------
  def isSymLinkOfProperAge(self, testPath):
    #logger.debug("%s - %s", threading.currentThread().getName(), testPath)
    #logger.debug("%s - %s", threading.currentThread().getName(), testPath[1].endswith(".symlink"))
    #logger.debug("%s - %s", threading.currentThread().getName(), (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(os.path.getmtime(testPath[2]))) > self.config.minimumSymlinkAge)
    return testPath[1].endswith(".symlink") and (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(os.path.getmtime(testPath[2]))) > self.config.minimumSymlinkAge

  #-----------------------------------------------------------------------------------------------------------------
  def priorityJobAllocationLoop(self):
    try:
      self.priorityJobAllocationDatabaseConnection = psycopg2.connect(self.config.databaseDSN)
      self.priorityJobAllocationCursor = self.priorityJobAllocationDatabaseConnection.cursor()
    except:
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a database connection
    symLinkIndexPath = os.path.join(self.config.storageRoot, "index")
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
                  for uuid in priorityUuids.keys():
                    logger.debug("%s - looking for %s", threading.currentThread().getName(), uuid)
                    for currentDirectory in dircache.listdir(symLinkIndexPath):
                      self.quitCheck()
                      absoluteSymLinkPathname = os.path.join(self.config.storageRoot, "index", currentDirectory, "%s.symlink" % uuid)
                      logger.debug("%s -         as %s", threading.currentThread().getName(), absoluteSymLinkPathname)
                      try:
                        pathname = os.readlink(absoluteSymLinkPathname)
                        logger.debug("%s -         FOUND", threading.currentThread().getName())
                        currentDirectory, filename = os.path.split(pathname)
                        currentDirectory = os.path.join(self.config.storageRoot, currentDirectory[5:]) # convert relative path to absolute
                      except OSError:
                        logger.debug("%s -         Not it...", threading.currentThread().getName())
                        continue
                      logger.info("%s - priority queuing %s", threading.currentThread().getName(), filename)
                      self.queueJob(self.priorityJobAllocationDatabaseConnection, self.priorityJobAllocationCursor, currentDirectory, filename, absoluteSymLinkPathname, processorIdSequenceGenerator, 1)
                      self.priorityJobAllocationCursor.execute("delete from priorityJobs where uuid = %s", (uuid,))
                      self.priorityJobAllocationDatabaseConnection.commit()
                      del priorityUuids[uuid]
                      break
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
              logger.debug("%s - releasing lock", threading.currentThread().getName())
              self.insertionLock.release()
          logger.debug("%s - sleeping", threading.currentThread().getName())
          self.responsiveSleep(self.config.priorityLoopDelay)
      except (KeyboardInterrupt, SystemExit):
        logger.debug("%s - outer QUITTING", threading.currentThread().getName())
        self.priorityJobAllocationDatabaseConnection.rollback()
        self.quit = True
    finally:
      self.priorityJobAllocationDatabaseConnection.close()
      logger.debug("%s - priorityLoop done.", threading.currentThread().getName())

  #-----------------------------------------------------------------------------------------------------------------
  def oldDirectoryCleanupLoop (self):
    logger.info("%s - oldDirectoryCleanupLoop starting.", threading.currentThread().getName())
    try:
      try:
        while True:
          logger.info("%s - beginning oldDirectoryCleanupLoop cycle.", threading.currentThread().getName())
          # walk entire tree looking for directories in need of deletion because they're old and empty
          for currentDirectory, directoryList, fileList in os.walk(self.config.storageRoot, topdown=False):
            self.quitCheck()
            self.passJudgementOnDirectory(currentDirectory, directoryList, fileList)
          self.responsiveSleep(self.config.cleanupLoopDelay)
      except (KeyboardInterrupt, SystemExit):
        logger.debug("%s - got quit message", threading.currentThread().getName())
        self.quit = True
      except:
        socorro.lib.util.reportExceptionAndContinue(logger)
    finally:
      logger.info("%s - oldDirectoryCleanupLoop done.", threading.currentThread().getName())



  #-----------------------------------------------------------------------------------------------------------------
  def start (self):
    priorityJobThread = threading.Thread(name="priorityLoopingThread", target=self.priorityJobAllocationLoop)
    priorityJobThread.start()
    directoryCleanupThread = threading.Thread(name="directoryCleanupThread", target=self.oldDirectoryCleanupLoop)
    directoryCleanupThread.start()

    try:
      try:
        self.standardJobAllocationLoop()
      finally:
        logger.debug("%s - waiting to join.", threading.currentThread().getName())
        priorityJobThread.join()
        directoryCleanupThread.join()
    except KeyboardInterrupt:
      raise SystemExit



