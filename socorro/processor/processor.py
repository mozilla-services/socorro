#! /usr/bin/env python

import psycopg2

import time
import datetime
import os
import os.path
import threading
import re
import signal
import sets

import logging

logger = logging.getLogger("processor")

import socorro.database.schema as sch

import socorro.lib.util
import socorro.lib.threadlib
import socorro.lib.ConfigurationManager
import socorro.lib.JsonDumpStorage as jds
import socorro.lib.psycopghelper as psy
import socorro.lib.ooid as ooid

import simplejson

#=================================================================================================================
class UTC(datetime.tzinfo):
  """
  """
  ZERO = datetime.timedelta(0)

  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self):
    super(UTC, self).__init__(self)

  #-----------------------------------------------------------------------------------------------------------------
  def utcoffset(self, dt):
    return UTC.ZERO

  #-----------------------------------------------------------------------------------------------------------------
  def tzname(self, dt):
    return "UTC"

  #-----------------------------------------------------------------------------------------------------------------
  def dst(self, dt):
    return UTC.ZERO

#=================================================================================================================
class DuplicateEntryException(Exception):
  pass

#=================================================================================================================
class ErrorInBreakpadStackwalkException(Exception):
  pass

#=================================================================================================================
class UuidNotFoundException(Exception):
  pass

#=================================================================================================================
class Processor(object):
  """ This class is a mechanism for processing the json and dump file pairs.  It fetches assignments
      from the 'jobs' table in the database and uses a group of threads to process them.

      class member data:
        buildDatePattern: a regular expression that partitions an appropriately formatted string into
            four groups
        utctz: a time zone instance for Universal Time Coordinate
        fixupSpace: a regular expression used to remove spaces before all stars, ampersands, and
            commas
        fixupComma: a regular expression used to ensure a space after commas

      instance member data:
        self.mainThreadDatabaseConnection: the connection to the database used by the main thread
        self.mainThreadCursor: a cursor associated with the main thread's database connection
        self.processorId: each instance of Processor registers itself in the database.  This enables
            the monitor process to assign jobs to specific processors.  This value is the unique
            identifier within the database for an instance of Processor
        self.quit: a boolean used for internal communication between threads.  Since any
            thread may receive the KeyboardInterrupt signal, the receiving thread just has to set this
            variable to True.  All threads periodically check it.  If a thread sees it as True, it abandons
            what it is working on and throws away any subsequent tasks.  The main thread, on seeing
            this value as True, tells all threads to quit, waits for them to do so, unregisters itself in the
            database, closes the database connection and then quits.
        self.getNextJobSQL: a string used as an SQL statement to fetch the next job assignment.
        self.threadManager: an instance of a class that manages the tasks of a set of threads.  It accepts
            new tasks through the call to newTask.  New tasks are placed in the internal task queue.
            Threads pull tasks from the queue as they need them.
        self.databaseConnectionPool: each thread uses its own connection to the database.
            This dictionary, indexed by thread name, is just a repository for the connections that
            persists between jobs.
  """
  buildDatePattern = re.compile('^(\\d{4})(\\d{2})(\\d{2})(\\d{2})')
  fixupSpace = re.compile(r' (?=[\*&,])')
  fixupComma = re.compile(r'(?<=,)(?! )')
  filename_re = re.compile('[/\\\\]([^/\\\\]+)$')
  irrelevantSignaturePattern = re.compile('@0x[01234567890abcdefABCDEF]{2,}')
  prefixSignaturePattern = re.compile('@0x0|strchr|memcpy|malloc|realloc|.*free.*|arena_dalloc_small')
  utctz = UTC()

  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config):
    """
    """
    super(Processor, self).__init__()

    assert "databaseHost" in config, "databaseHost is missing from the configuration"
    assert "databaseName" in config, "databaseName is missing from the configuration"
    assert "databaseUserName" in config, "databaseUserName is missing from the configuration"
    assert "databasePassword" in config, "databasePassword is missing from the configuration"
    assert "storageRoot" in config, "storageRoot is missing from the configuration"
    assert "deferredStorageRoot" in config, "deferredStorageRoot is missing from the configuration"
    assert "jsonFileSuffix" in config, "jsonFileSuffix is missing from the configuration"
    assert "dumpFileSuffix" in config, "dumpFileSuffix is missing from the configuration"
    assert "processorCheckInTime" in config, "processorCheckInTime is missing from the configuration"
    assert "processorCheckInFrequency" in config, "processorCheckInFrequency is missing from the configuration"
    assert "processorId" in config, "processorId is missing from the configuration"
    assert "numberOfThreads" in config, "numberOfThreads is missing from the configuration"
    assert "batchJobLimit" in config, "batchJobLimit is missing from the configuration"

    self.databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)

    self.processorLoopTime = config.processorLoopTime.seconds

    self.config = config
    self.quit = False
    signal.signal(signal.SIGTERM, Processor.respondToSIGTERM)

    self.reportsTable = sch.ReportsTable(logger=logger)
    self.dumpsTable = sch.DumpsTable(logger=logger)
    self.extensionsTable = sch.ExtensionsTable(logger=logger)
    self.framesTable = sch.FramesTable(logger=logger)
    self.reportsTable.setDependents([self.dumpsTable, self.extensionsTable, self.framesTable])

    logger.info("%s - connecting to database", threading.currentThread().getName())
    try:
      databaseConnection, databaseCursor = self.databaseConnectionPool.connectionCursorPair()
    except:
      self.quit = True
      logger.critical("%s - cannot connect to the database", threading.currentThread().getName())
      socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a database connection

    # register self with the processors table in the database
    logger.info("%s - registering with 'processors' table", threading.currentThread().getName())
    try:
      self.processorId = 0
      self.processorName = "%s_%d" % (os.uname()[1], os.getpid())
      if self.config.processorId == 'auto':  # take over for an existing processor
        threshold = psy.singleValueSql(databaseCursor, "select now() - interval '%s'" % self.config.processorCheckInTime)
        try:
          logger.debug("%s - looking for a dead processor", threading.currentThread().getName())
          self.config.processorId = psy.singleValueSql(databaseCursor, "select id from processors where lastSeenDateTime < '%s' limit 1" % threshold)
          logger.info("%s - will step in for processor %d", threading.currentThread().getName(), self.config.processorId)
        except psy.SQLDidNotReturnSingleValue:
          logger.debug("%s - no dead processor found", threading.currentThread().getName())
          self.config.processorId = '0'
      if self.config.processorId != '0':  # take over for a specific existing processor
        try:
          processorId = int(self.config.processorId)
        except ValueError:
          raise socorro.lib.ConfigurationManager.OptionError("%s is not a valid option for processorId" % self.config.processorId)
        try:
          logger.info("%s - stepping in for processor %d", threading.currentThread().getName(), processorId)
          databaseCursor.execute("update processors set name = %s, startDateTime = now(), lastSeenDateTime = now() where id = %s", (self.processorName, processorId))
          databaseCursor.execute("update jobs set starteddatetime = NULL where id in (select id from jobs where starteddatetime is not null and success is null and owner = %s)", (self.config.processorId, ))
          self.processorId = processorId
        except:
          databaseConnection.rollback()
      else:  # be a new processor with a new id
        databaseCursor.execute("insert into processors (name, startDateTime, lastSeenDateTime) values (%s, now(), now())", (self.processorName,))
        self.processorId = psy.singleValueSql(databaseCursor, "select id from processors where name = '%s'" % (self.processorName,))
        logger.info("%s - initializing as processor %d", threading.currentThread().getName(), self.processorId)
      self.priorityJobsTableName = "priority_jobs_%d" % self.processorId
      databaseConnection.commit()
      try:
        databaseCursor.execute("create table %s (uuid varchar(50) not null primary key)" % self.priorityJobsTableName)
        databaseConnection.commit()
      except:
        logger.warning("%s - failed in creating priority jobs table for this processor.  Does it already exist?  This is probably OK",  threading.currentThread().getName())
        databaseConnection.rollback()
        #socorro.lib.util.reportExceptionAndContinue(logger)
    except:
      logger.critical("%s - cannot register with the database", threading.currentThread().getName())
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a registration

    self.lastCheckInTimestamp = datetime.datetime(1950, 1, 1)
    self.getNextJobSQL = "select j.id, j.pathname, j.uuid from jobs j where j.owner = %d and startedDateTime is null order by priority desc, queuedDateTime asc limit 1" % self.processorId

    # start the thread manager with the number of threads specified in the configuration.  The second parameter controls the size
    # of the internal task queue within the thread manager.  It is constrained so that the queue remains starved.  This means that tasks
    # remain queued in the database until the last minute.  This allows some external process to change the priority of a job by changing
    # the 'priority' column of the 'jobs' table for the particular record in the database.  If the threadManager were allowed to suck all
    # the pending jobs from the database, then the job priority could not be changed by an external process.
    logger.info("%s - starting worker threads", threading.currentThread().getName())
    self.threadManager = socorro.lib.threadlib.TaskManager(self.config.numberOfThreads, self.config.numberOfThreads * 2)
    logger.info("%s - I am processor #%d", threading.currentThread().getName(), self.processorId)
    logger.info("%s -   my priority jobs table is called: '%s'", threading.currentThread().getName(), self.priorityJobsTableName)
    self.standardJobStorage = jds.JsonDumpStorage(root=self.config.storageRoot,
                                                  jsonSuffix=self.config.jsonFileSuffix,
                                                  dumpSuffix=self.config.dumpFileSuffix,
                                                  logger=logger)
    self.deferredJobStorage = jds.JsonDumpStorage(root=self.config.deferredStorageRoot,
                                                  jsonSuffix=self.config.jsonFileSuffix,
                                                  dumpSuffix=self.config.dumpFileSuffix,
                                                  logger=logger)

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
  def checkin (self):
    """ a processor must keep its database registration current.  If a processor has not updated its
        record in the database in the interval specified in as self.config.processorCheckInTime, the
        monitor will consider it to be expired.  The monitor will stop assigning jobs to it and reallocate
        its unfinished jobs to other processors.
    """
    if self.lastCheckInTimestamp + self.config.processorCheckInFrequency < datetime.datetime.now():
      logger.debug("%s - updating 'processor' table registration", threading.currentThread().getName())
      databaseConnection, databaseCursor = self.databaseConnectionPool.connectionCursorPairNoTest()
      databaseCursor.execute("update processors set lastSeenDateTime = %s where id = %s", (datetime.datetime.now(), self.processorId))
      databaseConnection.commit()
      self.lastCheckInTimestamp = datetime.datetime.now()

  #-----------------------------------------------------------------------------------------------------------------
  def cleanup(self):
    """ clean up before shutdown
    """
    logger.info("%s - waiting for threads to stop", threading.currentThread().getName())
    self.threadManager.waitForCompletion()
    logger.info("%s - all threads stopped", threading.currentThread().getName())

    databaseConnection, databaseCursor = self.databaseConnectionPool.connectionCursorPairNoTest()

    try:
      # force the processor to record a lastSeenDateTime in the distant past so that the monitor will
      # mark it as dead.  The monitor will process its completed jobs and reallocate it unfinished ones.
      logger.debug("%s - unregistering processor", threading.currentThread().getName())
      databaseCursor.execute("update processors set lastSeenDateTime = '1999-01-01' where id = %s", (self.processorId,))
      databaseConnection.commit()
    except Exception, x:
      logger.critical("%s - could not unregister %d from the database", threading.currentThread().getName(), self.processorId)
      socorro.lib.util.reportExceptionAndContinue(logger)

    try:
      databaseCursor.execute("drop table %s" % self.priorityJobsTableName)
    except psycopg2.Error:
      logger.error("%s - Cannot complete cleanup.  %s may need manual deletion", threading.currentThread().getName(), self.priorityJobsTableName)
      socorro.lib.util.reportExceptionAndContinue(logger)

    # we're done - kill all the threads' database connections
    self.databaseConnectionPool.cleanup()

    logger.debug("%s - done with work", threading.currentThread().getName())


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
  def make_signature(module_name, function, source, source_line, instruction):
    """ returns a structured conglomeration of the input parameters to serve as a signature
    """
    if function is not None:
      # Remove spaces before all stars, ampersands, and commas
      function = re.sub(Processor.fixupSpace, '', function)

      # Ensure a space after commas
      function = re.sub(Processor.fixupComma, ' ', function)
      return function

    if source is not None and source_line is not None:
      filename = filename_re.search(source)
      if filename is not None:
        source = filename.group(1)

      return '%s#%s' % (source, source_line)

    if module_name is not None:
      return '%s@%s' % (module_name, instruction)

    return '@%s' % instruction

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def generateSignatureFromList(signatureList):
    signatureNewSignatureList = []
    prefixFound = False
    for aSignature in signatureList:
      if Processor.irrelevantSignaturePattern.match(aSignature):
        if prefixFound:
          signatureNewSignatureList.append(aSignature)
        continue
      signatureNewSignatureList.append(aSignature)
      if not Processor.prefixSignaturePattern.match(aSignature):
        break
      prefixFound = True
    return ' | '.join(signatureNewSignatureList)

  #-----------------------------------------------------------------------------------------------------------------
  def submitJobToThreads(self, databaseCursor, aJobTuple):
    databaseCursor.execute("update jobs set startedDateTime = %s where id = %s", (datetime.datetime.now(), aJobTuple[0]))
    databaseCursor.connection.commit()
    logger.info("%s - queuing job %d, %s, %s", threading.currentThread().getName(), aJobTuple[0], aJobTuple[2], aJobTuple[1])
    self.threadManager.newTask(self.processJob, aJobTuple)

  #-----------------------------------------------------------------------------------------------------------------
  def jsonPathForUuidInJsonDumpStorage(self, uuid):
    try:
      jsonPath = self.standardJobStorage.getJson(uuid)
    except (OSError, IOError):
      try:
        jsonPath = self.deferredJobStorage.getJson(uuid)
      except (OSError, IOError):
        raise UuidNotFoundException("%s cannot be found in standard or deferred storage" % uuid)
    return jsonPath

  #-----------------------------------------------------------------------------------------------------------------
  def dumpPathForUuidInJsonDumpStorage(self, uuid):
    try:
      dumpPath = self.standardJobStorage.getDump(uuid)
    except (OSError, IOError):
      try:
        dumpPath = self.deferredJobStorage.getDump(uuid)
      except (OSError, IOError):
        raise UuidNotFoundException("%s cannot be found in standard or deferred storage" % uuid)
    return dumpPath

  #-----------------------------------------------------------------------------------------------------------------
  def moveJobFromLegacyToStandardStorage(self, uuid, legacyJsonPathName):
    logger.debug("%s - moveJobFromLegacyToStandardStorage: %s, '%s'", threading.currentThread().getName(), uuid, legacyJsonPathName)
    legacyDumpPathName = "%s%s" % (legacyJsonPathName[:-len(self.config.jsonFileSuffix)], self.config.dumpFileSuffix)
    self.standardJobStorage.copyFrom(uuid, legacyJsonPathName, legacyDumpPathName, "legacy", datetime.datetime.now(), False, True)

  #-----------------------------------------------------------------------------------------------------------------
  def incomingJobStream(self, databaseCursor):
    """
       aJobTuple has this form: (jobId, jobUuid, jobPriority)
    """
    jobList = {}
    preexistingPriorityJobs = set()
    while (True):
      self.quitCheck()
      self.checkin()
      try:
        lastPriorityCheckTimestamp = datetime.datetime.now()
        databaseCursor.execute("select uuid from %s" % self.priorityJobsTableName)
        setOfPriorityJobs = preexistingPriorityJobs | set([x[0] for x in databaseCursor.fetchall()])
        preexistingPriorityJobs = set()
        #logger.debug("%s - priorityJobs: %s", threading.currentThread().getName(), setOfPriorityJobs)
        if setOfPriorityJobs:
          for aPriorityJobUuid in setOfPriorityJobs:
            try:
              aJobTuple = jobList[aPriorityJobUuid]
              del jobList[aPriorityJobUuid]
              databaseCursor.execute("delete from %s where uuid = '%s'" % (self.priorityJobsTableName, aPriorityJobUuid))
              databaseCursor.connection.commit()
              logger.debug("%s - incomingJobStream yielding priority from existing job list: %s", threading.currentThread().getName(), aJobTuple[1])
              yield aJobTuple
            except KeyError:
              try:
                try:
                  aJobTuple = psy.singleRowSql(databaseCursor, "select j.id, j.uuid, j.priority from jobs j where j.uuid = '%s'" % aPriorityJobUuid)
                  #aJobTuple = psy.singleRowSql(databaseCursor, "select j.id, j.uuid, j.priority, j.pathname from jobs j where j.uuid = '%s'" % aPriorityJobUuid)
                  #if aJobTuple[3] is not None and aJobTuple[3] != '':
                    #self.moveJobFromLegacyToStandardStorage(aJobTuple[0], aJobTuple[3])
                  logger.debug("%s - incomingJobStream yielding priority from database: %s", threading.currentThread().getName(), aJobTuple[1])
                finally:
                  databaseCursor.execute("delete from %s where uuid = '%s'" % (self.priorityJobsTableName, aPriorityJobUuid))
                  databaseCursor.connection.commit()
                yield aJobTuple
              except psy.SQLDidNotReturnSingleRow, x:
                logger.warning("%s - the priority job %s was never found", threading.currentThread().getName(), aPriorityJobUuid)
                databaseCursor.execute("delete from %s where uuid = '%s'" % (self.priorityJobsTableName, aPriorityJobUuid))
                databaseCursor.connection.commit()
          continue  # done processing priorities - start the loop again in case there are more priorities
        preexistingPriorityJobs = set()
        if not jobList:
          #databaseCursor.execute("select j.id, j.uuid, j.priority, j.pathname from jobs j where j.owner = %d and j.starteddatetime is null order by j.priority desc limit %d" % (self.processorId, self.config.batchJobLimit))
          databaseCursor.execute("select j.id, j.uuid, j.priority from jobs j where j.owner = %d and j.starteddatetime is null order by j.priority desc limit %d" % (self.processorId, self.config.batchJobLimit))
          for aJobTuple in databaseCursor.fetchall():
            #if aJobTuple[3] is not None and aJobTuple[3] != '':
              #logger.debug("%s - we've got a legacy job: '%s'", threading.currentThread().getName(), aJobTuple[3])
              #self.moveJobFromLegacyToStandardStorage(aJobTuple[0], aJobTuple[3])
            jobList[aJobTuple[1]] = aJobTuple
            if aJobTuple[2]:  #check priority
              logger.debug("%s - adding priority job found in database: %s", threading.currentThread().getName(), aJobTuple[1])
              preexistingPriorityJobs.add(aJobTuple[1])
          if not jobList:
            logger.info("%s - no jobs to do - sleeping %d seconds", threading.currentThread().getName(), self.processorLoopTime)
            self.responsiveSleep(self.processorLoopTime)
        for aJobTuple in jobList.values():
          if lastPriorityCheckTimestamp + self.config.checkForPriorityFrequency < datetime.datetime.now():
            break
          del jobList[aJobTuple[1]]
          logger.debug("%s - incomingJobStream yielding standard from job list: %s", threading.currentThread().getName(), aJobTuple[1])
          yield aJobTuple
      except psycopg2.Error:
        self.quit = True
        logger.critical("%s - fatal database trouble - quitting", threading.currentThread().getName())
        socorro.lib.util.reportExceptionAndAbort()


  #-----------------------------------------------------------------------------------------------------------------
  def start(self):
    """ Run by the main thread, this function fetches jobs from the incoming job stream one at a time
        puts them on the task queue.  If there are no jobs to do, it sleeps before trying again.
        If it detects that some thread has received a Keyboard Interrupt, it stops its looping,
        waits for the threads to stop and then closes all the database connections.
    """
    sqlErrorCounter = 0
    while (True):
      try:
        databaseConnection, databaseCursor = self.databaseConnectionPool.connectionCursorPair()
      except:
        self.quit = True
        socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a database connection
      try:
        #get a job
        for aJobTuple in self.incomingJobStream(databaseCursor):
          self.quitCheck()
          logger.debug("%s - start got: %s", threading.currentThread().getName(), aJobTuple[1])
          self.submitJobToThreads(databaseCursor, aJobTuple)
      except KeyboardInterrupt:
        logger.info("%s - quit request detected", threading.currentThread().getName())
        databaseConnection.rollback()
        self.quit = True
        break
    self.cleanup()

  #-----------------------------------------------------------------------------------------------------------------
  def processJob (self, jobTuple):
    """ This function is run only by a worker thread.
        Given a job, fetch a thread local database connection and the json document.  Use these
        to create the record in the 'reports' table, then start the analysis of the dump file.

        input parameters:
          jobTuple: a tuple containing up to three items: the jobId (the primary key from the jobs table), the
              jobUuid (a unique string with the json file basename minus the extension) and the priority (an integer)
    """
    threadName = threading.currentThread().getName()
    try:
      threadLocalDatabaseConnection, threadLocalCursor = self.databaseConnectionPool.connectionCursorPair()
    except:
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a database connection
    try:
      processorErrorMessages = []
      jobId, jobUuid, jobPriority = jobTuple
      logger.info("%s - starting job: %s, %s", threadName, jobId, jobUuid)
      startedDateTime = datetime.datetime.now()
      threadLocalCursor.execute("update jobs set startedDateTime = %s where id = %s", (startedDateTime, jobId))
      threadLocalDatabaseConnection.commit()

      date_processed = ooid.dateFromOoid(jobUuid)
      jobPathname = self.jsonPathForUuidInJsonDumpStorage(jobUuid)
      dumpfilePathname = self.dumpPathForUuidInJsonDumpStorage(jobUuid)
      jsonFile = open(jobPathname)
      try:
        jsonDocument = simplejson.load(jsonFile)
      finally:
        jsonFile.close()
      reportId = self.insertReportIntoDatabase(threadLocalCursor, jobUuid, jsonDocument, jobPathname, date_processed, processorErrorMessages)
      threadLocalDatabaseConnection.commit()
      truncated = self.doBreakpadStackDumpAnalysis(reportId, jobUuid, dumpfilePathname, threadLocalCursor, date_processed, processorErrorMessages)
      self.quitCheck()
      #finished a job - cleanup
      threadLocalCursor.execute("update jobs set completedDateTime = %s, success = True where id = %s", (datetime.datetime.now(), jobId))
      threadLocalCursor.execute("update reports set started_datetime = timestamp without time zone '%s', completed_datetime = timestamp without time zone '%s', success = True, truncated = %s where id = %s and date_processed = timestamp without time zone '%s'" % (startedDateTime, datetime.datetime.now(), truncated, reportId, date_processed))
      #self.updateRegistrationNoCommit(threadLocalCursor)
      threadLocalDatabaseConnection.commit()
      logger.info("%s - succeeded and committed: %s, %s", threadName, jobId, jobUuid)
    except (KeyboardInterrupt, SystemExit):
      logger.info("%s - quit request detected", threadName)
      self.quit = True
      try:
        logger.info("%s - abandoning job with rollback: %s, %s", threadName, jobId, jobUuid)
        threadLocalDatabaseConnection.rollback()
        threadLocalDatabaseConnection.close()
      except:
        pass
    except DuplicateEntryException, x:
      logger.warning("%s - duplicate entry: %s", threadName, jobUuid)
    except psycopg2.OperationalError:
      logger.critical("%s - something's gone horribly wrong with the database connection", threadName)
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger)
    except Exception, x:
      if type(x) != ErrorInBreakpadStackwalkException:
        socorro.lib.util.reportExceptionAndContinue(logger)
      threadLocalDatabaseConnection.rollback()
      processorErrorMessages.append(str(x))
      message = '\n'.join(processorErrorMessages).replace("'", "''")
      threadLocalCursor.execute("update jobs set completedDateTime = %s, success = False, message = %s where id = %s", (datetime.datetime.now(), message, jobId))
      try:
        threadLocalCursor.execute("update reports set started_datetime = timestamp without time zone '%s', completed_datetime = timestamp without time zone '%s', success = False, processor_notes = '%s' where id = %s and date_processed = timestamp without time zone '%s'" % (startedDateTime, datetime.datetime.now(), message, reportId, date_processed))
      except AttributeError:
        pass
      threadLocalDatabaseConnection.commit()

  #-----------------------------------------------------------------------------------------------------------------
  def insertReportIntoDatabase(self, threadLocalCursor, uuid, jsonDocument, jobPathname, date_processed, processorErrorMessages):
    """ This function is run only by a worker thread.
        Create the record for the current job in the 'reports' table

        input parameters:
          threadLocalCursor: a database cursor for exclusive use by the calling thread
          uuid: the unique id identifying the job - corresponds with the uuid column in the 'jobs'
              and the 'reports' tables
          jsonDocument: an object with a dictionary interface for fetching the components of
              the json document
          jobPathname:  the complete pathname for the json document
          date_processed: when job came in (a key used in partitioning)
          processorErrorMessages: list of strings of error messages
    """
    logger.debug("%s - starting insertReportIntoDatabase", threading.currentThread().getName())
    try:
      product = socorro.lib.util.limitStringOrNone(jsonDocument['ProductName'], 30)
    except KeyError:
      processorErrorMessages.append("ERROR: Json file missing 'ProductName'")
    try:
      version = socorro.lib.util.limitStringOrNone(jsonDocument['Version'], 16)
    except KeyError:
      processorErrorMessages.append("ERROR: Json file missing 'Version'")
    try:
      build = socorro.lib.util.limitStringOrNone(jsonDocument['BuildID'], 30)
    except KeyError:
      processorErrorMessages.append("ERROR: Json file missing 'BuildID'")
    url = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'URL', 255)
    #email = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Email', 100)
    email = None
    user_id = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'UserID',  50)
    user_comments = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Comments', 500)
    app_notes = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Notes', 1000)
    distributor = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Distributor', 20)
    distributor_version = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Distributor_version', 20)
    crash_time = None
    install_age = None
    uptime = 0
    report_date = date_processed
    try:
      crash_time = int(jsonDocument['CrashTime'])
      report_date = datetime.datetime.fromtimestamp(crash_time, Processor.utctz)
      install_age = crash_time - int(jsonDocument['InstallTime'])
      uptime = max(0, crash_time - int(jsonDocument['StartupTime']))
    except (ValueError, KeyError):
      try:
        report_date = datetime.datetime.fromtimestamp(jsonDocument['timestamp'], Processor.utctz)
      except (ValueError, KeyError):
        logger.warning("%s - no 'report_date' calculated in %s", threading.currentThread().getName(), jobPathname)
        socorro.lib.util.reportExceptionAndContinue(logger, logging.WARNING)
        processorErrorMessages.append("WARNING: No 'client_report_date' could be determined from the Json file")
    build_date = None
    try:
      build_date = datetime.datetime(*[int(x) for x in Processor.buildDatePattern.match(str(jsonDocument['BuildID'])).groups()])
    except (AttributeError, ValueError, KeyError):
        logger.warning("%s - no 'build_date' calculated in %s", threading.currentThread().getName(), jobPathname)
        processorErrorMessages.append("WARNING: No 'build_date' could be determined from the Json file")
        socorro.lib.util.reportExceptionAndContinue(logger, logging.WARNING)
    try:
      last_crash = int(jsonDocument['SecondsSinceLastCrash'])
    except:
      last_crash = None
    newReportsRowTuple = (uuid, report_date, date_processed, product, version, build, url, install_age, last_crash, uptime, email, build_date, user_id, user_comments, distributor, distributor_version)
    try:
      logger.debug("%s - inserting for %s", threading.currentThread().getName(), uuid)
      self.reportsTable.insert(threadLocalCursor, newReportsRowTuple, self.databaseConnectionPool.connectToDatabase, date_processed=date_processed)
    except psycopg2.IntegrityError:
      logger.debug("%s - %s: this report already exists",  threading.currentThread().getName(), uuid)
      threadLocalCursor.connection.rollback()
      previousTrialWasSuccessful = psy.singleValueSql(threadLocalCursor, "select success from reports where uuid = '%s' and date_processed = timestamp without time zone '%s'" % (uuid, date_processed))
      if previousTrialWasSuccessful:
        raise DuplicateEntryException(uuid)
      threadLocalCursor.execute("delete from reports where uuid = '%s' and date_processed = timestamp without time zone '%s'" % (uuid, date_processed))
      processorErrorMessages.append("INFO: This record is a replacement for a previous record with the same uuid")
      self.reportsTable.insert(threadLocalCursor, newReportsRowTuple)
    reportId = psy.singleValueSql(threadLocalCursor, "select id from reports where uuid = '%s' and date_processed = timestamp without time zone '%s'" % (uuid, date_processed))
    return reportId

  #-----------------------------------------------------------------------------------------------------------------
  def doBreakpadStackDumpAnalysis (self, reportId, uuid, dumpfilePathname, databaseCursor, date_processed, processorErrorMessages):
    """ This function is run only by a worker thread.
        This function must be overriden in a subclass - this method will invoke the breakpad_stackwalk process
        (if necessary) and then do the anaylsis of the output
    """
    raise Exception("No breakpad_stackwalk invocation method specified")


