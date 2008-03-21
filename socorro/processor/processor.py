#! /usr/bin/env python

import psycopg2

import time
import datetime
import os
import os.path
import threading
import re

import socorro.lib.config as config
import socorro.lib.util
import socorro.lib.threadlib

import simplejson

buildDatePattern = re.compile('^(\\d{4})(\\d{2})(\\d{2})(\\d{2})')
buildPattern = re.compile('^\\d{10}')
timePattern = re.compile('^\\d+.?\\d+$')
fixupSpace = re.compile(r' (?=[\*&,])')
fixupComma = re.compile(r'(?<=,)(?! )')
filename_re = re.compile('[/\\\\]([^/\\\\]+)$')

class UTC(datetime.tzinfo):
  def __init__(self):
    super(UTC, self).__init__(self)
  
  ZERO = datetime.timedelta(0)
 
  def utcoffset(self, dt):
    return UTC.ZERO

  def tzname(self, dt):
    return "UTC"

  def dst(self, dt):
    return UTC.ZERO

utctz = UTC()

def fixupJsonPathname(pathname):
  return pathname

def checkJsonReportValidity(json, pathname):
  """Given a json dict passed from simplejson, we need to verify that required
  fields exist.  If they don't, we should throw away the dump and continue.
  Method returns a boolean value -- true if valid, false if not."""

  if 'BuildID' not in json or not buildPattern.match(json['BuildID']):
    raise Exception("Json file error: missing or improperly formated 'BuildID' in %s" % pathname)

  if 'ProductName' not in json:
    raise Exception("Json file error: missing 'ProductName' in %s" % pathname)

  if 'Version' not in json:
    raise Exception("Json file error: missing 'Version' in %s" % pathname)

def make_signature(module_name, function, source, source_line, instruction):
  if function is not None:
    # Remove spaces before all stars, ampersands, and commas
    function = re.sub(fixupSpace, '', function)

    # Ensure a space after commas
    function = re.sub(fixupComma, ' ', function)
    return function

  if source is not None and source_line is not None:
    filename = filename_re.search(source)
    if filename is not None:
      source = filename.group(1)

    return '%s#%s' % (source, source_line)

  if module_name is not None:
    return '%s@%s' % (module_name, instruction)

  return '@%s' % instruction

class Processor(object):
  def __init__ (self):
    super(Processor, self).__init__()
    try:
      self.databaseConnection = psycopg2.connect(config.processorDatabaseDSN)
      self.aCursor = self.databaseConnection.cursor()
    except:
      socorro.lib.util.reportExceptionAndAbort() # can't continue without a database connection    
    #register self with the processors table in the database
    try:
      processorName = "%s:%d" % (os.uname()[1], os.getpid())
      self.aCursor.execute("insert into processors (name, startDateTime, lastSeenDateTime) values (%s, now(), now())", (processorName,))
      self.aCursor.execute("select id from processors where name = %s", (processorName,))
      self.processorId = self.aCursor.fetchall()[0][0]
      self.databaseConnection.commit()
    except:
      socorro.lib.util.reportExceptionAndAbort() # can't continue without a registration
      
    self.getNextJobSQL = "select j.id, j.pathname, j.uuid from jobs j where j.owner = %d and startedDateTime is null order by priority desc, queuedDateTime asc limit 1" % self.processorId
    
    self.threadManager = socorro.lib.threadlib.TaskManager(config.processorNumberOfThreads)
    self.threadLocalDatabaseConnections = {}
    
    self.stopProcessing = False
    
  def start(self):
    #loop forever getting and processing jobs
    sqlErrorCounter = 0
    while (True):
      try:
        #get a job
        if self.stopProcessing: raise KeyboardInterrupt
        try:
          self.aCursor.execute(self.getNextJobSQL)
          jobId, jobPathname, jobUuid = self.aCursor.fetchall()[0]
        except psycopg2.Error:
          socorro.lib.util.reportExceptionAndContinue()
          sqlErrorCounter += 1
          if sqlErrorCounter == 10:
            print >>config.errorReportStream, "%s: too many server errors - quitting" % datetime.datetime.now()
            self.stopProcessing = True
            break
          continue
        except IndexError:
          #no jobs to do
          print >>config.statusReportStream, "%s: no jobs to do.  Waiting %s seconds" % (datetime.datetime.now(), config.processorLoopTime)
          time.sleep(config.processorLoopTime)
          continue
        sqlErrorCounter = 0
        
        self.aCursor.execute("update jobs set startedDateTime = %s where id = %s", (datetime.datetime.now(), jobId))
        self.databaseConnection.commit()
        print >>config.statusReportStream, "%s queuing job %d, %s, %s" % (datetime.datetime.now(), jobId, jobUuid, jobPathname)
        self.threadManager.newTask(self.processJob, (jobId, jobUuid, jobPathname))
        
      except KeyboardInterrupt:
        print >>config.statusReportStream, "%s keyboard interrupt - waiting for threads to stop" % datetime.datetime.now()
        self.stopProcessing = True
        break
    self.threadManager.waitForCompletion()
    
    for aDatabaseConnection in self.threadLocalDatabaseConnections.values():
      aDatabaseConnection.rollback()
      aDatabaseConnection.close()
  
  def processJob (self, jobTuple):
    try:
      threadLocalDatabaseConnection = self.threadLocalDatabaseConnections[threading.currentThread().getName()]
    except KeyError:
      try:
        threadLocalDatabaseConnection = self.threadLocalDatabaseConnections[threading.currentThread().getName()] = psycopg2.connect(config.processorDatabaseDSN)
      except:
        socorro.lib.util.reportExceptionAndAbort() # can't continue without a database connection
    try:
      jobId, jobUuid, jobPathname = jobTuple
      print "%s starting job: %s, %s" % (datetime.datetime.now(), jobId, jobUuid)
      threadLocalCursor = threadLocalDatabaseConnection.cursor()
      
      jsonFile = open(jobPathname)
      try:
        jsonDocument = simplejson.load(jsonFile)
      finally:
        jsonFile.close()
      checkJsonReportValidity(jsonDocument, jobPathname)
      reportId = self.createReport(threadLocalCursor, jobUuid, jsonDocument, jobPathname)
      dumpfilePathname = "%s%s" % (jobPathname[:-len(config.jsonFileSuffix)], config.dumpFileSuffix)
      self.doBreakpadStackDumpAnalysis(reportId, jobUuid, dumpfilePathname, threadLocalCursor)
      #finished a job - cleanup
      threadLocalCursor.execute("update jobs set completedDateTime = %s, success = True where id = %s", (datetime.datetime.now(), jobId))
      threadLocalCursor.execute("update processors set lastSeenDateTime = %s where id = %s", (datetime.datetime.now(), self.processorId))
      if self.stopProcessing: raise KeyboardInterrupt
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

  def createReport(self, threadLocalCursor, uuid, jsonDocument, jobPathname):
    crash_time = None
    install_age = None
    uptime = 0 
    report_date = datetime.datetime.now()
    
    # this code needs refactoring - but I'm not going to do it until there is more leasure time...
    # in the original version, ValueError exceptions were being caught and ignored - why?
    if 'CrashTime' in jsonDocument and timePattern.match(str(jsonDocument['CrashTime'])) and 'InstallTime' in jsonDocument and timePattern.match(str(jsonDocument['InstallTime'])):
      try:
        crash_time = int(jsonDocument['CrashTime'])
        report_date = datetime.datetime.fromtimestamp(crash_time, utctz)
        install_age = crash_time - int(jsonDocument['InstallTime'])
        if 'StartupTime' in jsonDocument and timePattern.match(str(jsonDocument['StartupTime'])) and crash_time >= int(jsonDocument['StartupTime']):
          uptime = crash_time - int(jsonDocument['StartupTime'])
      except (ValueError):
        print >>statusReportStream, "no 'uptime',  'crash_time' or 'install_age' calculated in %s" % jobPathname
        socorro.lib.util.reportExceptionAndContinue()
    elif 'timestamp' in jsonDocument and timePattern.match(str(jsonDocument['timestamp'])):
      try:
        report_date = datetime.datetime.fromtimestamp(jsonDocument['timestamp'], utctz)
      except (ValueError):
        print >>statusReportStream, "no 'report_date' calculated in %s" % jobPathname
        socorro.lib.util.reportExceptionAndContinue()
    build_date = None
    try:
      (y, m, d, h) = map(int, buildDatePattern.match(str(jsonDocument['BuildID'])).groups())
      build_date = datetime.datetime(y, m, d, h)
    except (AttributeError, ValueError, KeyError):
        print >>statusReportStream, "no 'build_date' calculated in %s" % jobPathname
        socorro.lib.util.reportExceptionAndContinue()

    last_crash = None
    if 'SecondsSinceLastCrash' in jsonDocument and timePattern.match(str(jsonDocument['SecondsSinceLastCrash'])):
      last_crash = int(jsonDocument['SecondsSinceLastCrash'])
      
    product = jsonDocument.get('ProductName', None)
    version = jsonDocument.get('Version', None)
    build = jsonDocument.get('BuildID', None)
    url = jsonDocument.get('URL', None)
    email = jsonDocument.get('Email', None)
    user_id = jsonDocument.get('UserID', None)
    comments = jsonDocument.get('Comments', None)

    threadLocalCursor.execute ("""insert into reports
                                  (id,                        uuid, date,         product, version, build, url, install_age, last_crash, uptime, email, build_date, user_id, comments) values
                                  (nextval('seq_reports_id'), %s,   %s,           %s,      %s,      %s,    %s,  %s,          %s,         %s,     %s,    %s,         %s,      %s)""",
                                  (                           uuid, report_date,  product, version, build, url, install_age, last_crash, uptime, email, build_date, user_id, comments))
    threadLocalCursor.execute("select id from reports where uuid = %s", (uuid,))
    reportId = threadLocalCursor.fetchall()[0][0]
    return reportId

  def doBreakpadStackDumpAnalysis (self, reportId, uuid, dumpfilePathname, databaseCursor):
    raise Exception("No breakpad_stackwalk invocation method specified")
   
if __name__ == '__main__':    
  p = Processor()
  p.start()
  print >>config.statusReportStream, "Done."
