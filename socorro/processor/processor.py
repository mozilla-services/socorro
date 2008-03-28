#! /usr/bin/env python

import psycopg2

import time
import datetime
import os
import os.path
import threading
import re

import signal

import socorro.lib.config as config
import socorro.lib.util
import socorro.lib.threadlib

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
        self.stopProcessing: a boolean used for internal communication between threads.  Since any
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
  def __init__ (self):
    """
    """
    super(Processor, self).__init__()
    
    signal.signal(signal.SIGTERM, Processor.respondToSIGTERM)
    
    self.stopProcessing = False
    
    try:
      self.mainThreadDatabaseConnection = psycopg2.connect(config.processorDatabaseDSN)
      self.mainThreadCursor = self.mainThreadDatabaseConnection.cursor()
    except:
      socorro.lib.util.reportExceptionAndAbort() # can't continue without a database connection
      
    #register self with the processors table in the database
    try:
      processorName = "%s:%d" % (os.uname()[1], os.getpid())
      self.mainThreadCursor.execute("insert into processors (name, startDateTime, lastSeenDateTime) values (%s, now(), now())", (processorName,))
      self.mainThreadCursor.execute("select id from processors where name = %s", (processorName,))
      self.processorId = self.mainThreadCursor.fetchall()[0][0]
      self.mainThreadDatabaseConnection.commit()
    except:
      socorro.lib.util.reportExceptionAndAbort() # can't continue without a registration
      
    self.getNextJobSQL = "select j.id, j.pathname, j.uuid from jobs j where j.owner = %d and startedDateTime is null order by priority desc, queuedDateTime asc limit 1" % self.processorId
    
    # start the thread manager with the number of threads specified in the configuration.  The second parameter controls the size
    # of the internal task queue within the thread manager.  It is constrained so that the queue remains starved.  This means that tasks
    # remain queued in the database until the last minute.  This allows some external process to change the priority of a job by changing
    # the 'priority' column of the 'jobs' table for the particular record in the database.  If the threadManager were allowed to suck all
    # the pending jobs from the database, then the job priority could not be changed by an external process.
    self.threadManager = socorro.lib.threadlib.TaskManager(config.processorNumberOfThreads, config.processorNumberOfThreads * 2)
    self.threadLocalDatabaseConnections = {}
    
  #-----------------------------------------------------------------------------------------------------------------
  @staticmethod
  def respondToSIGTERM(signalNumber, frame):
    """ these classes are instrumented to respond to a KeyboardInterrupt by cleanly shutting down.
        This function, when given as a handler to for a SIGTERM event, will make the program respond
        to a SIGTERM as neatly as it responds to ^C.
    """
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
  def updateRegistrationNoCommit(self, aCursor):
    """ a processor must keep its database registration current.  If a processor has not updated its
        record in the database in the interval specified in as config.processorCheckInTime, the 
        monitor will consider it to be expired.  The monitor will stop assigning jobs to it and reallocate
        its unfinished jobs to other processors.
    """
    aCursor.execute("update processors set lastSeenDateTime = %s where id = %s", (datetime.datetime.now(), self.processorId))
    
  #-----------------------------------------------------------------------------------------------------------------
  def start(self):
    """ Run by the main thread, this function fetches jobs from the database one at a time
        puts them on the task queue.  If there are no jobs to do, it sleeps before trying again.
        If it detects that some thread has received a Keyboard Interrupt, it stops its looping,
        waits for the threads to stop and then closes all the database connections.
    """
    sqlErrorCounter = 0
    while (True):
      try:
        if self.stopProcessing: raise KeyboardInterrupt
        #get a job
        try:
          self.mainThreadCursor.execute(self.getNextJobSQL)
          jobId, jobPathname, jobUuid = self.mainThreadCursor.fetchall()[0]
        except psycopg2.Error:
          socorro.lib.util.reportExceptionAndContinue()
          sqlErrorCounter += 1
          if sqlErrorCounter == 10:
            print >>config.errorReportStream, "%s: too many server errors - quitting" % datetime.datetime.now()
            self.stopProcessing = True
            break
          continue
        except IndexError:
          print >>config.statusReportStream, "%s: no jobs to do.  Waiting %s seconds" % (datetime.datetime.now(), config.processorLoopTime)
          time.sleep(config.processorLoopTime)
          #self.updateRegistrationNoCommit(self.mainThreadCursor)
          #self.mainThreadDatabaseConnection.commit()
          continue
        sqlErrorCounter = 0
        
        self.mainThreadCursor.execute("update jobs set startedDateTime = %s where id = %s", (datetime.datetime.now(), jobId))
        self.mainThreadDatabaseConnection.commit()
        print >>config.statusReportStream, "%s queuing job %d, %s, %s" % (datetime.datetime.now(), jobId, jobUuid, jobPathname)
        self.threadManager.newTask(self.processJob, (jobId, jobUuid, jobPathname))
        
      except KeyboardInterrupt:
        print >>config.statusReportStream, "%s quit request detected" % datetime.datetime.now()
        self.mainThreadDatabaseConnection.rollback()
        self.stopProcessing = True
        break
      
    print >>config.statusReportStream, "%s waiting for threads to stop" % datetime.datetime.now()
    self.threadManager.waitForCompletion()
    
    # we're done - kill all the threads' database connections
    for aDatabaseConnection in self.threadLocalDatabaseConnections.values():
      try:
        aDatabaseConnection.rollback()
        aDatabaseConnection.close()
      except:
        pass
    
    try:
      # force the processor to record a lastSeenDateTime in the distant past so that the monitor will
      # mark it as dead.  The monitor will process its completed jobs and reallocate it unfinished ones.
      self.mainThreadCursor.execute("update processors set lastSeenDateTime = '1999-01-01' where id = %s", (self.processorId,))
      self.mainThreadDatabaseConnection.commit()
    except Exception, x:
      print >>config.errorReportStream, type(x), x 
      print >>config.errorReportStream, "%s could not unregister %d from the database" % (datetime.datetime.now(), self.processorId)
  
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
      if self.stopProcessing: return
      try:
        threadLocalDatabaseConnection = self.threadLocalDatabaseConnections[threading.currentThread().getName()]
      except KeyError:
        try:
          threadLocalDatabaseConnection = self.threadLocalDatabaseConnections[threading.currentThread().getName()] = psycopg2.connect(config.processorDatabaseDSN)
        except:
          socorro.lib.util.reportExceptionAndAbort() # can't continue without a database connection
    except KeyboardInterrupt:
      self.stopProcessing = True
      return
    try:
      jobId, jobUuid, jobPathname = jobTuple
      print "%s starting job: %s, %s" % (datetime.datetime.now(), jobId, jobUuid)
      threadLocalCursor = threadLocalDatabaseConnection.cursor()
      
      jsonFile = open(jobPathname)
      try:
        jsonDocument = simplejson.load(jsonFile)
      finally:
        jsonFile.close()
      reportId = self.createReport(threadLocalCursor, jobUuid, jsonDocument, jobPathname)
      dumpfilePathname = "%s%s" % (jobPathname[:-len(config.jsonFileSuffix)], config.dumpFileSuffix)
      self.doBreakpadStackDumpAnalysis(reportId, jobUuid, dumpfilePathname, threadLocalCursor)
      if self.stopProcessing: raise KeyboardInterrupt
      #finished a job - cleanup
      threadLocalCursor.execute("update jobs set completedDateTime = %s, success = True where id = %s", (datetime.datetime.now(), jobId))
      self.updateRegistrationNoCommit(threadLocalCursor)
      threadLocalDatabaseConnection.commit()
    except KeyboardInterrupt:
      self.stopProcessing = True
      try:
        threadLocalDatabaseConnection.rollback()
        threadLocalDatabaseConnection.close()
      except:
        pass
    except Exception, x:
      threadLocalDatabaseConnection.rollback()
      threadLocalCursor.execute("update jobs set completedDateTime = %s, success = False, message = %s where id = %s", (datetime.datetime.now(), "%s:%s" % (type(x), str(x)), jobId))
      threadLocalDatabaseConnection.commit()
      socorro.lib.util.reportExceptionAndContinue()

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
        print >>statusReportStream, "no 'report_date' calculated in %s" % jobPathname
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
        print >>statusReportStream, "no 'build_date' calculated in %s" % jobPathname
        socorro.lib.util.reportExceptionAndContinue()
    try:
      last_crash = int(jsonDocument['SecondsSinceLastCrash'])
    except:
      last_crash = None

    threadLocalCursor.execute ("""insert into reports
                                  (id,                        uuid,      date,         product,      version,      build,       url,       install_age, last_crash, uptime, email,       build_date, user_id,      comments) values
                                  (nextval('seq_reports_id'), %s,        %s,           %s,           %s,           %s,          %s,        %s,          %s,         %s,     %s,          %s,         %s,           %s)""",
                                  (                           uuid, report_date,  product, version, build, url, install_age, last_crash, uptime, email, build_date, user_id, comments))
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

  
if __name__ == '__main__':    
  print >>config.statusReportStream, "This file is not meant to be run as a standalone program."
