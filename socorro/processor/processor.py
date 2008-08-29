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

import socorro.lib.util
import socorro.lib.threadlib
import socorro.lib.ConfigurationManager
import socorro.lib.psycopghelper

import simplejson

#==========================================================
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

#==========================================================
class DuplicateEntryException(Exception):
  pass

#==========================================================
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
        self.threadLocalDatabaseConnections: each thread uses its own connection to the database.
            This dictionary, indexed by thread name, is just a repository for the connections that
            persists between jobs.
  """
  buildDatePattern = re.compile('^(\\d{4})(\\d{2})(\\d{2})(\\d{2})')
  fixupSpace = re.compile(r' (?=[\*&,])')
  fixupComma = re.compile(r'(?<=,)(?! )')
  filename_re = re.compile('[/\\\\]([^/\\\\]+)$')
  utctz = UTC()

  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config):
    """
    """
    super(Processor, self).__init__()
    self.config = config

    signal.signal(signal.SIGTERM, Processor.respondToSIGTERM)

    self.quit = False

    logger.info("%s - connecting to database", threading.currentThread().getName())
    try:
      self.mainThreadDatabaseConnection = psycopg2.connect(self.config.databaseDSN)
      self.mainThreadCursor = self.mainThreadDatabaseConnection.cursor()
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
        threshold = socorro.lib.psycopghelper.singleValueSql(self.mainThreadCursor, "select now() - interval '%s'" % self.config.processorCheckInTime)
        try:
          logger.debug("%s - looking for a dead processor", threading.currentThread().getName())
          self.config.processorId = socorro.lib.psycopghelper.singleValueSql(self.mainThreadCursor, "select id from processors where lastSeenDateTime < '%s' limit 1" % threshold)
          logger.info("%s - will step in for processor %d", threading.currentThread().getName(), self.config.processorId)
        except socorro.lib.psycopghelper.SQLDidNotReturnSingleValue:
          logger.debug("%s - no dead processor found", threading.currentThread().getName())
          self.config.processorId = '0'
      if self.config.processorId != '0':  # take over for a specific existing processor
        try:
          processorId = int(self.config.processorId)
        except ValueError:
          raise socorro.lib.ConfigurationManager.OptionError("%s is not a valid option for processorId" % self.config.processorId)
        try:
          logger.info("%s - stepping in for processor %d", threading.currentThread().getName(), processorId)
          self.mainThreadCursor.execute("update processors set name = %s, startDateTime = now(), lastSeenDateTime = now() where id = %s", (self.processorName, processorId))
          self.mainThreadCursor.execute("update jobs set starteddatetime = NULL where id in (select id from jobs where starteddatetime is not null and success is null and owner = %s)", (self.config.processorId, ))
          self.processorId = processorId
        except:
          self.mainThreadDatabaseConnection.rollback()
      else:  # be a new processor with a new id
        self.mainThreadCursor.execute("insert into processors (name, startDateTime, lastSeenDateTime) values (%s, now(), now())", (self.processorName,))
        self.processorId = socorro.lib.psycopghelper.singleValueSql(self.mainThreadCursor, "select id from processors where name = '%s'" % (self.processorName,))
        logger.info("%s - initializing as processor %d", threading.currentThread().getName(), self.processorId)
      self.priorityJobsTableName = "priority_jobs_%d" % self.processorId
      self.mainThreadDatabaseConnection.commit()
      try:
        self.mainThreadCursor.execute("create table %s (uuid varchar(50) not null primary key)" % self.priorityJobsTableName)
        self.mainThreadDatabaseConnection.commit()
      except:
        logger.warning("%s - failed in creating priority jobs table for this processor.  Does it already exist?",  threading.currentThread().getName())
        self.mainThreadDatabaseConnection.rollback()
        socorro.lib.util.reportExceptionAndContinue(logger)
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
    self.threadLocalDatabaseConnections = {}
    logger.info("%s - I am processor #%d", threading.currentThread().getName(), self.processorId)
    logger.info("%s -   my priority jobs table is called: '%s'", threading.currentThread().getName(), self.priorityJobsTableName)

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
      self.mainThreadCursor.execute("update processors set lastSeenDateTime = %s where id = %s", (datetime.datetime.now(), self.processorId))
      self.mainThreadDatabaseConnection.commit()
      self.lastCheckInTimestamp = datetime.datetime.now()

  #-----------------------------------------------------------------------------------------------------------------
  def cleanup(self):
    """ clean up before shutdown
    """
    logger.info("%s - waiting for threads to stop", threading.currentThread().getName())
    self.threadManager.waitForCompletion()
    logger.info("%s - all threads stopped", threading.currentThread().getName())

    # we're done - kill all the threads' database connections
    logger.debug("%s - killing thread database connections", threading.currentThread().getName())
    for i, aDatabaseConnection in enumerate(self.threadLocalDatabaseConnections.values()):
      try:
        aDatabaseConnection.rollback()
        aDatabaseConnection.close()
        logger.debug("%s -   connection %d closed", threading.currentThread().getName(), i)
      except psycopg2.InterfaceError:
        logger.debug("%s -   connection %d already closed", threading.currentThread().getName(), i)
      except:
        socorro.lib.util.reportExceptionAndContinue(logger)

    try:
      # force the processor to record a lastSeenDateTime in the distant past so that the monitor will
      # mark it as dead.  The monitor will process its completed jobs and reallocate it unfinished ones.
      logger.debug("%s - unregistering processor", threading.currentThread().getName())
      self.mainThreadCursor.execute("update processors set lastSeenDateTime = '1999-01-01' where id = %s", (self.processorId,))
      self.mainThreadDatabaseConnection.commit()
    except Exception, x:
      logger.critical("%s - could not unregister %d from the database", threading.currentThread().getName(), self.processorId)
      socorro.lib.util.reportExceptionAndContinue(logger)

    try:
      self.mainThreadCursor.execute("drop table %s" % self.priorityJobsTableName)
      self.mainThreadDatabaseConnection.commit()
      self.mainThreadDatabaseConnection.close()
    except psycopg2.Error:
      logger.error("%s - Cannot complete cleanup.  %s may need manual deletion", threading.currentThread().getName(), self.priorityJobsTableName)
      socorro.lib.util.reportExceptionAndContinue(logger)

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
  def submitJobToThreads(self, aJobTuple):
    self.mainThreadCursor.execute("update jobs set startedDateTime = %s where id = %s", (datetime.datetime.now(), aJobTuple[0]))
    self.mainThreadDatabaseConnection.commit()
    logger.info("%s - queuing job %d, %s, %s", threading.currentThread().getName(), aJobTuple[0], aJobTuple[2], aJobTuple[1])
    self.threadManager.newTask(self.processJob, aJobTuple)

  #-----------------------------------------------------------------------------------------------------------------
  def incomingJobStream(self):
    """
       aJobTuple has this form: (jobId, jobUuid, jobPathname, jobPriority) jobPriority is optional
    """
    jobList = {}
    preexistingPriorityJobs = set()
    while (True):
      self.quitCheck()
      self.checkin()
      try:
        lastPriorityCheckTimestamp = datetime.datetime.now()
        self.mainThreadCursor.execute("select uuid from %s" % self.priorityJobsTableName)
        setOfPriorityJobs = preexistingPriorityJobs | set([x[0] for x in self.mainThreadCursor.fetchall()])
        logger.debug("%s - priorityJobs: %s", threading.currentThread().getName(), setOfPriorityJobs)
        if setOfPriorityJobs:
          for aPriorityJobUuid in setOfPriorityJobs:
            try:
              aJobTuple = jobList[aPriorityJobUuid]
              del jobList[aPriorityJobUuid]
              self.mainThreadCursor.execute("delete from %s where uuid = '%s'" % (self.priorityJobsTableName, aPriorityJobUuid))
              self.mainThreadDatabaseConnection.commit()
              logger.debug("%s - incomingJobStream yielding priority from existing job list: %s", threading.currentThread().getName(), aJobTuple[1])
              yield aJobTuple
            except KeyError:
              self.mainThreadCursor.execute("select j.id, j.uuid, j.pathname, j.priority from jobs j where j.uuid = '%s'" % aPriorityJobUuid)
              try:
                try:
                  aJobTuple = self.mainThreadCursor.fetchall()[0]
                finally:
                  self.mainThreadCursor.execute("delete from %s where uuid = '%s'" % (self.priorityJobsTableName, aPriorityJobUuid))
                  self.mainThreadDatabaseConnection.commit()
                logger.debug("%s - incomingJobStream yielding priority from database: %s", threading.currentThread().getName(), aJobTuple[1])
                yield aJobTuple
              except IndexError:
                logger.warning("%s - the priority job %s was never found", threading.currentThread().getName(), aPriorityJobUuid)
                self.mainThreadCursor.execute("delete from %s where uuid = '%s'" % (self.priorityJobsTableName, aPriorityJobUuid))
                self.mainThreadDatabaseConnection.commit()
          continue  # done processing priorities - start the loop again in case there are more priorities
        preexistingPriorityJobs = set()
        if not jobList:
          self.mainThreadCursor.execute("select j.id, j.uuid, j.pathname, j.priority from jobs j where j.owner = %d and j.starteddatetime is null order by j.priority desc limit %d" % (self.processorId, self.config.batchJobLimit))
          for aJobTuple in self.mainThreadCursor.fetchall():
            jobList[aJobTuple[1]] = aJobTuple
            if aJobTuple[3]:  #check priority
              logger.debug("%s - adding priority job found in database: %s", threading.currentThread().getName(), aJobTuple[1])
              preexistingPriorityJobs.add(aJobTuple[1])
          if not jobList:
            logger.info("%s - no jobs to do - sleeping %d seconds", threading.currentThread().getName(), self.config.processorLoopTime)
            self.responsiveSleep(self.config.processorLoopTime)
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
        #get a job
        for aJobTuple in self.incomingJobStream():
          self.quitCheck()
          logger.debug("%s - start got: %s", threading.currentThread().getName(), aJobTuple[1])
          self.submitJobToThreads(aJobTuple)
      except KeyboardInterrupt:
        logger.info("%s - quit request detected", threading.currentThread().getName())
        self.mainThreadDatabaseConnection.rollback()
        self.quit = True
        break
    self.cleanup()

  #-----------------------------------------------------------------------------------------------------------------
  def processJob (self, jobTuple):
    """ This function is run only by a worker thread.
        Given a job, fetch a thread local database connection and the json document.  Use these
        to create the record in the 'reports' table, then start the analysis of the dump file.

        input parameters:
          jobTuple: a tuple containing three items: the jobId (the primary key from the jobs table), the
              jobUuid (a unique string with the json file basename minus the extension) and the jobPathname
              (a string with the full pathname of the json file that defines the job)
    """
    try:
      if self.quit: return
      try:
        threadLocalDatabaseConnection = self.threadLocalDatabaseConnections[threading.currentThread().getName()]
      except KeyError:
        try:
          logger.info("%s - connecting to database", threading.currentThread().getName())
          threadLocalDatabaseConnection = self.threadLocalDatabaseConnections[threading.currentThread().getName()] = psycopg2.connect(self.config.databaseDSN)
        except:
          self.quit = True
          logger.critical("%s - cannot connect to the database", threading.currentThread().getName())
          socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a database connection
    except (KeyboardInterrupt, SystemExit):
      logger.info("%s - quit request detected", threading.currentThread().getName())
      self.quit = True
      return

    try:
      threadLocalCursor = threadLocalDatabaseConnection.cursor()
      threadLocalCursor.execute("select 1")
    except psycopg2.OperationalError:
      # did the connection time out?
      logger.info("%s - trying to re-establish a database connection", threading.currentThread().getName())
      try:
        threadLocalDatabaseConnection = self.threadLocalDatabaseConnections[threading.currentThread().getName()] = psycopg2.connect(self.config.databaseDSN)
        threadLocalCursor = threadLocalDatabaseConnection.cursor()
        threadLocalCursor.execute("select 1")
      except psycopg2.OperationalError:
        logger.critical("%s - something's gone horribly wrong with the database connection", threading.currentThread().getName())
        self.quit = True
        socorro.lib.util.reportExceptionAndAbort(logger)


    try:
      jobId, jobUuid, jobPathname, jobPriority = jobTuple
      logger.info("%s - starting job: %s, %s", threading.currentThread().getName(), jobId, jobUuid)
      threadLocalCursor = threadLocalDatabaseConnection.cursor()
      startedDateTime = datetime.datetime.now()
      threadLocalCursor.execute("update jobs set startedDateTime = %s where id = %s", (startedDateTime, jobId))
      threadLocalDatabaseConnection.commit()

      jsonFile = open(jobPathname)
      try:
        jsonDocument = simplejson.load(jsonFile)
      finally:
        jsonFile.close()
      reportId = self.createReport(threadLocalCursor, jobUuid, jsonDocument, jobPathname)
      threadLocalDatabaseConnection.commit()
      dumpfilePathname = "%s%s" % (jobPathname[:-len(self.config.jsonFileSuffix)], self.config.dumpFileSuffix)
      truncated = self.doBreakpadStackDumpAnalysis(reportId, jobUuid, dumpfilePathname, threadLocalCursor)
      self.quitCheck()
      #finished a job - cleanup
      threadLocalCursor.execute("update jobs set completedDateTime = %s, success = True where id = %s", (datetime.datetime.now(), jobId))
      threadLocalCursor.execute("update reports set startedDateTime = %s, completedDateTime = %s, success = True, truncated = %s where id = %s", (startedDateTime, datetime.datetime.now(), truncated, reportId))
      #self.updateRegistrationNoCommit(threadLocalCursor)
      threadLocalDatabaseConnection.commit()
      logger.info("%s - succeeded and committed: %s, %s", threading.currentThread().getName(), jobId, jobUuid)
    except (KeyboardInterrupt, SystemExit):
      logger.info("%s - quit request detected", threading.currentThread().getName())
      self.quit = True
      try:
        logger.info("%s - abandoning job with rollback: %s, %s", threading.currentThread().getName(), jobId, jobUuid)
        threadLocalDatabaseConnection.rollback()
        threadLocalDatabaseConnection.close()
      except:
        pass
    except DuplicateEntryException, x:
      logger.warning("%s - duplicate entry: %s", threading.currentThread().getName(), jobUuid)
    except psycopg2.OperationalError:
      logger.critical("%s - something's gone horribly wrong with the database connection", threading.currentThread().getName())
      self.quit = True
      socorro.lib.util.reportExceptionAndAbort(logger)
    except Exception, x:
      socorro.lib.util.reportExceptionAndContinue(logger)
      threadLocalDatabaseConnection.rollback()
      message = "%s:%s" % (type(x), str(x))
      threadLocalCursor.execute("update jobs set completedDateTime = %s, success = False, message = %s where id = %s", (datetime.datetime.now(), message, jobId))
      try:
        threadLocalCursor.execute("update reports set startedDateTime = %s, completedDateTime = %s, success = False, message = %s where id = %s", (startedDateTime, datetime.datetime.now(), message, reportId))
      except:
        pass
      threadLocalDatabaseConnection.commit()

  #-----------------------------------------------------------------------------------------------------------------
  def createReport(self, threadLocalCursor, uuid, jsonDocument, jobPathname):
    """ This function is run only by a worker thread.
        Create the record for the current job in the 'reports' table

        input parameters:
          threadLocalCursor: a database cursor for exclusive use by the calling thread
          uuid: the unique id identifying the job - corresponds with the uuid column in the 'jobs'
              and the 'reports' tables
          jsonDocument: an object with a dictionary interface for fetching the components of
              the json document
          jobPathname:  the complete pathname for the json document
    """
    try:
      product = socorro.lib.util.limitStringOrNone(jsonDocument['ProductName'], 30)
      version = socorro.lib.util.limitStringOrNone(jsonDocument['Version'], 16)
      build = socorro.lib.util.limitStringOrNone(jsonDocument['BuildID'], 30)
    except KeyError, x:
      raise Exception("Json file error: missing or improperly formated '%s' in %s" % (x, jobPathname))
    url = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'URL', 255)
    email = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Email', 100)
    user_id = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'UserID',  50)
    comments = socorro.lib.util.lookupLimitedStringOrNone(jsonDocument, 'Comments', 500)
    crash_time = None
    install_age = None
    uptime = 0
    report_date = datetime.datetime.now()
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
    #if 'CrashTime' in jsonDocument and timePattern.match(str(jsonDocument['CrashTime'])) and 'InstallTime' in jsonDocument and timePattern.match(str(jsonDocument['InstallTime'])):
    #  try:
    #    crash_time = int(jsonDocument['CrashTime'])
    #    report_date = datetime.datetime.fromtimestamp(crash_time, utctz)
    #    install_age = crash_time - int(jsonDocument['InstallTime'])
    #    if 'StartupTime' in jsonDocument and timePattern.match(str(jsonDocument['StartupTime'])) and crash_time >= int(jsonDocument['StartupTime']):
    #      uptime = crash_time - int(jsonDocument['StartupTime'])
    #  except (ValueError):
    #    print >>statusReportStream, "no 'uptime',  'crash_time' or 'install_age' calculated in %s" % jobPathname
    #    socorro.lib.util.reportExceptionAndContinue()
    #elif 'timestamp' in jsonDocument and timePattern.match(str(jsonDocument['timestamp'])):
    #  try:
    #    report_date = datetime.datetime.fromtimestamp(jsonDocument['timestamp'], utctz)
    #  except (ValueError):
    #    print >>statusReportStream, "no 'report_date' calculated in %s" % jobPathname
    #    socorro.lib.util.reportExceptionAndContinue()
    build_date = None
    try:
      y, m, d, h = [int(x) for x in Processor.buildDatePattern.match(str(jsonDocument['BuildID'])).groups()]
      #(y, m, d, h) = map(int, Processor.buildDatePattern.match(str(jsonDocument['BuildID'])).groups())
      build_date = datetime.datetime(y, m, d, h)
    except (AttributeError, ValueError, KeyError):
        logger.warning("%s - no 'build_date' calculated in %s", threading.currentThread().getName(), jobPathname)
        socorro.lib.util.reportExceptionAndContinue(logger, logging.WARNING)
    try:
      last_crash = int(jsonDocument['SecondsSinceLastCrash'])
    except:
      last_crash = None
    def insertReport():
      threadLocalCursor.execute ("""insert into reports
                                    (id,                        uuid,      date,         product,      version,      build,       url,       install_age, last_crash, uptime, email,       build_date, user_id,      comments) values
                                    (nextval('seq_reports_id'), %s,        %s,           %s,           %s,           %s,          %s,        %s,          %s,         %s,     %s,          %s,         %s,           %s)""",
                                    (                           uuid, report_date,  product, version, build, url, install_age, last_crash, uptime, email, build_date, user_id, comments))
    try:
      insertReport()
    except psycopg2.IntegrityError:
      logger.debug("%s - %s: this report already exists",  threading.currentThread().getName(), uuid)
      threadLocalCursor.connection.rollback()
      threadLocalCursor.execute("select success from reports where uuid = %s", (uuid,))
      previousTrialWasSuccessful = threadLocalCursor.fetchall()[0][0]
      if previousTrialWasSuccessful:
        raise DuplicateEntryException(uuid)
      threadLocalCursor.execute("delete from reports where uuid = %s", (uuid,))
      insertReport()
    threadLocalCursor.execute("select id from reports where uuid = %s", (uuid,))
    reportId = threadLocalCursor.fetchall()[0][0]
    return reportId

  #-----------------------------------------------------------------------------------------------------------------
  def doBreakpadStackDumpAnalysis (self, reportId, uuid, dumpfilePathname, databaseCursor):
    """ This function is run only by a worker thread.
        This function must be overriden in a subclass - this method will invoke the breakpad_stackwalk process
        (if necessary) and then do the anaylsis of the output
    """
    raise Exception("No breakpad_stackwalk invocation method specified")


