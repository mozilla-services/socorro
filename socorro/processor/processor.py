import datetime
from operator import itemgetter
import logging
import os
import os.path
import re
import signal
import threading
import time

logger = logging.getLogger("processor")

import socorro.database.schema as sch

import socorro.lib.util as sutil
import socorro.lib.threadlib as sthr
import socorro.lib.ConfigurationManager as scm
import socorro.lib.JsonDumpStorage as jds
import socorro.database.database as sdb
import socorro.lib.ooid as ooid
import socorro.lib.datetimeutil as sdt
import socorro.storage.crashstorage as cstore
import socorro.storage.hbaseClient as hbc
import socorro.processor.signatureUtilities as sig

#=================================================================================================================
class DuplicateEntryException(Exception):
  pass

#=================================================================================================================
class ErrorInBreakpadStackwalkException(Exception):
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

  _config_requirements = ("databaseHost",
                          "databaseName",
                          "databaseUserName",
                          "databasePassword",
                          "processorCheckInTime",
                          "processorCheckInFrequency",
                          "processorLoopTime",
                          "jsonFileSuffix",
                          "dumpFileSuffix",
                          "processorId",
                          "numberOfThreads",
                          "batchJobLimit",
                          "irrelevantSignatureRegEx",
                          "prefixSignatureRegEx",
                          "collectAddon",
                          "collectCrashProcess",
                          "signatureSentinels",
                          "signaturesWithLineNumbersRegEx",
                          "hbaseHost",
                          "hbasePort",
                          "temporaryFileSystemStoragePath",
                         )

  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config, sdb=sdb, cstore=cstore, signal=signal,
                sthr=sthr, os=os, nowFunc=datetime.datetime.now):
    """
    """
    super(Processor, self).__init__()

    if 'logger' not in config:
      config.logger = logger

    for x in Processor._config_requirements:
      assert x in config, '%s missing from configuration' % x

    self.crashStorePool = cstore.CrashStoragePool(config)

    self.sdb = sdb
    self.os = os
    self.nowFunc = nowFunc
    self.databaseConnectionPool = sdb.DatabaseConnectionPool(config, config.logger)
    self.processorLoopTime = config.processorLoopTime.seconds
    self.config = config
    self.quit = False
    signal.signal(signal.SIGTERM, Processor.respondToSIGTERM)
    signal.signal(signal.SIGHUP, Processor.respondToSIGTERM)
    self.irrelevantSignatureRegEx = re.compile(self.config.irrelevantSignatureRegEx)
    self.prefixSignatureRegEx = re.compile(self.config.prefixSignatureRegEx)
    self.signaturesWithLineNumbersRegEx = re.compile(self.config.signaturesWithLineNumbersRegEx)

    self.reportsTable = sch.ReportsTable(logger=config.logger)
    self.extensionsTable = sch.ExtensionsTable(logger=config.logger)
    self.framesTable = sch.FramesTable(logger=config.logger)
    self.pluginsTable = sch.PluginsTable(logger=config.logger)
    self.pluginsReportsTable = sch.PluginsReportsTable(logger=config.logger)

    self.signatureUtilities = sig.SignatureUtilities(config)

    self.registration()

    # force checkin to run immediately after start(). I don't understand the need, since the database already reflects nearly-real reality. Oh well.
    self.lastCheckInTimestamp = datetime.datetime(1950, 1, 1)
    #self.getNextJobSQL = "select j.id, j.pathname, j.uuid from jobs j where j.owner = %d and startedDateTime is null order by priority desc, queuedDateTime asc limit 1" % self.processorId

    # start the thread manager with the number of threads specified in the configuration.  The second parameter controls the size
    # of the internal task queue within the thread manager.  It is constrained so that the queue remains starved.  This means that tasks
    # remain queued in the database until the last minute.  This allows some external process to change the priority of a job by changing
    # the 'priority' column of the 'jobs' table for the particular record in the database.  If the threadManager were allowed to suck all
    # the pending jobs from the database, then the job priority could not be changed by an external process.
    logger.info("starting worker threads")
    self.threadManager = sthr.TaskManager(self.config.numberOfThreads, self.config.numberOfThreads * 2)
    logger.info("I am processor #%d", self.processorId)
    logger.info("my priority jobs table is called: '%s'", self.priorityJobsTableName)

  #-----------------------------------------------------------------------------
  @sdb.db_transaction_retry_wrapper
  def registration(self):
    logger.info("connecting to database")
    try:
      databaseConnection, databaseCursor =  \
                        self.databaseConnectionPool.connectionCursorPair()
    except sdb.exceptions_eligible_for_retry:
      raise
    except Exception:
      self.quit = True
      logger.critical("cannot connect to the database")
      sutil.reportExceptionAndAbort(logger)

    # register self with the processors table in the database
    # Must request 'auto' id, or an id number that is in the processors table
    # AND not alive
    logger.info("registering with 'processors' table")
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
          raise scm.OptionError("%s is not a valid option for processorId" %
                                self.config.processorId)
      self.processorName = "%s_%d" % (self.os.uname()[1], self.os.getpid())
      threshold = self.sdb.singleValueSql(databaseCursor,
                                          "select now() - interval '%s'" %
                                            self.config.processorCheckInTime)
      if requestedId == 'auto':  # take over for an existing processor
        logger.debug("looking for a dead processor")
        try:
          self.processorId = self.sdb.singleValueSql(databaseCursor,
                                                     "select id from processors"
                                                     " where lastseendatetime <"
                                                     " '%s' limit 1" %
                                                     threshold)
          logger.info("will step in for processor %d", self.processorId)
        except sdb.SQLDidNotReturnSingleValue:
          logger.debug("no dead processor found")
          requestedId = 0 # signal that we found no dead processors
      else: # requestedId is an integer: We already raised OptionError if not
        try:
          # singleValueSql should actually accept sql with placeholders and an
          # array of values instead of just a string. Enhancement needed...
          checkSql = "select id from processors where lastSeenDateTime < '%s' " \
                     "and id = %s" % (threshold,requestedId)
          self.processorId = self.sdb.singleValueSql(databaseCursor, checkSql)
          logger.info("stepping in for processor %d", self.processorId)
        except sdb.SQLDidNotReturnSingleValue,x:
          raise scm.OptionError("ProcessorId %s is not in processors table or "
                                "is still live." % requestedId)
      if requestedId == 0:
        try:
          databaseCursor.execute("insert into processors (name, startdatetime, "
                                 "lastseendatetime) values (%s, now(), now())",
                                 (self.processorName,))
          self.processorId = self.sdb.singleValueSql(databaseCursor,
                                                     "select id from processors"
                                                     " where name = '%s'" %
                                                     (self.processorName,))
        except sdb.exceptions_eligible_for_retry:
          raise
        except Exception, x:
          databaseConnection.rollback()
          raise
        logger.info("initializing as processor %d", self.processorId)
        priorityCreateRuberic = "Does it already exist?"
        # We have a good processorId and a name. Register self with database
      try:
        databaseCursor.execute("update processors set name = %s, "
                               "startdatetime = now(), lastseendatetime = now()"
                               " where id = %s",
                               (self.processorName, self.processorId))
        databaseCursor.execute("update jobs set"
                               "    starteddatetime = NULL,"
                               "    completeddatetime = NULL,"
                               "    success = NULL "
                               "where"
                               "    owner = %s", (self.processorId, ))
      except sdb.exceptions_eligible_for_retry:
        raise
      except Exception, x:
        logger.critical("Constructor: Unable to update processors or jobs "
                        "table: %s: %s", type(x), x)
        databaseConnection.rollback()
        raise
    except sdb.exceptions_eligible_for_retry:
      raise
    except Exception, x:
      logger.critical("cannot register with the database %s %s", str(type(x)), str(x))
      databaseConnection.rollback()
      self.quit = True
      # can't continue without a registration
      sutil.reportExceptionAndAbort(logger)
    # We're registered, make sure we have our own priority_jobs table
    self.priorityJobsTableName = "priority_jobs_%d" % self.processorId
    try:
      databaseCursor.execute("create table %s (uuid varchar(50) not null "
                             "primary key)" % self.priorityJobsTableName)
      databaseConnection.commit()
    except sdb.exceptions_eligible_for_retry:
      raise
    #except sdb.db_module.Error:
      #sutil.reportExceptionAndContinue()
      #logger.debug('aoeuaoeu')
      #databaseConnection.rollback()
      #raise
    except sdb.db_module.ProgrammingError, x:
      logger.warning('failed to create table %s because "%s". %s This is '
                     'probably OK', self.priorityJobsTableName, str(x),
                     priorityCreateRuberic)
      databaseConnection.rollback()

  #-----------------------------------------------------------------------------
  def quitCheck(self):
    if self.quit:
      raise KeyboardInterrupt

  #-----------------------------------------------------------------------------
  def responsiveSleep (self, seconds, waitLogInterval=0, waitReason=''):
    for x in xrange(int(seconds)):
      self.quitCheck()
      if waitLogInterval and not x % waitLogInterval:
        logger.info('%s: %dsec of %dsec',
                                                     waitReason,
                                                     x,
                                                     seconds)
      time.sleep(1.0)

  #-----------------------------------------------------------------------------
  @sdb.db_transaction_retry_wrapper
  def checkin (self):
    """ a processor must keep its database registration current.  If a processor
        has not updated its record in the database in the interval specified in
        as self.config.processorCheckInTime, the monitor will consider it to be
        expired.  The monitor will stop assigning jobs to it and reallocate
        its unfinished jobs to other processors.
    """
    if self.lastCheckInTimestamp + self.config.processorCheckInFrequency < \
          self.nowFunc():
      logger.debug("updating 'processor' table registration")
      tstamp = self.nowFunc()
      databaseConnection, databaseCursor =  \
                        self.databaseConnectionPool.connectionCursorPair()
      databaseCursor.execute("update processors set lastseendatetime = %s "
                             "where id = %s", (tstamp, self.processorId))
      databaseConnection.commit()
      self.lastCheckInTimestamp = self.nowFunc()

  #-----------------------------------------------------------------------------
  def cleanup(self):
    """ clean up before shutdown
    """
    logger.info("waiting for threads to stop")
    self.threadManager.waitForCompletion()
    logger.info("all threads stopped")

    databaseConnection, databaseCursor = self.databaseConnectionPool.connectionCursorPair()
    try:
      # force the processor to record a lastSeenDateTime in the distant past so that the monitor will
      # mark it as dead.  The monitor will process its completed jobs and reallocate it unfinished ones.
      logger.debug("unregistering processor")
      databaseCursor.execute("update processors set lastseendatetime = '1999-01-01' where id = %s", (self.processorId,))
      databaseConnection.commit()
    except Exception, x:
      logger.critical("could not unregister %d from the database", self.processorId)
      databaseConnection.rollback()
      sutil.reportExceptionAndContinue(logger)
    try:
      databaseCursor.execute("drop table %s" % self.priorityJobsTableName)
      databaseConnection.commit()
    except sdb.db_module.Error:
      logger.error("Cannot complete cleanup.  %s may need manual deletion", self.priorityJobsTableName)
      databaseConnection.rollback()
      sutil.reportExceptionAndContinue(logger)

    # we're done - kill all the threads' database connections
    self.databaseConnectionPool.cleanup()
    self.crashStorePool.cleanup()

    logger.debug("done with work")

  #-----------------------------------------------------------------------------
  @staticmethod
  def respondToSIGTERM(signalNumber, frame):
    """ these classes are instrumented to respond to a KeyboardInterrupt by cleanly shutting down.
        This function, when given as a handler to for a SIGTERM event, will make the program respond
        to a SIGTERM as neatly as it responds to ^C.
    """
    signame = 'SIGTERM'
    if signalNumber != signal.SIGTERM: signame = 'SIGHUP'
    logger.info("%s detected",signame)
    raise KeyboardInterrupt

  #-----------------------------------------------------------------------------
  def submitJobToThreads(self, aJobTuple):
    self.sdb.transaction_execute_with_retry(
                        self.databaseConnectionPool,
                        "update jobs set starteddatetime = %s where id = %s",
                        (self.nowFunc(), aJobTuple[0]))
    #logger.info("queuing job %d, %s, %s",
                #aJobTuple[0], aJobTuple[2],  aJobTuple[1])
    self.threadManager.newTask(self.processJobWithRetry, aJobTuple)
    #self.threadManager.newTask(self.processJob, aJobTuple)

  #-----------------------------------------------------------------------------
  def newPriorityJobsIter (self):
    """
    Yields a list of JobTuples pulled from the 'jobs' table for all the jobs
    found in this process' priority jobs table.  If there are no priority jobs,
    yields None.
    This iterator is perpetual - it never raises the StopIteration exception
    """
    getPriorityJobsSql =  "select" \
                          "    j.id," \
                          "    pj.uuid," \
                          "    1," \
                          "    j.starteddatetime " \
                          "from" \
                          "    jobs j right join %s pj on j.uuid = pj.uuid" \
                          % self.priorityJobsTableName
    deleteOnePriorityJobSql = "delete from %s where uuid = %%s" %  \
                              self.priorityJobsTableName
    fullJobsList = []
    while True:
      if not fullJobsList:
        fullJobsList = self.sdb.transaction_execute_with_retry(
                                  self.databaseConnectionPool,
                                  getPriorityJobsSql)
      if fullJobsList:
        while fullJobsList:
          aFullJobTuple = fullJobsList.pop(-1)
          self.sdb.transaction_execute_with_retry(self.databaseConnectionPool,
                                                  deleteOnePriorityJobSql,
                                                  (aFullJobTuple[1],))
          if aFullJobTuple[0] is not None:
            if aFullJobTuple[3]:
              continue
            else:
              yield (aFullJobTuple[0],aFullJobTuple[1],aFullJobTuple[2],)
          else:
            logger.debug("the priority job %s was never found", aFullJobTuple[1])
      else:
        yield None

  #-----------------------------------------------------------------------------
  def newNormalJobsIter (self):
    """
    Yields a list of job tuples pulled from the 'jobs' table for which the owner
    is this process and the started datetime is null.
    This iterator is perpetual - it never raises the StopIteration exception
    """
    getNormalJobSql = "select"  \
                      "    j.id,"  \
                      "    j.uuid,"  \
                      "    priority "  \
                      "from"  \
                      "    jobs j "  \
                      "where"  \
                      "    j.owner = %d"  \
                      "    and j.starteddatetime is null "  \
                      "order by queueddatetime"  \
                      "  limit %d" % (self.processorId,
                                        self.config.batchJobLimit)
    normalJobsList = []
    while True:
      if not normalJobsList:
        normalJobsList = self.sdb.transaction_execute_with_retry( \
                              self.databaseConnectionPool,
                              getNormalJobSql
                              )
      if normalJobsList:
        while normalJobsList:
          yield normalJobsList.pop(-1)
      else:
        yield None

  #-----------------------------------------------------------------------------
  def incomingJobStream(self):
    """
       aJobTuple has this form: (jobId, jobUuid, jobPriority) ... of which
       jobPriority is pure excess, and should someday go away
       Yields the next job according to this pattern:
       START
       Attempt to yield a priority job
       If no priority job, attempt to yield a normal job
       If no priority or normal job, sleep self.processorLoopTime seconds
       loop back to START
    """
    priorityJobIter = self.newPriorityJobsIter()
    normalJobIter = self.newNormalJobsIter()
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
          logger.debug("incomingJobStream yielding %s job %s", aJobType, aJobTuple[1])
          yield aJobTuple
        else:
          logger.debug("Skipping already seen job %s", aJobTuple[1])
      else:
        logger.info("no jobs to do - sleeping %d seconds", self.processorLoopTime)
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
        #get a job
        for aJobTuple in self.incomingJobStream():
          self.quitCheck()
          #logger.debug("start got: %s", aJobTuple[1])
          self.submitJobToThreads(aJobTuple)
      except KeyboardInterrupt:
        logger.info("quit request detected")
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
  def saveProcessedDumpJson (self, aReportRecordAsDict, threadLocalCrashStorage):
    #date_processed = aReportRecordAsDict["date_processed"]
    Processor.sanitizeDict(aReportRecordAsDict)
    Processor.convertDatesInDictToString(aReportRecordAsDict)
    uuid = aReportRecordAsDict["uuid"]
    threadLocalCrashStorage.save_processed(uuid, aReportRecordAsDict)

  #-----------------------------------------------------------------------------------------------------------------
  ok = 0
  criticalError = 1
  quit = 2

  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def backoffSecondsGenerator():
    seconds = [10, 30, 60, 120, 300]
    for x in seconds:
      yield x
    while True:
      yield seconds[-1]

  #-----------------------------------------------------------------------------------------------------------------
  def processJobWithRetry(self, jobTuple):
    backoffGenerator = self.backoffSecondsGenerator()
    try:
      while True:
        result = self.processJob(jobTuple)
        #self.logger.debug('task complete: %d', result)
        if result in (Processor.ok, Processor.quit):
          return
        waitInSeconds = backoffGenerator.next()
        logger.critical('major failure in crash storage - retry in %s seconds', waitInSeconds)
        self.responsiveSleep(waitInSeconds, 10, "waiting for retry after failure in crash storage")
    except KeyboardInterrupt:
      return

  #-----------------------------------------------------------------------------------------------------------------
  def processJob (self, jobTuple):
    """ This function is run only by a worker thread.
        Given a job, fetch a thread local database connection and the json document.  Use these
        to create the record in the 'reports' table, then start the analysis of the dump file.

        input parameters:
          jobTuple: a tuple containing up to three items: the jobId (the primary key from the jobs table), the
              jobUuid (a unique string with the json file basename minus the extension) and the priority (an integer)
    """
    if self.quit:
      return Processor.quit
    threadName = threading.currentThread().getName()

    try:
      threadLocalDatabaseConnection, threadLocalCursor = self.databaseConnectionPool.connectionCursorPair()
      threadLocalCrashStorage = self.crashStorePool.crashStorage(threadName)
    except sdb.db_module.OperationalError:
      logger.critical("something's gone horribly wrong with the database connection")
      sutil.reportExceptionAndContinue(logger, loggingLevel=logging.CRITICAL)
      return Processor.criticalError
    except hbc.FatalException:
      logger.critical("something's gone horribly wrong with the HBase connection")
      sutil.reportExceptionAndContinue(logger, loggingLevel=logging.CRITICAL)
      return Processor.criticalError
    except Exception:
      self.quit = True
      sutil.reportExceptionAndContinue(logger, loggingLevel=logging.CRITICAL)
      return Processor.quit

    try:
      self.quitCheck()
      newReportRecordAsDict = {}
      processorErrorMessages = []
      jobId, jobUuid, jobPriority = jobTuple
      logger.info("starting job: %s", jobUuid)
      startedDateTime = self.nowFunc()
      threadLocalCursor.execute("update jobs set starteddatetime = %s where id = %s", (startedDateTime, jobId))
      threadLocalDatabaseConnection.commit()

      jsonDocument = threadLocalCrashStorage.get_meta(jobUuid)
      try:
        date_processed = sdt.datetimeFromISOdateString(jsonDocument["submitted_timestamp"])
      except KeyError:
        date_processed = ooid.dateFromOoid(jobUuid)

      newReportRecordAsDict = self.insertReportIntoDatabase(threadLocalCursor, jobUuid, jsonDocument, date_processed, processorErrorMessages)

      threadLocalDatabaseConnection.commit()
      reportId = newReportRecordAsDict["id"]
      newReportRecordAsDict['dump'] = ''
      newReportRecordAsDict["startedDateTime"] = startedDateTime

      if self.config.collectAddon:
        #logger.debug("collecting Addons")
        addonsAsAListOfTuples = self.insertAdddonsIntoDatabase(threadLocalCursor, reportId, jsonDocument, date_processed, processorErrorMessages)
        newReportRecordAsDict["addons"] = addonsAsAListOfTuples

      if self.config.collectCrashProcess:
        #logger.debug("collecting Crash Process")
        crashProcessAsDict = self.insertCrashProcess(threadLocalCursor, reportId, jsonDocument, date_processed, processorErrorMessages)
        newReportRecordAsDict.update( crashProcessAsDict )

      try:
        dumpfilePathname = threadLocalCrashStorage.dumpPathForUuid(jobUuid,
                                                             self.config.temporaryFileSystemStoragePath)
        #logger.debug('about to doBreakpadStackDumpAnalysis')
        isHang = 'hangid' in newReportRecordAsDict and bool(newReportRecordAsDict['hangid'])
        additionalReportValuesAsDict = self.doBreakpadStackDumpAnalysis(reportId, jobUuid, dumpfilePathname, isHang, threadLocalCursor, date_processed, processorErrorMessages)
        newReportRecordAsDict.update(additionalReportValuesAsDict)
      finally:
        newReportRecordAsDict["completeddatetime"] = completedDateTime = self.nowFunc()
        threadLocalCrashStorage.cleanUpTempDumpStorage(jobUuid, self.config.temporaryFileSystemStoragePath)

      #logger.debug('finished a job - cleanup')
      #finished a job - cleanup
      threadLocalCursor.execute("update jobs set completeddatetime = %s, success = %s where id = %s", (completedDateTime, newReportRecordAsDict['success'], jobId))
      # Bug 519703: Collect setting for topmost source filename(s), addon compatibility check override, flash version
      reportsSql = """
      update reports set
        signature = %%s,
        processor_notes = %%s,
        started_datetime = timestamp without time zone %%s,
        completed_datetime = timestamp without time zone %%s,
        success = %%s,
        truncated = %%s,
        topmost_filenames = %%s,
        addons_checked = %%s,
        flash_version = %%s
      where id = %s and date_processed = timestamp without time zone '%s'
      """ % (reportId,date_processed)
      #logger.debug("newReportRecordAsDict %s, %s", newReportRecordAsDict['topmost_filenames'], newReportRecordAsDict['flash_version'])
      #topmost_filenames = "|".join(jsonDocument.get('topmost_filenames',[]))
      topmost_filenames = "|".join(newReportRecordAsDict.get('topmost_filenames',[]))
      addons_checked = None
      try:
        addons_checked_txt = jsonDocument['EMCheckCompatibility'].lower()
        addons_checked = False
        if addons_checked_txt == 'true':
          addons_checked = True
      except KeyError:
        pass # leaving it as None if not in the document
      try:
        newReportRecordAsDict['Winsock_LSP'] = jsonDocument['Winsock_LSP']
      except KeyError:
        pass # if it's not in the original json, it does get into the jsonz
      #flash_version = jsonDocument.get('flash_version')
      flash_version = newReportRecordAsDict.get('flash_version')
      processor_notes = '; '.join(processorErrorMessages)
      newReportRecordAsDict['processor_notes'] = processor_notes
      infoTuple = (newReportRecordAsDict['signature'], processor_notes, startedDateTime, completedDateTime, newReportRecordAsDict["success"], newReportRecordAsDict["truncated"], topmost_filenames, addons_checked, flash_version)
      #logger.debug("Updated report %s (%s): %s", reportId, jobUuid, str(infoTuple))
      threadLocalCursor.execute(reportsSql, infoTuple)
      threadLocalDatabaseConnection.commit()
      self.saveProcessedDumpJson(newReportRecordAsDict, threadLocalCrashStorage)
      if newReportRecordAsDict["success"]:
        logger.info("succeeded and committed: %s", jobUuid)
      else:
        logger.info("failed but committed: %s", jobUuid)
      self.quitCheck()
      return Processor.ok
    except (KeyboardInterrupt, SystemExit):
      logger.info("quit request detected")
      self.quit = True
      return Processor.quit
    except DuplicateEntryException, x:
      logger.warning("duplicate entry: %s", jobUuid)
      threadLocalCursor.execute('delete from jobs where id = %s', (jobId,))
      threadLocalDatabaseConnection.commit()
      return Processor.ok
    except sdb.db_module.OperationalError:
      logger.critical("something's gone horribly wrong with the database connection")
      sutil.reportExceptionAndContinue(logger, loggingLevel=logging.CRITICAL)
      return Processor.criticalError
    except hbc.FatalException:
      logger.critical("something's gone horribly wrong with the HBase connection")
      sutil.reportExceptionAndContinue(logger, loggingLevel=logging.CRITICAL)
      return Processor.criticalError
    except Exception, x:
      if x.__class__ != ErrorInBreakpadStackwalkException:
        sutil.reportExceptionAndContinue(logger)
      else:
        sutil.reportExceptionAndContinue(logger, logging.WARNING, showTraceback=False)
      threadLocalDatabaseConnection.rollback()
      processorErrorMessages.append(str(x))
      message = '; '.join(processorErrorMessages).replace("'", "''")
      newReportRecordAsDict['processor_notes'] = message
      threadLocalCursor.execute("update jobs set completeddatetime = %s, success = False, message = %s where id = %s", (self.nowFunc(), message, jobId))
      threadLocalDatabaseConnection.commit()
      try:
        threadLocalCursor.execute("update reports set started_datetime = timestamp without time zone %s, completed_datetime = timestamp without time zone %s, success = False, processor_notes = %s where id = %s and date_processed = timestamp without time zone %s", (startedDateTime, self.nowFunc(), message, reportId, date_processed))
        threadLocalDatabaseConnection.commit()
        self.saveProcessedDumpJson(newReportRecordAsDict, threadLocalCrashStorage)
      except Exception, x:
        sutil.reportExceptionAndContinue(logger)
        threadLocalDatabaseConnection.rollback()
      return Processor.ok

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
      logger.warning("While extracting '%s' from jsonDoc %s, exception (%s): %s",key,jsonDoc,type(x),x)
    return ret

  #-----------------------------------------------------------------------------------------------------------------
  def insertReportIntoDatabase(self, threadLocalCursor, uuid, jsonDocument, date_processed, processorErrorMessages):
    """
    This function is run only by a worker thread.
      Create the record for the current job in the 'reports' table
      input parameters:
        threadLocalCursor: a database cursor for exclusive use by the calling thread
        uuid: the unique id identifying the job - corresponds with the uuid column in the 'jobs' and the 'reports' tables
        jsonDocument: an object with a dictionary interface for fetching the components of the json document
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
    #logger.debug("starting insertReportIntoDatabase")
    product = Processor.getJsonOrWarn(jsonDocument,'ProductName',processorErrorMessages,None, 30)
    version = Processor.getJsonOrWarn(jsonDocument,'Version', processorErrorMessages,None,16)
    buildID =   Processor.getJsonOrWarn(jsonDocument,'BuildID', processorErrorMessages,None,16)
    url = sutil.lookupLimitedStringOrNone(jsonDocument, 'URL', 255)
    user_comments = sutil.lookupLimitedStringOrNone(jsonDocument, 'Comments', 500)
    app_notes = sutil.lookupLimitedStringOrNone(jsonDocument, 'Notes', 1000)
    distributor = sutil.lookupLimitedStringOrNone(jsonDocument, 'Distributor', 20)
    distributor_version = sutil.lookupLimitedStringOrNone(jsonDocument, 'Distributor_version', 20)
    defaultCrashTime = int(time.mktime(date_processed.timetuple())) # must have crashed before date processed
    timestampTime = int(jsonDocument.get('timestamp',defaultCrashTime)) # the old name for crash time
    crash_time = int(Processor.getJsonOrWarn(jsonDocument,'CrashTime',processorErrorMessages,timestampTime,10))
    startupTime = int(jsonDocument.get('StartupTime',crash_time)) # must have started up some time before crash
    installTime = int(jsonDocument.get('InstallTime',startupTime)) # must have installed some time before startup
    crash_date = datetime.datetime.fromtimestamp(crash_time, Processor.utctz)
    install_age = crash_time - installTime
    email = sutil.lookupLimitedStringOrNone(jsonDocument, 'Email', 100)
    hangid = jsonDocument.get('HangID',None)
    process_type = sutil.lookupLimitedStringOrNone(jsonDocument, 'ProcessType', 10)
    #logger.debug ('hangid: %s', hangid)
    #logger.debug ('Email: %s', str(jsonDocument))
    # userId is now deprecated and replace with empty string
    user_id = ""
    uptime = max(0, crash_time - startupTime)
    if crash_time == defaultCrashTime:
      logger.warning("no 'crash_time' calculated in %s: Using date_processed", uuid)
      #sutil.reportExceptionAndContinue(logger, logging.WARNING)
      processorErrorMessages.append("WARNING: No 'client_crash_date' could be determined from the Json file")
    build_date = None
    if buildID:
      try:
        build_date = datetime.datetime(*[int(x) for x in Processor.buildDatePattern.match(str(buildID)).groups()])
      except (AttributeError, ValueError, KeyError):
        logger.warning("no 'build_date' calculated in %s", uuid)
        processorErrorMessages.append("WARNING: No 'build_date' could be determined from the Json file")
        sutil.reportExceptionAndContinue(logger, logging.WARNING)
    try:
      last_crash = int(jsonDocument['SecondsSinceLastCrash'])
    except:
      last_crash = None

    newReportRecordAsTuple = (uuid, crash_date, date_processed, product, version, buildID, url, install_age, last_crash, uptime, email, build_date, user_id, user_comments, app_notes, distributor, distributor_version,None,None,None,hangid,process_type)
    newReportRecordAsDict = dict(x for x in zip(self.reportsTable.columns, newReportRecordAsTuple))
    if not product or not version:
      msgTemplate = "Skipping report: Missing product&version: ["+", ".join(["%s:%%s"%x for x in self.reportsTable.columns])+"]"
      logger.error(msgTemplate % newReportRecordAsTuple)
      return {}
    try:
      #logger.debug("inserting for %s, %s", uuid, str(date_processed))
      self.reportsTable.insert(threadLocalCursor, newReportRecordAsTuple, self.databaseConnectionPool.connectionCursorPair, date_processed=date_processed)
    except sdb.db_module.IntegrityError, x:
      #logger.debug("psycopg2.IntegrityError %s", str(x))
      logger.debug("replacing record that already exsited: %s", uuid)
      threadLocalCursor.connection.rollback()
      # the following code fragment can prevent a crash from being processed a second time
      #previousTrialWasSuccessful = self.sdb.singleValueSql(threadLocalCursor, "select success from reports where uuid = '%s' and date_processed = timestamp without time zone '%s'" % (uuid, date_processed))
      #if previousTrialWasSuccessful:
        #raise DuplicateEntryException(uuid)
      threadLocalCursor.execute("delete from reports where uuid = '%s' and date_processed = timestamp without time zone '%s'" % (uuid, date_processed))
      processorErrorMessages.append("INFO: This record is a replacement for a previous record with the same uuid")
      self.reportsTable.insert(threadLocalCursor, newReportRecordAsTuple, self.databaseConnectionPool.connectionCursorPair, date_processed=date_processed)
    newReportRecordAsDict["id"] = self.sdb.singleValueSql(threadLocalCursor, "select id from reports where uuid = '%s' and date_processed = timestamp without time zone '%s'" % (uuid, date_processed))

    return newReportRecordAsDict

  #-----------------------------------------------------------------------------------------------------------------
  def insertAdddonsIntoDatabase (self, threadLocalCursor, reportId, jsonDocument, date_processed, processorErrorMessages):
    jsonAddonString = Processor.getJsonOrWarn(jsonDocument, 'Add-ons', processorErrorMessages, "")
    if not jsonAddonString: return []
    listOfAddonsForInput = [x.split(":") for x in jsonAddonString.split(',')]
    listOfAddonsForOutput = []
    for i, x in enumerate(listOfAddonsForInput):
      try:
        self.extensionsTable.insert(threadLocalCursor, (reportId, date_processed, i, x[0][:100], x[1]), self.databaseConnectionPool.connectionCursorPair, date_processed=date_processed)
        listOfAddonsForOutput.append(x)
      except IndexError:
        processorErrorMessages.append('WARNING: "%s" is deficient as a name and version for an addon' % str(x[0]))
    return listOfAddonsForOutput

  #-----------------------------------------------------------------------------------------------------------------
  def insertCrashProcess (self, threadLocalCursor, reportId, jsonDocument,
                          date_processed, processorErrorMessages):
    """ Electrolysis Support - Optional - jsonDocument may contain a ProcessType
    of plugin. In the future this value would be default, content, maybe even
    Jetpack... This indicates which process was the crashing process.
        plugin - When set to plugin, the jsonDocument MUST calso contain
                 PluginFilename, PluginName, and PluginVersion
    """
    crashProcesOutputDict = sutil.DotDict()
    processType = sutil.lookupLimitedStringOrNone(jsonDocument, 'ProcessType',
                                                  10)
    if not processType:
      return crashProcesOutputDict
    crashProcesOutputDict.processType = processType

    #logger.debug('processType %s', processType)
    if "plugin" == processType:
      # Bug#543776 We actually will are relaxing the non-null policy... a null
      # filename, name, and version is OK. We'll use empty strings
      pluginFilename = sutil.lookupStringOrEmptyString(jsonDocument,
                                                       'PluginFilename')
      pluginName     = sutil.lookupStringOrEmptyString(jsonDocument,
                                                       'PluginName')
      pluginVersion  = sutil.lookupStringOrEmptyString(jsonDocument,
                                                       'PluginVersion')
      crashProcesOutputDict.pluginFilename = pluginFilename
      crashProcesOutputDict.pluginName = pluginName
      crashProcesOutputDict.pluginVersion = pluginVersion

      try:
        pluginId = self.sdb.singleRowSql(threadLocalCursor,
                                         'select id from plugins '
                                         'where filename = %s '
                                         'and name = %s',
                                         (pluginFilename, pluginName))
        #logger.debug('%s/%s already exists in the database',
                     #pluginFilename, pluginName)
      except sdb.SQLDidNotReturnSingleRow, x:
        self.pluginsTable.insert(threadLocalCursor,
                                 (pluginFilename, pluginName))
        pluginId = self.sdb.singleRowSql(threadLocalCursor,
                                         'select id from plugins '
                                         'where filename = %s '
                                         'and name = %s',
                                         (pluginFilename, pluginName))
        #logger.debug('%s/%s inserted into the database',
                     #pluginFilename, pluginName)

      try:
        self.pluginsReportsTable.insert(threadLocalCursor,
                                          (reportId,
                                           pluginId,
                                           date_processed,
                                           pluginVersion),
                                        self.databaseConnectionPool.connectionCursorPair,
                                        date_processed=date_processed)
      except sdb.db_module.IntegrityError, x:
        logger.error("psycopg2.IntegrityError %s", str(x))
        logger.error("Unable to save record for plugin report. pluginId: %s"
                     "reportId: %s version: %s", pluginId, reportId,
                     pluginVersion)
        processorErrorMessages.append("Detected out of process plugin crash, "
                                      "but unable to record %s %s %s" %
                                      (pluginFilename, pluginName,
                                       pluginVersion))
    return crashProcesOutputDict

  #-----------------------------------------------------------------------------------------------------------------
  def doBreakpadStackDumpAnalysis (self, reportId, uuid, dumpfilePathname, isHang, databaseCursor, date_processed, processorErrorMessages):
    """ This function is run only by a worker thread.
        This function must be overriden in a subclass - this method will invoke the breakpad_stackwalk process
        (if necessary) and then do the anaylsis of the output
    """
    raise Exception("No breakpad_stackwalk invocation method specified")


