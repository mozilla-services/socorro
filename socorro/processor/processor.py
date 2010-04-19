import psycopg2

import datetime
from operator import itemgetter
import logging
import os
import os.path
import re
import signal
import sets
import threading
import time

logger = logging.getLogger("processor")

import socorro.database.schema as sch

import socorro.lib.util
import socorro.lib.threadlib
import socorro.lib.ConfigurationManager
import socorro.lib.JsonDumpStorage as jds
import socorro.lib.psycopghelper as psy
import socorro.lib.ooid as ooid
import socorro.lib.datetimeutil as sdt
import socorro.lib.processedDumpStorage as pds

import simplejson

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
        self.threadManager: an instance of a class that manages the tasks of a set of threads.  It accepts
            new tasks through the call to newTask.  New tasks are placed in the internal task queue.
            Threads pull tasks from the queue as they need them.
        self.databaseConnectionPool: each thread uses its own connection to the database.
            This dictionary, indexed by thread name, is just a repository for the connections that
            persists between jobs.
  """
  #-----------------------------------------------------------------------------------------------------------------
  # static data. Beware threading!
  buildDatePattern = re.compile('^(\\d{4})(\\d{2})(\\d{2})(\\d{2})')
  utctz = sdt.UTC()

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
    assert "processedDumpStoragePath" in config, "processedDumpStoragePath is missing from the configuration"
    assert "jsonFileSuffix" in config, "jsonFileSuffix is missing from the configuration"
    assert "dumpFileSuffix" in config, "dumpFileSuffix is missing from the configuration"
    assert "processorCheckInTime" in config, "processorCheckInTime is missing from the configuration"
    assert "processorCheckInFrequency" in config, "processorCheckInFrequency is missing from the configuration"
    assert "processorId" in config, "processorId is missing from the configuration"
    assert "numberOfThreads" in config, "numberOfThreads is missing from the configuration"
    assert "batchJobLimit" in config, "batchJobLimit is missing from the configuration"
    assert "irrelevantSignatureRegEx" in config, "irrelevantSignatureRegEx is missing from the configuration"
    assert "prefixSignatureRegEx" in config, "prefixSignatureRegEx is missing from the configuration"
    assert "collectAddon" in config, "collectAddon is missing from the configuration"
    assert "collectCrashProcess" in config, "collectCrashProcess is missing from the configuration"
    assert "signatureSentinels" in config, "signatureSentinels is missing from the configuration"
    assert "signaturesWithLineNumbersRegEx" in config, "signaturesWithLineNumbersRegEx is missing from the configuration"
    assert "dumpPermissions" in config, "dumpPermissions is missing from the configuration"
    assert "dirPermissions" in config, "dirPermissions is missing from the configuration"
    assert "dumpGID" in config, "dumpGID is missing from the configuration"

    self.databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)

    self.processorLoopTime = config.processorLoopTime.seconds

    self.config = config
    self.quit = False
    signal.signal(signal.SIGTERM, Processor.respondToSIGTERM)
    signal.signal(signal.SIGHUP, Processor.respondToSIGTERM)

    self.irrelevantSignatureRegEx = re.compile(self.config.irrelevantSignatureRegEx)
    self.prefixSignatureRegEx = re.compile(self.config.prefixSignatureRegEx)
    self.signaturesWithLineNumbersRegEx = re.compile(self.config.signaturesWithLineNumbersRegEx)

    self.processedDumpStorage = pds.ProcessedDumpStorage(root=config.processedDumpStoragePath,
                                                         dumpPermissions=config.dumpPermissions,
                                                         dirPermissions=config.dirPermissions,
                                                         dumpGID=config.dumpGID,
                                                         logger=logger)

    self.reportsTable = sch.ReportsTable(logger=logger)
    self.extensionsTable = sch.ExtensionsTable(logger=logger)
    self.framesTable = sch.FramesTable(logger=logger)
    self.pluginsTable = sch.PluginsTable(logger=logger)
    self.pluginsReportsTable = sch.PluginsReportsTable(logger=logger)

    logger.info("%s - connecting to database", threading.currentThread().getName())
    try:
      databaseConnection, databaseCursor = self.databaseConnectionPool.connectionCursorPair()
    except:
      self.quit = True
      logger.critical("%s - cannot connect to the database", threading.currentThread().getName())
      socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a database connection

    # register self with the processors table in the database
    # Must request 'auto' id, or an id number that is in the processors table AND not alive
    logger.info("%s - registering with 'processors' table", threading.currentThread().getName())
    priorityCreateRuberic = "Since we took over, it probably exists."
    self.processorId = None
    legalOption = False
    try:
      requestedId = 0
      try:
        requestedId = int(self.config.processorId)
      except ValueError:
        if 'auto' == self.config.processorId:
          requestedId = 'auto'
        else:
          raise socorro.lib.ConfigurationManager.OptionError("%s is not a valid option for processorId" % self.config.processorId)
      self.processorName = "%s_%d" % (os.uname()[1], os.getpid())
      threshold = psy.singleValueSql(databaseCursor, "select now() - interval '%s'" % self.config.processorCheckInTime)
      if requestedId == 'auto':  # take over for an existing processor
        logger.debug("%s - looking for a dead processor", threading.currentThread().getName())
        try:
          self.processorId = psy.singleValueSql(databaseCursor, "select id from processors where lastseendatetime < '%s' limit 1" % threshold)
          logger.info("%s - will step in for processor %d", threading.currentThread().getName(), self.processorId)
        except psy.SQLDidNotReturnSingleValue:
          logger.debug("%s - no dead processor found", threading.currentThread().getName())
          requestedId = 0 # signal that we found no dead processors
      else: # requestedId is an integer: We already raised OptionError if not
        try:
          # singleValueSql should actually accept sql with placeholders and an array of values instead of just a string. Enhancement needed...
          checkSql = "select id from processors where lastSeenDateTime < '%s' and id = %s" % (threshold,requestedId)
          self.processorId = psy.singleValueSql(databaseCursor, checkSql)
          logger.info("%s - stepping in for processor %d", threading.currentThread().getName(), self.processorId)
        except psy.SQLDidNotReturnSingleValue,x:
          raise socorro.lib.ConfigurationManager.OptionError("ProcessorId %s is not in processors table or is still live."%requestedId)
      if requestedId == 0:
        try:
          databaseCursor.execute("insert into processors (name, startdatetime, lastseendatetime) values (%s, now(), now())", (self.processorName,))
          self.processorId = psy.singleValueSql(databaseCursor, "select id from processors where name = '%s'" % (self.processorName,))
        except:
          databaseConnection.rollback()
          raise
        logger.info("%s - initializing as processor %d", threading.currentThread().getName(), self.processorId)
        priorityCreateRuberic = "Does it already exist?"
        # We have a good processorId and a name. Register self with database
      try:
        databaseCursor.execute("update processors set name = %s, startdatetime = now(), lastseendatetime = now() where id = %s", (self.processorName, self.processorId))
        databaseCursor.execute("update jobs set starteddatetime = NULL where id in (select id from jobs where starteddatetime is not null and success is null and owner = %s)", (self.processorId, ))
      except Exception,x:
        logger.critical("Constructor: Unable to update processors or jobs table: %s: %s",type(x),x)
        databaseConnection.rollback()
        raise
    except:
      logger.critical("%s - cannot register with the database", threading.currentThread().getName())
      databaseConnection.rollback()
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a registration
    # We managed to get registered. Make sure we have our own priority_jobs table
    self.priorityJobsTableName = "priority_jobs_%d" % self.processorId
    try:
      databaseCursor.execute("create table %s (uuid varchar(50) not null primary key)" % self.priorityJobsTableName)
      databaseConnection.commit()
    except:
      logger.warning("%s - failed to create table %s. %s This is probably OK",  threading.currentThread().getName(),self.priorityJobsTableName,priorityCreateRuberic)
      databaseConnection.rollback()
    # force checkin to run immediately after start(). I don't understand the need, since the database already reflects nearly-real reality. Oh well.
    self.lastCheckInTimestamp = datetime.datetime(1950, 1, 1)
    #self.getNextJobSQL = "select j.id, j.pathname, j.uuid from jobs j where j.owner = %d and startedDateTime is null order by priority desc, queuedDateTime asc limit 1" % self.processorId

    # start the thread manager with the number of threads specified in the configuration.  The second parameter controls the size
    # of the internal task queue within the thread manager.  It is constrained so that the queue remains starved.  This means that tasks
    # remain queued in the database until the last minute.  This allows some external process to change the priority of a job by changing
    # the 'priority' column of the 'jobs' table for the particular record in the database.  If the threadManager were allowed to suck all
    # the pending jobs from the database, then the job priority could not be changed by an external process.
    logger.info("%s - starting worker threads", threading.currentThread().getName())
    self.threadManager = socorro.lib.threadlib.TaskManager(self.config.numberOfThreads, self.config.numberOfThreads * 2)
    logger.info("%s - I am processor #%d", threading.currentThread().getName(), self.processorId)
    logger.info("%s - my priority jobs table is called: '%s'", threading.currentThread().getName(), self.priorityJobsTableName)
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
      tstamp = datetime.datetime.now()
      databaseConnection, databaseCursor = self.databaseConnectionPool.connectionCursorPairNoTest()
      databaseCursor.execute("update processors set lastseendatetime = %s where id = %s", (tstamp, self.processorId))
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
      databaseCursor.execute("update processors set lastseendatetime = '1999-01-01' where id = %s", (self.processorId,))
      databaseConnection.commit()
    except Exception, x:
      logger.critical("%s - could not unregister %d from the database", threading.currentThread().getName(), self.processorId)
      databaseConnection.rollback()
      socorro.lib.util.reportExceptionAndContinue(logger)
    try:
      databaseCursor.execute("drop table %s" % self.priorityJobsTableName)
      databaseConnection.commit()
    except psycopg2.Error:
      logger.error("%s - Cannot complete cleanup.  %s may need manual deletion", threading.currentThread().getName(), self.priorityJobsTableName)
      databaseConnection.rollback()
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
    signame = 'SIGTERM'
    if signalNumber != signal.SIGTERM: signame = 'SIGHUP'
    logger.info("%s - %s detected", threading.currentThread().getName(),signame)
    raise KeyboardInterrupt

  #--- put these near where they are needed to avoid scrolling during maintenance ----------------------------------
  fixupSpace = re.compile(r' (?=[\*&,])')
  fixupComma = re.compile(r',(?! )')
  fixupInteger = re.compile(r'(<|, )(\d+)([uUlL]?)([^\w])')
  #-----------------------------------------------------------------------------------------------------------------
  def make_signature(self, module_name, function, source, source_line, instruction):
    """ returns a structured conglomeration of the input parameters to serve as a signature
    """
    if function is not None:
      if self.signaturesWithLineNumbersRegEx.match(function):
        function = "%s:%s" % (function, source_line)

      # Remove spaces before all stars, ampersands, and commas
      function = Processor.fixupSpace.sub('',function)

      # Ensure a space after commas
      function = Processor.fixupComma.sub(', ', function)

      # normalize template signatures with manifest const integers to 'int': Bug 481445
      function = Processor.fixupInteger.sub(r'\1int\4', function)

      return function

    if source is not None and source_line is not None:
      filename = source.rstrip('/\\')
      if '\\' in filename:
        source = filename.rsplit('\\')[-1]
      else:
        source = filename.rsplit('/')[-1]
      return '%s#%s' % (source, source_line)

    if not module_name: module_name = '' # might have been None
    return '%s@%s' % (module_name, instruction)

  #-----------------------------------------------------------------------------------------------------------------
  def generateSignatureFromList(self, signatureList):
    """
    each element of signatureList names a frame in the crash stack; and is:
      - a prefix of a relevant frame: Append this element to the signature
      - a relevant frame: Append this element and stop looking
      - irrelevant: Append this element only after we have seen a prefix frame
    The signature is a ' | ' separated string of frame names
    Although the database holds only 255 characters, we don't truncate here
    """
    # shorten signatureList to the first signatureSentinel
    sentinelLocations = []
    for aSentinel in self.config.signatureSentinels:
      try:
        sentinelLocations.append(signatureList.index(aSentinel))
      except ValueError:
        pass
    if sentinelLocations:
      signatureList = signatureList[min(sentinelLocations):]

    newSignatureList = []
    prefixFound = False
    for aSignature in signatureList:
      if self.irrelevantSignatureRegEx.match(aSignature):
        if prefixFound:
          newSignatureList.append(aSignature)
        continue
      newSignatureList.append(aSignature)
      if not self.prefixSignatureRegEx.match(aSignature):
        break
      prefixFound = True
    return ' | '.join(newSignatureList)

  #-----------------------------------------------------------------------------------------------------------------
  def submitJobToThreads(self, databaseCursor, aJobTuple):
    databaseCursor.execute("update jobs set starteddatetime = %s where id = %s", (datetime.datetime.now(), aJobTuple[0]))
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
  def newPriorityJobsIter (self, databaseCursor):
    """
    Yields a list of JobTuples pulled from the 'jobs' table for all the jobs found in this process' priority jobs table.
    If there are no priority jobs, yields None.
    This iterator is perpetual - it never raises the StopIteration exception
    """
    deleteOnePriorityJobSql = "delete from %s where uuid = %%s" % self.priorityJobsTableName
    fullJobsList = []
    while True:
      if not fullJobsList:
        databaseCursor.execute("""select
                                      j.id,
                                      pj.uuid,
                                      1,
                                      j.starteddatetime
                                  from
                                      jobs j right join %s pj on j.uuid = pj.uuid""" % self.priorityJobsTableName)
        fullJobsList = databaseCursor.fetchall()
        databaseCursor.connection.commit()           # LEAVE THIS LINE: As of 2009-February, it prevents psycopg2 issues
      if fullJobsList:
        while fullJobsList:
          aFullJobTuple = fullJobsList.pop(-1)
          databaseCursor.execute(deleteOnePriorityJobSql, (aFullJobTuple[1],)) #entry should be deleted even if it is not found
          databaseCursor.connection.commit()
          if aFullJobTuple[0] is not None:
            if aFullJobTuple[3]:
              continue
            else:
              yield (aFullJobTuple[0],aFullJobTuple[1],aFullJobTuple[2],)
          else:
            logger.debug("%s - the priority job %s was never found", threading.currentThread().getName(), aFullJobTuple[1])
      else:
        yield None

  #-----------------------------------------------------------------------------------------------------------------
  def newNormalJobsIter (self, databaseCursor):
    """
    Yields a list of job tuples pulled from the 'jobs' table for which the owner is this process and the
    started datetime is null.
    This iterator is perpetual - it never raises the StopIteration exception
    """
    normalJobsList = []
    while True:
      if not normalJobsList:
        databaseCursor.execute("""select
                                      j.id,
                                      j.uuid,
                                      priority
                                  from
                                      jobs j
                                  where
                                      j.owner = %d
                                      and j.starteddatetime is null
                                  order by queueddatetime
                                  limit %d""" % (self.processorId, self.config.batchJobLimit))
        normalJobsList = databaseCursor.fetchall()
        databaseCursor.connection.commit()
      if normalJobsList:
        while normalJobsList:
          yield normalJobsList.pop(-1)
      else:
        yield None

  #-----------------------------------------------------------------------------------------------------------------
  def incomingJobStream(self, databaseCursor):
    """
       aJobTuple has this form: (jobId, jobUuid, jobPriority) ... of which jobPriority is pure excess, and should someday go away
       Yields the next job according to this pattern:
       START
       Attempt to yield a priority job
       If no priority job, attempt to yield a normal job
       If no priority or normal job, sleep self.processorLoopTime seconds
       loop back to START
    """
    priorityJobIter = self.newPriorityJobsIter(databaseCursor)
    normalJobIter = self.newNormalJobsIter(databaseCursor)
    seenUuids = set()
    while (True):
      aJobType = 'priority'
      self.quitCheck()
      self.checkin()
      aJobTuple = priorityJobIter.next()
      if not aJobTuple:
        aJobTuple = normalJobIter.next()
        aJobType = 'standard'
      if aJobTuple:
        if not aJobTuple[1] in seenUuids:
          seenUuids.add(aJobTuple[1])
          logger.debug("%s - incomingJobStream yielding %s job %s",threading.currentThread().getName(), aJobType, aJobTuple)
          yield aJobTuple
        else:
          logger.debug("Skipping already seen job %s",aJobTuple)
      else:
        logger.info("%s - no jobs to do - sleeping %d seconds", threading.currentThread().getName(), self.processorLoopTime)
        seenUuids = set()
        self.responsiveSleep(self.processorLoopTime)

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
  @staticmethod
  def convertDatesInDictToString (aDict):
    for name, value in aDict.iteritems():
      if type(value) == datetime.datetime:
        aDict[name] = "%4d-%02d-%02d %02d:%02d:%02d.%d" % (value.year, value.month, value.day, value.hour, value.minute, value.second, value.microsecond)

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def sanitizeDict (aDict, listOfForbiddenKeys=['url','email','user_id']):
    for aForbiddenKey in listOfForbiddenKeys:
      if aForbiddenKey in aDict:
        del aDict[aForbiddenKey]

  #-----------------------------------------------------------------------------------------------------------------
  def saveProcessedDumpJson (self, aReportRecordAsDict):
    date_processed = aReportRecordAsDict["date_processed"]
    Processor.sanitizeDict(aReportRecordAsDict)
    Processor.convertDatesInDictToString(aReportRecordAsDict)
    uuid = aReportRecordAsDict["uuid"]
    try:
      self.processedDumpStorage.putDumpToFile(uuid, aReportRecordAsDict, date_processed)
    except OSError, x:
      if x.errno == 17:
        self.processedDumpStorage.removeDumpFile(uuid)
        self.processedDumpStorage.putDumpToFile(uuid, aReportRecordAsDict, date_processed)
      else:
        raise

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
      newReportRecordAsDict = {}
      processorErrorMessages = []
      jobId, jobUuid, jobPriority = jobTuple
      logger.info("%s - starting job: %s, %s", threadName, jobId, jobUuid)
      startedDateTime = datetime.datetime.now()
      threadLocalCursor.execute("update jobs set starteddatetime = %s where id = %s", (startedDateTime, jobId))
      threadLocalDatabaseConnection.commit()

      jobPathname = self.jsonPathForUuidInJsonDumpStorage(jobUuid)
      dumpfilePathname = self.dumpPathForUuidInJsonDumpStorage(jobUuid)
      jsonFile = open(jobPathname)
      try:
        jsonDocument = simplejson.load(jsonFile)
      finally:
        jsonFile.close()

      try:
        date_processed = sdt.datetimeFromISOdateString(jsonDocument["submitted_timestamp"])
      except KeyError:
        date_processed = ooid.dateFromOoid(jobUuid)

      newReportRecordAsDict = self.insertReportIntoDatabase(threadLocalCursor, jobUuid, jsonDocument, jobPathname, date_processed, processorErrorMessages)
      threadLocalDatabaseConnection.commit()
      reportId = newReportRecordAsDict["id"]
      newReportRecordAsDict['dump'] = ''
      newReportRecordAsDict["startedDateTime"] = startedDateTime

      if self.config.collectAddon:
        logger.info("%s - collecting Addons", threadName)
        addonsAsAListOfTuples = self.insertAdddonsIntoDatabase(threadLocalCursor, reportId, jsonDocument, date_processed, processorErrorMessages)
        newReportRecordAsDict["addons"] = addonsAsAListOfTuples

      if self.config.collectCrashProcess:
        logger.info("%s - collecting Crash Process", threadName)
        crashProcessAsDict = self.insertCrashProcess(threadLocalCursor, reportId, jsonDocument, date_processed, processorErrorMessages)
        newReportRecordAsDict.update( crashProcessAsDict )

      try:
        additionalReportValuesAsDict = self.doBreakpadStackDumpAnalysis(reportId, jobUuid, dumpfilePathname, threadLocalCursor, date_processed, processorErrorMessages)
        newReportRecordAsDict.update(additionalReportValuesAsDict)
      finally:
        newReportRecordAsDict["completeddatetime"] = completedDateTime = datetime.datetime.now()

      #finished a job - cleanup
      threadLocalCursor.execute("update jobs set completeddatetime = %s, success = True where id = %s", (completedDateTime, jobId))
      # Bug 519703: Collect setting for topmost source filename(s), addon compatibility check override, flash version
      reportsSql = """
      update reports set
        started_datetime = timestamp without time zone %%s,
        completed_datetime = timestamp without time zone %%s,
        success = True,
        truncated = %%s,
        topmost_filenames = %%s,
        addons_checked = %%s,
        flash_version = %%s
      where id = %s and date_processed = timestamp without time zone '%s'
      """ % (reportId,date_processed)
      #logger.debug("%s - newReportRecordAsDict %s, %s",threadName, newReportRecordAsDict['topmost_filenames'], newReportRecordAsDict['flash_version'])
      #topmost_filenames = "|".join(jsonDocument.get('topmost_filenames',[]))
      topmost_filenames = "|".join(newReportRecordAsDict.get('topmost_filenames',[]))
      addons_checked = None
      try:
        ac = jsonDocument['EMCheckCompatibility']
        #ac = newReportRecordAsDict['EMCheckCompatibility']
        #addons_checked = False
        if ac and not  'false' == ("%s"%ac).lower():
          addons_checked = True
      except:
        pass # leaving it as None if not in the document
      #flash_version = jsonDocument.get('flash_version')
      flash_version = newReportRecordAsDict.get('flash_version')
      infoTuple = (startedDateTime, completedDateTime, newReportRecordAsDict["truncated"], topmost_filenames, addons_checked, flash_version)
      logger.debug("%s - Updated report %s (%s): %s",threadName,reportId,jobUuid,str(infoTuple))
      threadLocalCursor.execute(reportsSql, infoTuple)
      threadLocalDatabaseConnection.commit()
      self.saveProcessedDumpJson(newReportRecordAsDict)
      logger.info("%s - succeeded and committed: %s, %s", threadName, jobId, jobUuid)
      self.quitCheck()
    except (KeyboardInterrupt, SystemExit):
      logger.info("%s - quit request detected", threadName)
      self.quit = True
      try:
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
      message = '; '.join(processorErrorMessages).replace("'", "''")
      newReportRecordAsDict['processor_notes'] = message
      threadLocalCursor.execute("update jobs set completeddatetime = %s, success = False, message = %s where id = %s", (datetime.datetime.now(), message, jobId))
      threadLocalDatabaseConnection.commit()
      try:
        threadLocalCursor.execute("update reports set started_datetime = timestamp without time zone '%s', completed_datetime = timestamp without time zone '%s', success = False, processor_notes = '%s' where id = %s and date_processed = timestamp without time zone '%s'" % (startedDateTime, datetime.datetime.now(), message, reportId, date_processed))
        threadLocalDatabaseConnection.commit()
        self.saveProcessedDumpJson(newReportRecordAsDict)
      except Exception:
        threadLocalDatabaseConnection.rollback()

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def getJsonOrWarn(jsonDoc,key,errorMessageList, default=None, maxLength=10000):
    """ Utility function to extract 'required' jsonDoc contents
        key: The key for the required value
        errorMessageList: Holds additional error messages as needed
        default: What to return if key is not in jsonDoc. It is NOT checked for maxLength
        maxLength: truncate value of key to this length
        Ran some timing tests on maxLength. Excluding the fixed cost of the loop:
          sys.maxint costs 4.3 x 10K, which is 1 part/million *faster* than 1K from this:
          3 million loops averages 0.116 seconds at 1K, 0.112 seconds at 10K, and .499 seconds at sys.maxint
          http://griswolf.pastebin.com/f3ff6a1d8
    """
    ret = default
    try:
      ret = jsonDoc[key][:maxLength];
    except KeyError:
      errorMessageList.append("WARNING: Json file missing %s"%key)
      ret = default
    except Exception,x:
      errorMessageList.append("ERROR: jsonDoc[%s]: %s"%(repr(key),x))
      logger.error("%s - While extracting '%s' from jsonDoc %s, exception (%s): %s",threading.currentThread().getName(),key,jsonDoc,type(x),x)
    return ret

  #-----------------------------------------------------------------------------------------------------------------
  def insertReportIntoDatabase(self, threadLocalCursor, uuid, jsonDocument, jobPathname, date_processed, processorErrorMessages):
    """
    This function is run only by a worker thread.
      Create the record for the current job in the 'reports' table
      input parameters:
        threadLocalCursor: a database cursor for exclusive use by the calling thread
        uuid: the unique id identifying the job - corresponds with the uuid column in the 'jobs' and the 'reports' tables
        jsonDocument: an object with a dictionary interface for fetching the components of the json document
        jobPathname:  the complete pathname for the json document
        date_processed: when job came in (a key used in partitioning)
        processorErrorMessages: list of strings of error messages
      jsonDocument MUST contain                                      : stored in table reports
        ProductName: Any string with length <= 30                    : in column productdims_id
        Version: Any string with length <= 16                        : in column productdims_id
      jsonDocument SHOULD contain:
        BuildID: 10-character date, as: datetime.strftime('%Y%m%d%H'): build_date (calculated from BuildID) (may also have minutes, seconds)
        CrashTime(preferred), or
        timestamp (deprecated): decimal unix timestamp               : in column client_crash_date
        StartupTime: decimal unix timestamp of 10 or fewer digits    : in column uptime = client_crash_date - startupTime
        InstallTime: decimal unix timestamp of 10 or fewer digits    : in column install_age = client_crash_date - installTime
        SecondsSinceLastCrash: some integer value                    : in column last_crash
      jsonDocument MAY contain:
        Comments: Length <= 500                                      : in column user_comments
        Notes:    Length <= 1000                                     : in column app_notes
        Distributor: Length <= 20                                    : in column distributor
        Distributor_version: Length <= 20                            : in column distributor_version
        HangId: uuid-like                                            : in column hangid
    """
    logger.debug("%s - starting insertReportIntoDatabase", threading.currentThread().getName())
    product = Processor.getJsonOrWarn(jsonDocument,'ProductName',processorErrorMessages,None, 30)
    version = Processor.getJsonOrWarn(jsonDocument,'Version', processorErrorMessages,None,16)
    buildID =   Processor.getJsonOrWarn(jsonDocument,'BuildID', processorErrorMessages,None,16)
    url = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'URL', 255)
    user_comments = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Comments', 500)
    app_notes = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Notes', 1000)
    distributor = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Distributor', 20)
    distributor_version = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Distributor_version', 20)
    defaultCrashTime = int(time.mktime(date_processed.timetuple())) # must have crashed before date processed
    timestampTime = int(jsonDocument.get('timestamp',defaultCrashTime)) # the old name for crash time
    crash_time = int(Processor.getJsonOrWarn(jsonDocument,'CrashTime',processorErrorMessages,timestampTime,10))
    startupTime = int(jsonDocument.get('StartupTime',crash_time)) # must have started up some time before crash
    installTime = int(jsonDocument.get('InstallTime',startupTime)) # must have installed some time before startup
    crash_date = datetime.datetime.fromtimestamp(crash_time, Processor.utctz)
    install_age = crash_time - installTime
    email = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Email', 100)
    hangid = jsonDocument.get('HangID',None)
    logger.debug ('hangid: %s', hangid)
    #logger.debug ('Email: %s', str(jsonDocument))
    # userId is now deprecated and replace with empty string
    user_id = ""
    uptime = max(0, crash_time - startupTime)
    if crash_time == defaultCrashTime:
      logger.warning("%s - no 'crash_time' calculated in %s: Using date_processed", threading.currentThread().getName(), jobPathname)
      #socorro.lib.util.reportExceptionAndContinue(logger, logging.WARNING)
      processorErrorMessages.append("WARNING: No 'client_crash_date' could be determined from the Json file")
    build_date = None
    if buildID:
      try:
        build_date = datetime.datetime(*[int(x) for x in Processor.buildDatePattern.match(str(buildID)).groups()])
      except (AttributeError, ValueError, KeyError):
        logger.warning("%s - no 'build_date' calculated in %s", threading.currentThread().getName(), jobPathname)
        processorErrorMessages.append("WARNING: No 'build_date' could be determined from the Json file")
        socorro.lib.util.reportExceptionAndContinue(logger, logging.WARNING)
    try:
      last_crash = int(jsonDocument['SecondsSinceLastCrash'])
    except:
      last_crash = None

    newReportRecordAsTuple = (uuid, crash_date, date_processed, product, version, buildID, url, install_age, last_crash, uptime, email, build_date, user_id, user_comments, app_notes, distributor, distributor_version,None,None,None,hangid)
    newReportRecordAsDict = dict(x for x in zip(self.reportsTable.columns, newReportRecordAsTuple))
    if not product or not version:
      msgTemplate = "%%s - Skipping report: Missing product&version: ["+", ".join(["%s:%%s"%x for x in self.reportsTable.columns])+"]"
      logger.error(msgTemplate % newReportRecordAsTuple,threading.currentThread().getName())
      return {}
    try:
      logger.debug("%s - inserting for %s, %s", threading.currentThread().getName(), uuid, str(date_processed))
      self.reportsTable.insert(threadLocalCursor, newReportRecordAsTuple, self.databaseConnectionPool.connectToDatabase, date_processed=date_processed)
    except psycopg2.IntegrityError, x:
      logger.debug("%s - psycopg2.IntegrityError %s", threading.currentThread().getName(), str(x))
      logger.debug("%s - %s: this report already exists for date: %s",  threading.currentThread().getName(), uuid, str(date_processed))
      threadLocalCursor.connection.rollback()
      previousTrialWasSuccessful = psy.singleValueSql(threadLocalCursor, "select success from reports where uuid = '%s' and date_processed = timestamp without time zone '%s'" % (uuid, date_processed))
      if previousTrialWasSuccessful:
        raise DuplicateEntryException(uuid)
      threadLocalCursor.execute("delete from reports where uuid = '%s' and date_processed = timestamp without time zone '%s'" % (uuid, date_processed))
      processorErrorMessages.append("INFO: This record is a replacement for a previous record with the same uuid")
      self.reportsTable.insert(threadLocalCursor, newReportRecordAsTuple, self.databaseConnectionPool.connectToDatabase, date_processed=date_processed)
    newReportRecordAsDict["id"] = psy.singleValueSql(threadLocalCursor, "select id from reports where uuid = '%s' and date_processed = timestamp without time zone '%s'" % (uuid, date_processed))
    return newReportRecordAsDict

  #-----------------------------------------------------------------------------------------------------------------
  def insertAdddonsIntoDatabase (self, threadLocalCursor, reportId, jsonDocument, date_processed, processorErrorMessages):
    jsonAddonString = Processor.getJsonOrWarn(jsonDocument, 'Add-ons', processorErrorMessages, "")
    if not jsonAddonString: return []
    listOfAddonsForInput = [x.split(":") for x in jsonAddonString.split(',')]
    listOfAddonsForOutput = []
    for i, x in enumerate(listOfAddonsForInput):
      try:
        self.extensionsTable.insert(threadLocalCursor, (reportId, date_processed, i, x[0][:100], x[1]), self.databaseConnectionPool.connectToDatabase, date_processed=date_processed)
        listOfAddonsForOutput.append(x)
      except IndexError:
        processorErrorMessages.append('WARNING: "%s" is deficient as a name and version for an addon' % str(x))
    return listOfAddonsForOutput

  #-----------------------------------------------------------------------------------------------------------------
  def insertCrashProcess (self, threadLocalCursor, reportId, jsonDocument, date_processed, processorErrorMessages):
    """ Electrolysis Support - Optional - jsonDocument may contain a ProcessType of plugin. In the future this
        value would be default, content, maybe even Jetpack... This indicates which process was the crashing process.
        plugin - When set to plugin, the jsonDocument MUST calso contain PluginFilename, PluginName, and PluginVersion
    """
    listOfCrashProcessOutput = {}
    processType = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'ProcessType', 10)
    if not processType: return listOfCrashProcessOutput
    listOfCrashProcessOutput['processType'] = processType

    if "plugin" == processType:
      # Bug#543776 We actually will are relaxing the non-null policy... a null filename, name, and version is OK. We'll use empty strings
      pluginFilename = socorro.lib.util.lookupStringOrEmptyString(jsonDocument, 'PluginFilename')
      pluginName     = socorro.lib.util.lookupStringOrEmptyString(jsonDocument, 'PluginName')
      pluginVersion  = socorro.lib.util.lookupStringOrEmptyString(jsonDocument, 'PluginVersion')
      listOfCrashProcessOutput.update({'pluginFilename': pluginFilename,'pluginName': pluginName,'pluginVersion': pluginVersion})

      pluginId = None
      try:
        self.pluginsTable.insert(threadLocalCursor, (pluginFilename, pluginName))
      except psycopg2.IntegrityError, x:
        threadLocalCursor.connection.rollback()
        logger.info("%s - No Big Deal - this plugin already exists for pluginFilename: %s pluginName: %s",  threading.currentThread().getName(), pluginFilename, pluginName)

      try:
        self.pluginsReportsTable.insert(threadLocalCursor,
                                          (reportId, pluginFilename, pluginName, date_processed, pluginVersion),
                                          self.databaseConnectionPool.connectToDatabase, date_processed=date_processed)
      except psycopg2.IntegrityError, x:
        logger.error("%s - psycopg2.IntegrityError %s", threading.currentThread().getName(), str(x))
        logger.error("%s - %s: Unable to save record for plugin report. pluginId: %s reportId: %s version: %s",  threading.currentThread().getName(), reportId, pluginId, pluginVersion)
        processorErrorMessages.append("Detected out of process plugin crash, but unable to record %s %s %s" % (pluginFilename, pluginName, pluginVersion))
      return listOfCrashProcessOutput

  #-----------------------------------------------------------------------------------------------------------------
  def doBreakpadStackDumpAnalysis (self, reportId, uuid, dumpfilePathname, databaseCursor, date_processed, processorErrorMessages):
    """ This function is run only by a worker thread.
        This function must be overriden in a subclass - this method will invoke the breakpad_stackwalk process
        (if necessary) and then do the anaylsis of the output
    """
    raise Exception("No breakpad_stackwalk invocation method specified")


