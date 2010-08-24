import datetime
from operator import itemgetter
import logging
import os
import os.path
import re
import signal
import threading
import time
import itertools
import collections
import Queue as queue
import urllib
import urllib2
import socket

import web

logger = logging.getLogger("processor")

import socorro.lib.util as sutil
import socorro.lib.threadlib as thr
import socorro.lib.ooid as ooidm
import socorro.lib.datetimeutil as sdt
import socorro.storage.crashstorage as cstore
import socorro.storage.hbaseClient as hbc
import socorro.webapi.webapiService as webapi
import socorro.webapi.classPartial as cpart
import socorro.registrar.registrar as sreg
import socorro.lib.stats as stats
import socorro.webapi.webapp as sweb

#===============================================================================
class ProcessorBaseService(webapi.JsonServiceBase):
  #-----------------------------------------------------------------------------
  def __init__(self, context, aProcessor):
    super(ProcessorBaseService, self).__init__(context)
    self.processor = aProcessor

#===============================================================================
class Hello(ProcessorBaseService):
  #-----------------------------------------------------------------------------
  def __init__(self, context, aProcessor):
    super(Hello, self).__init__(context, aProcessor)
  #-----------------------------------------------------------------------------
  "/hello"
  uri = '/hello'
  #-----------------------------------------------------------------------------
  def get(self, *args):
    return "hello"

#===============================================================================
class NameService(ProcessorBaseService):
  #-----------------------------------------------------------------------------
  def __init__(self, context, aProcessor):
    super(NameService, self).__init__(context, aProcessor)
  #-----------------------------------------------------------------------------
  uri = '/name'
  #-----------------------------------------------------------------------------
  def get(self, *args):
    return self.processor.hostname

#=================================================================================================================
class Test(ProcessorBaseService):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, context, aProcessor):
    super(Test, self).__init__(context, aProcessor)
  #-----------------------------------------------------------------------------------------------------------------
  "/test/PROPERTYNAME"
  uri = '/test/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    #self.context.logger.debug('in Test with %s', str(args))
    convertedArgs = webapi.typeConversion([str], args)
    parameters = sutil.DotDict(zip(['attributeName'], convertedArgs))
    return parameters.attributeName

#=================================================================================================================
class ProcessorOoidService(ProcessorBaseService):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, context, aProcessor):
    super(ProcessorOoidService, self).__init__(context, aProcessor)
  #-----------------------------------------------------------------------------------------------------------------
  uri = '/201006/process/ooid'
  #-----------------------------------------------------------------------------------------------------------------
  def post(self):
    data = web.input()
    ooid = data['ooid']
    self.context.logger.debug('ProcessorOoidService request for %s', ooid)
    self.processor.queueOoid(ooid)
    return self.processor.hostname


#=================================================================================================================
class ProcessorPriorityOoidService(ProcessorBaseService):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, context, aProcessor):
    super(ProcessorPriorityOoidService, self).__init__(context, aProcessor)
  #-----------------------------------------------------------------------------------------------------------------
  uri = '/201006/priority/process/ooid'
  #-----------------------------------------------------------------------------------------------------------------
  def post(self):
    data = web.input()
    ooid = data['ooid']
    self.context.logger.debug('ProcessorPriorityOoidService request for %s', ooid)
    self.processor.queuePriorityOoid(ooid)
    return self.processor.hostname

#=================================================================================================================
class ProcessorOoidBenchmarkedService(ProcessorOoidService):
  import time
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, context, aProcessor):
    super(ProcessorOoidBenchmarkedService, self).__init__(context, aProcessor)
  #-----------------------------------------------------------------------------------------------------------------
  def POST(self):
    t = time.time()
    ProcessorOoidService.POST(self)
    dt = time.time() - t
    self.logger.debug('ProcessorOoidBenchmarkedService: %f', dt)

#=================================================================================================================
class ProcessorServicesQuery(ProcessorBaseService):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, context, aProcessor):
    super(ProcessorServicesQuery, self).__init__(context, aProcessor)
  #-----------------------------------------------------------------------------------------------------------------
  uri = '/services'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    return dict(((x.__name__, x.uri) for x in self.processor.webServicesClassList))

#=================================================================================================================
class ProcessorStats(ProcessorBaseService):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, context, aProcessor):
    super(ProcessorStats, self).__init__(context, aProcessor)
  #-----------------------------------------------------------------------------------------------------------------
  uri = '/201007/stats/(.*)'
  #uriArgNames = ['statName']
  #uriArgTypes = [str]
  #uriDoc = "provides data for the given stat name or all if argument is 'all'"
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    if args[0] == 'all':
      returnValue = dict((name, counterPool.read()) for name, counterPool in
                  self.processor.statsPools.iteritems())
    else:
      try:
        returnValue = self.processor.statsPools[args[0]].read()
      except KeyError:
        raise web.notfound()
    return webapi.sanitizeForJson(returnValue)

#=================================================================================================================
class ProcessorTimeAccumulation(ProcessorBaseService):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, context, aProcessor):
    super(ProcessorTimeAccumulation, self).__init__(context, aProcessor)
  #-----------------------------------------------------------------------------------------------------------------
  uri = '/201008/process/time/accumulation'
  #uriArgNames = []
  #uriArgTypes = []
  #uriDoc = "a tuple of (count, durationsum) for jobs"
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    try:
      returnValue = self.processor.statsPools['processTime'].sumDurations()
    except KeyError:
      raise web.notfound()
    return webapi.sanitizeForJson(returnValue)

#=================================================================================================================
class ProcessorIntrospectionService(ProcessorBaseService):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, context, aProcessor):
    super(ProcessorIntrospectionService, self).__init__(context, aProcessor)
  #-----------------------------------------------------------------------------------------------------------------
  uri = '/201006/processor/(.*)'
  #-----------------------------------------------------------------------------------------------------------------
  def get(self, *args):
    #self.context.logger.debug('in ProcessorIntrospectionService with %s', str(args))
    convertedArgs = webapi.typeConversion([str], args)
    parameters = sutil.DotDict(zip(['attributeName'], convertedArgs))
    processorAttribute = self.processor.__getattribute__(parameters.attributeName)
    if isinstance(processorAttribute, collections.Callable):
      return webapi.sanitizeForJson(processorAttribute())
    return webapi.sanitizeForJson(processorAttribute)
  #-----------------------------------------------------------------------------------------------------------------
  #@staticmethod
  #def sanitizeForJson(something):
    #if type(something) in [int, str, float]:
      #return something
    #if isinstance(something, collections.Mapping):
      #return dict((k, ProcessorIntrospectionService.sanitizeForJson(v)) for k, v in something.iteritems())
    #if isinstance(something, collections.Iterable):
      #return [ProcessorIntrospectionService.sanitizeForJson(x) for x in something]
    #return str(something)

#=================================================================================================================
class DuplicateEntryException(Exception):
  pass

#=================================================================================================================
class ProcessorCannotBeReUsedException(Exception):
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

  _config_requirements = ("hbaseHost",
                          "hbasePort",
                          "hbaseTimeout",
                          "hbaseRetry",
                          "hbaseRetryDelay",
                          "serverIPAddress",
                          "serverPort",
                          "processorCheckInTime",
                          "processorCheckInFrequency",
                          "registrationHostPort",
                          "registrationTimeout",
                          "generatePipeDump",
                          "generateJDump",
                          "processedToFailedRatioThreshold",
                          "numberOfThreads",
                          "stackwalkCommandLine",
                          "threadFrameThreshold",
                          "threadTailFrameThreshold",
                          "processorLoopTime",
                          "irrelevantSignatureRegEx",
                          "prefixSignatureRegEx",
                          "collectAddon",
                          "collectCrashProcess",
                          "signatureSentinels",
                          "signaturesWithLineNumbersRegEx",
                          "knownFlashIdentifiers",
                          "syslogHost",
                          "syslogPort",
                          "syslogFacilityString",
                          "syslogLineFormatString",
                          "syslogErrorLoggingLevel",
                          "stderrLineFormatString",
                          "stderrErrorLoggingLevel",
                         )

  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config):
    """
    """
    super(Processor, self).__init__()

    self.logger = config.logger = logger

    for x in Processor._config_requirements:
      assert x in config, '%s missing from configuration' % x

    self.crashStorePool = cstore.CrashStoragePool(config)

    self.processorLoopTime = config.processorLoopTime.seconds
    self.config = config
    self.quit = False
    signal.signal(signal.SIGTERM, Processor.respondToSIGTERM)
    signal.signal(signal.SIGHUP, Processor.respondToSIGTERM)
    self.irrelevantSignatureRegEx = re.compile(self.config.irrelevantSignatureRegEx)
    self.prefixSignatureRegEx = re.compile(self.config.prefixSignatureRegEx)
    self.signaturesWithLineNumbersRegEx = re.compile(self.config.signaturesWithLineNumbersRegEx)

    self.hostname = '%s:%s' % (socket.gethostname(), config.serverPort)

    # start the thread manager with the number of threads specified in the configuration.  The second parameter controls the size
    # of the internal task queue within the thread manager.  It is constrained so that the queue remains starved.  This means that tasks
    # remain queued in the database until the last minute.  This allows some external process to change the priority of a job by changing
    # the 'priority' column of the 'jobs' table for the particular record in the database.  If the threadManager were allowed to suck all
    # the pending jobs from the database, then the job priority could not be changed by an external process.
    logger.info("starting worker threads")
    self.threadManager = thr.TaskManager(self.config.numberOfThreads,
                                         self.config.numberOfThreads * 2,
                                         logger=config.logger)

    self.webServicesClassList = [ ProcessorIntrospectionService,
                                  Hello,
                                  Test,
                                  NameService,
                                  ProcessorOoidService,
                                  ProcessorServicesQuery,
                                  ProcessorPriorityOoidService,
                                  ProcessorStats,
                                  ProcessorTimeAccumulation,
                                ]

    self.standardQueue = queue.Queue()
    self.priorityQueue = queue.Queue()

    self.registrationURL = "http://%s%s" % (config.registrationHostPort,
                                            sreg.RegistrationService.uri)
    self.deregistrationURL = "http://%s%s" % (config.registrationHostPort,
                                              sreg.DeregistrationService.uri)

    self.statsPools = sutil.DotDict({ 'processed': stats.CounterPool(config),
                                      'missing': stats.CounterPool(config),
                                      'failures': stats.CounterPool(config),
                                      'breakpadErrors': stats.CounterPool(config),
                                      'processTime': stats.DurationAccumulatorPool(config),
                                      'mostRecent': stats.MostRecentPool(config),
                                    })
    self.name = '%s:%s' % (config.serverIPAddress, config.serverPort)
    # an instance of this class can only go through one instantiation/shutdown
    # cycle.  It cannot be reused.  After creation, the state is "ready".  At
    # the end of execution of the 'start' method, the state changes to "dead".
    self.state = 'ready'
    # 'status' is the health of the processor.  This is the value that is sent
    # to the registrar.  The possible values are:
    #    'ok' - initial state
    #    'warning' - something is suspicious
    #    'shutdown' - the processor is no longer functioning
    self.status = 'ok'
    self.warnings = []
    logger.info("I am processor %s", self.name)

  #-----------------------------------------------------------------------------------------------------------------
  def responsiveJoin(self, thread):
    while True:
      try:
        thread.join(1.0)
        if not thread.isAlive():
          break
      except KeyboardInterrupt:
        logger.info ('quit detected')
        self.quit = True

  #-----------------------------------------------------------------------------------------------------------------
  def start(self):
    """
    """
    if 'ready' not in self.state:
      raise ProcessorCannotBeReUsedException('this Processor is used.  Processors cannot be reused')

    self.mainProcessorThread = threading.Thread(name="mainProcessorThread", target=self.mainProcessorLoop)
    self.registrationThread = threading.Thread(name="registrationThread", target=self.registrationLoop)
    try:
      self.mainProcessorThread.start()
      self.registrationThread.start()
      self.webAppThread()
    except Exception:
      sutil.reportExceptionAndContinue(logger)
    finally:
      logger.debug('the webAppThread has quit')
      self.quit = True
      logger.info('waiting for mainProcessorThread')
      self.responsiveJoin(self.mainProcessorThread)
      self.responsiveJoin(self.registrationThread)
      logger.debug('shutting down stackwalkers')
      self.orderlyShutdown()
      self.state = 'dead'
      logger.debug("done with work")

  #-----------------------------------------------------------------------------------------------------------------
  def orderlyShutdown(self):
    """this must be a cooperative function with all derived classes."""
    pass

  #-----------------------------------------------------------------------------------------------------------------
  def mainProcessorLoop(self):
    try:
      #get a job
      for aJobTuple in self.incomingJobStream(): # infinite iterator - never StopIteration
        self.quitCheck()
        logger.info("queuing job %s", str(aJobTuple))
        #deadWorkers = self.threadManager.deadWorkers()
        #if deadWorkers:
          #for thread_name in deadWorkers:
            #logger.info('%s has died, replacing it', thread_name)
            #self.crashStorePool.remove(thread_name)
          #self.threadManager.fullEmployment()
        self.threadManager.newTask(self.processJob, aJobTuple)
    except KeyboardInterrupt:
      logger.info("mainProcessorLoop gets quit request")
      self.quit = True
    logger.info("waiting for worker threads to stop")
    self.threadManager.waitForCompletion()
    logger.info("all worker threads stopped")
    # TODO - unregister because we're going away
    self.crashStorePool.cleanup()

  #-----------------------------------------------------------------------------------------------------------------
  def calculateProcessedToFailedRatio(self):
    processedCounters = self.statsPools.processed
    failedCounters = self.statsPools.failures
    try:
      processedToFailedRatio = float(processedCounters.read()) / float(failedCounters.read())
      if processedToFailedRatio < self.config.processedToFailedRatioThreshold:
        self.logger.warning('failed ProcessedToFailedRatio %s', processedToFailedRatio)
        self.warnings.append(('ProcessedToFailedRatio', processedToFailedRatio))
    except ZeroDivisionError:
      pass

  #-----------------------------------------------------------------------------------------------------------------
  def calculateUnderPerformingWorker(self):
    processedCounters = self.statsPools.processed
    underPerforming = processedCounters.underPerforming()
    if underPerforming:
      self.logger.warning('underperforming workers: %s', str(underPerforming))
      self.warnings.append(('UnderPerformingWorker', underPerforming))

  #-----------------------------------------------------------------------------------------------------------------
  def deadWorkers(self):
    deadWorkers = self.threadManager.deadWorkers()
    if deadWorkers:
      self.logger.warning('dead workers: %s', str(deadWorkers))
      self.warnings.append(('DeadWorkers', deadWorkers))

  #-----------------------------------------------------------------------------------------------------------------
  def assessHealth(self):
    self.warnings = []
    numberOfThreads = self.config.numberOfThreads
    self.calculateProcessedToFailedRatio()
    self.calculateUnderPerformingWorker()
    self.deadWorkers()
    if self.warnings:
      self.status = 'warnings'
    else:
      self.status = 'ok'

  #-----------------------------------------------------------------------------------------------------------------
  def registrationLoop(self):
    try:
      while True:
        self.assessHealth()
        self.quitCheck()
        try:
          urllib2.urlopen(self.registrationURL,
                          urllib.urlencode((('name', self.hostname),
                                            ('status', self.status))),
                          float(self.config.registrationTimeout.seconds))
          self.responsiveSleep(self.config.processorCheckInFrequency.seconds)
        except urllib2.URLError:
          sutil.reportExceptionAndContinue(self.logger,
                                           loggingLevel=logging.CRITICAL,
                                           showTraceback=False)
          self.responsiveSleep(30) #try to register again in 30 seconds
    except KeyboardInterrupt:
      self.logger.debug('registrationThread gets quit request')
    finally:
      try:
        self.status = "shutdown"
        urllib2.urlopen(self.deregistrationURL,
                        urllib.urlencode((('name', self.hostname),)),
                        float(self.config.registrationTimeout.seconds))
      except urllib2.URLError:
        sutil.reportExceptionAndContinue(self.logger,
                                         loggingLevel=logging.CRITICAL,
                                         showTraceback=False)

  #-----------------------------------------------------------------------------------------------------------------
  def webAppThread(self):
    try:
      servicesUriTuples = ((x.uri,
                      cpart.classWithPartialInit(x, self.config, self))
                     for x in self.webServicesClassList)
      self.serviceUrls = tuple(itertools.chain(*servicesUriTuples))
      logger.debug(str(self.serviceUrls))
      self.app =  sweb.StandAloneWebApplication(self.config.serverIPAddress,
                                                self.config.serverPort,
                                                self.serviceUrls,
                                                globals())
      #self.app =  web.application(self.serviceUrls, globals())
      self.app.run()
    except Exception:
      sutil.reportExceptionAndContinue(self.logger,
                                       loggingLevel=logging.CRITICAL,
                                       showTraceback=False)
    except KeyboardInterrupt:
      logger.info("quit request detected")
      self.quit = True
      raise
    finally:
      del self.app  # we're done - delete the app to cleanup one half of some circular references
      del self.webServicesClassList # delete objects that have some circular references to self

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
  @staticmethod
  def respondToSIGTERM(signalNumber, frame):
    """ these classes are instrumented to respond to a KeyboardInterrupt by cleanly shutting down.
        This function, when given as a handler to for a SIGTERM event, will make the program respond
        to a SIGTERM as neatly as it responds to ^C.
    """
    signame = 'SIGTERM'
    if signalNumber != signal.SIGTERM: signame = 'SIGHUP'
    logger.info("%s detected", signame)
    raise KeyboardInterrupt

  #-----------------------------------------------------------------------------------------------------------------
  def queueOoid(self, ooid):
    self.standardQueue.put((ooid,))

  #-----------------------------------------------------------------------------------------------------------------
  def queuePriorityOoid(self, ooid):
    self.priorityQueue.put((ooid,))

  #-----------------------------------------------------------------------------------------------------------------
  def queueIter(self, aQueue):
    """
    yields an item from a Queue or None is there is nothing in the queue.
    This iterator is perpetual - it never raises the StopIteration exception
    """
    while True:
      if aQueue.empty():
        yield None
      else:
        try:
          yield aQueue.get_nowait()
        except queue.Empty:
          yield None

  #-----------------------------------------------------------------------------------------------------------------
  def incomingJobStream(self):
    """
       merge the priorityQueue and standardQueue with preference to the priority
    """
    priorityJobIter = self.queueIter(self.priorityQueue)
    normalJobIter = self.queueIter(self.standardQueue)
    seenUuids = set()
    while (True):
      self.quitCheck()
      aJobTuple = priorityJobIter.next()
      if aJobTuple:
        # mark as priority
        threadLocalCrashStorage = self.crashStorePool.crashStorage()
        threadLocalCrashStorage.tagAsPriority(aJobTuple[0])
        self.logger.debug('yielding  priority job: %s', aJobTuple[0])
        yield aJobTuple
        continue
      aJobTuple = normalJobIter.next()
      if aJobTuple:
        self.logger.debug('yielding  normal job: %s', aJobTuple[0])
        yield aJobTuple
      else:
        logger.info("no jobs to do - sleeping %d seconds", self.processorLoopTime)
        self.responsiveSleep(self.processorLoopTime)

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
    ooid = aReportRecordAsDict["uuid"]
    threadLocalCrashStorage.save_processed(ooid, aReportRecordAsDict)

  #-----------------------------------------------------------------------------------------------------------------
  def processJob (self, jobTuple):
    """ This function is run only by a worker thread.
        Given a job, fetch a thread local database connection and the json document.  Use these
        to create the record in the 'reports' table, then start the analysis of the dump file.

        input parameters:
          jobTuple: a tuple containing up to three items: the jobId (the primary key from the jobs table), the
              jobOoid (a unique string with the json file basename minus the extension) and the priority (an integer)
    """
    if self.quit: return
    try:
      threadLocalCrashStorage = self.crashStorePool.crashStorage()
    except Exception:
      logger.critical("something's gone horribly wrong with the HBase connection")
      self.quit = True
      sutil.reportExceptionAndContinue(logger, loggingLevel=logging.CRITICAL)
    try:
      self.quitCheck()
      processTimeStatistic = self.statsPools.processTime.getStat()
      processTimeStatistic.start()
      new_jdoc = sutil.DotDict()
      new_jdoc.uuid = jobOoid = jobTuple[0]
      logger.info("starting job: %s", jobOoid)
      j_doc = threadLocalCrashStorage.get_meta(jobOoid) # raises OoidNotFoundException
      new_jdoc.processor_notes = err_list = []
      new_jdoc.started_datetime = datetime.datetime.now()

      try:
        new_jdoc.date_processed = sdt.datetimeFromISOdateString(j_doc["submitted_timestamp"])
      except KeyError:
        err_list.append("field 'submitted_timestamp' is missing, estimating submission time from last 6 digits of OOID")
        new_jdoc.date_processed = ooidm.dateFromOoid(jobOoid)

      self.preprocessCrashMetadata(j_doc, new_jdoc)
      new_jdoc.dump = ''

      try:
        self.doBreakpadStackDumpAnalysis(j_doc, new_jdoc, threadLocalCrashStorage)
      finally:
        new_jdoc.completed_datetime = c = datetime.datetime.now()
        mostRecentStatistic = self.statsPools.mostRecent.getStat().put(c)

      self.saveProcessedDumpJson(new_jdoc, threadLocalCrashStorage)
      if new_jdoc.success:
        logger.info("succeeded and committed: %s", jobOoid)
        self.statsPools.processed.getStat().increment()
      else:
        logger.info("failed but committed: %s", jobOoid)
        self.statsPools.failures.getStat().increment()
      self.quitCheck()
    except (KeyboardInterrupt, SystemExit):
      logger.info("quit request detected")
      self.quit = True
    except hbc.FatalException:
      logger.critical("something's gone horribly wrong with the HBase connection")
      self.quit = True
      sutil.reportExceptionAndContinue(logger, loggingLevel=logging.CRITICAL)
    except cstore.OoidNotFoundException, x:
      logger.warning("the ooid %s, was not found", jobOoid)
      self.statsPools.missing.getStat().increment()
      sutil.reportExceptionAndContinue(logger, logging.DEBUG, showTraceback=False)
    except Exception, x:
      self.statsPools.failures.getStat().increment()
      if x.__class__ != ErrorInBreakpadStackwalkException:
        sutil.reportExceptionAndContinue(logger)
      else:
        self.statsPools.breakpadErrors.getStat().increment()
        sutil.reportExceptionAndContinue(logger, logging.WARNING, showTraceback=False)
    finally:
      processTimeStatistic.end()

  #-----------------------------------------------------------------------------------------------------------------
  def preprocessCrashMetadata(self, j_doc, new_jdoc):
    #logger.debug("starting preprocessCrashMetadata")
    err_list = new_jdoc.processor_notes
    ooid = new_jdoc.uuid
    # 'ProductName' is required
    new_jdoc.product = sutil.get_req(j_doc, 'ProductName', err_list)
    # 'Version' is required
    new_jdoc.version = sutil.get_req(j_doc, 'Version', err_list)
    # 'BuildID' is required
    new_jdoc.build =   sutil.get_req(j_doc, 'BuildID', err_list)
    # 'URL' is optional
    new_jdoc.url = j_doc.get('URL', None)
    # 'Comments' is optional
    new_jdoc.user_comments = j_doc.get('Comments', None)
    # 'Notes' is optional - these are comments inserted by the OS/X version of breakpad
    new_jdoc.app_notes = j_doc.get('Notes', None)
    # 'Distributor' is optional
    new_jdoc.distributor = j_doc.get('Distributor', None)
    # 'Distributor_version' is optional
    new_jdoc.distributor_version = j_doc.get('Distributor_version', None)
    # 'Email' is optional
    new_jdoc.email = j_doc.get('Email', None)
    # 'HangID' is optional
    new_jdoc.hangid = j_doc.get('HangID',None)
    # 'EMCheckCompatibility' is optional, translates to 'addons_checked'
    new_jdoc.addons_checked =  j_doc.get('EMCheckCompatibility', "false").lower()

    #  'CrashTime' is required - but defaults to 0 if not present; error message added if missing
    try:
      crash_time = sutil.get_req(j_doc, 'CrashTime', err_list, 0)
      new_jdoc.client_crash_time_as_int = int(crash_time)
    except ValueError:
      err_list.append("can't make 'CrashTime' (%s) into an integer - setting to 0" % crash_time)
      new_jdoc.client_crash_time_as_int = 0
    # 'client_crash_date' is based on the client reported 'CrashTime'
    # is it valid to apply UTC to this value??
    new_jdoc.client_crash_date = datetime.datetime.fromtimestamp(new_jdoc.client_crash_time_as_int, Processor.utctz)

    # 'StartupTime' is required - defaults to None if missing; error message added if missing
    try:
      new_jdoc.client_startup_time_as_int = int(j_doc.setdefault('StartupTime', None)) # must have started up some time before crash
    except TypeError:
      err_list.append("'StartupTime' is missing")
      new_jdoc.client_startup_time_as_int = None
    except ValueError:
      err_list.append("'StartupTime' is't an integer")
      new_jdoc.client_startup_time_as_int = None

    # 'InstallTime' is required - defaults to None if missing; error message added if missing
    try:
      new_jdoc.client_install_time_as_int = int(j_doc.setdefault('InstallTime', None)) # must have installed some time before startup
    except TypeError:
      err_list.append("'InstallTime' is missing")
      new_jdoc.client_install_time_as_int = None
    except ValueError:
      err_list.append("'InstallTime' isn't an integer")
      new_jdoc.client_install_time_as_int = None

    # 'install_age' is based on 'CrashTime' and 'InstallTime' - defaults to None if either is missing
    try:
      new_jdoc.install_age = new_jdoc.client_crash_time_as_int - \
                            new_jdoc.client_install_time_as_int
    except (TypeError, ValueError):
      new_jdoc.install_age = None
      err_list.append("Cannot calculate an 'install_age from %s and %s'" %
          (str(new_jdoc.client_crash_time_as_int),
           str(new_jdoc.client_install_time_as_int)))

    # 'uptime' is based on 'CrashTime' and 'StartupTime'
    try:
      new_jdoc.uptime = max(0, new_jdoc.client_crash_time_as_int -
                            new_jdoc.client_startup_time_as_int)
    except (TypeError, ValueError):
      new_jdoc.uptime = None
      err_list.append("Cannot calculate an 'uptime' from %s and %s" %
                      (new_jdoc.client_crash_time_as_int,
                       new_jdoc.client_startup_time_as_int))

    # 'build_date' comes from 'BuildID'
    new_jdoc.build_date = None
    if new_jdoc.build:
      try:
        date_parts = Processor.buildDatePattern.match(new_jdoc.build).groups()
        new_jdoc.build_date = datetime.datetime(*(int(x) for x in date_parts))
      except (AttributeError, ValueError, KeyError), e:
        logger.debug(str(e))
        err_list.append("No 'build_date' could be determined: %s" % new_jdoc.build)

    # 'SecondsSinceLastCrash' is optional
    new_jdoc.last_crash = sutil.get_int_or_none(j_doc, 'SecondsSinceLastCrash')

    if self.config.collectAddon:
      #logger.debug("collecting Addons for %s", ooid)
      self.preprocessAddons(j_doc, new_jdoc)

    if self.config.collectCrashProcess:
      #logger.info("collecting Crash Process for %s", ooid)
      self.preprocessCrashProcess(j_doc, new_jdoc)

  #-----------------------------------------------------------------------------------------------------------------
  def preprocessAddons (self, j_doc, new_doc):
    jsonAddonString = sutil.get_req(j_doc, 'Add-ons', new_doc.processor_notes, "")
    new_doc.original_add_ons_string = jsonAddonString
    new_doc.addons = [x.split(":") for x in jsonAddonString.split(',')]
    for x in new_doc.addons:
      try:
        if len(x) != 2:
          new_doc.processor_notes.append('addon name/version is defective: %s' % str(x))
      except Exception:
        new_doc.processor_notes.append('addon name/version is defective: %s' % str(x))

  #-----------------------------------------------------------------------------------------------------------------
  def preprocessCrashProcess (self, j_doc, new_doc):
    """ Electrolysis Support - Optional - j_doc may contain a ProcessType of plugin. In the future this
        value would be default, content, maybe even Jetpack... This indicates which process was the crashing process.
        plugin - When set to plugin, the j_doc MUST calso contain PluginFilename, PluginName, and PluginVersion
    """
    # 'ProcessType' is optional
    new_doc.processType = j_doc.get('ProcessType', None)

    if "plugin" == new_doc.processType:
      # Bug#543776 We actually will are relaxing the non-null policy... a null filename, name, and version is OK. We'll use empty strings
      new_doc.pluginFilename = j_doc.get('PluginFilename', '')
      new_doc.pluginName  = j_doc.get('PluginName', '')
      new_doc.pluginVersion = j_doc.get('PluginVersion', '')

    if "jetPack"  == new_doc.processType:
      new_doc.jetpack_id = j_doc.get('JetpackID', '')
      new_doc.jetpack_name  = j_doc.get('JetpackName', '')

    if "content"   == new_doc.processType:
      pass # fill in as details become known

  #-----------------------------------------------------------------------------------------------------------------
  def doBreakpadStackDumpAnalysis (self, j_doc, new_jdoc, threadLocalCrashStorage):
    """ This function is run only by a worker thread.
        This function must be overriden in a subclass - this method will invoke the breakpad_stackwalk process
        (if necessary) and then do the anaylsis of the output
    """
    raise Exception("No breakpad_stackwalk invocation method specified")


