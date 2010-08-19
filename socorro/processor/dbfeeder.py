import datetime
import logging
import signal
import time
import threading
import Queue as queue

import web

logger = logging.getLogger("dbfeeder")

import socorro.lib.util as sutil
import socorro.lib.threadlib as thr
import socorro.lib.datetimeutil as sdt
import socorro.database.schema as sch
import socorro.database.database as sdb
import socorro.storage.crashstorage as cstore
import socorro.storage.hbaseClient as hbc


#=================================================================================================================
class DbFeeder(object):
  """ """
  #-----------------------------------------------------------------------------------------------------------------
  # static data. Beware threading!
  _config_requirements = (
                         )
  _hbase_config_requirements = ("hbaseHost",
                                "hbasePort",
                               )

  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, config):
    """
    """
    super(DbFeeder, self).__init__()
    self.config = config
    self.logger = config.logger
    self.databasePool = sdb.DatabaseConnectionPool(config, config.logger)
    self.reportsTable = sch.ReportsTable(logger=config.logger)
    self.extensionsTable = sch.ExtensionsTable(logger=config.logger)
    self.pluginsTable = sch.PluginsTable(logger=config.logger)
    self.pluginsReportsTable = sch.PluginsReportsTable(logger=config.logger)
    self.standardThreadManager = thr.TaskManager(self.config.numberOfThreads)
    self.priorityThreadManager = thr.TaskManager(1)
    self.crashStoragePool = cstore.CrashStoragePool(config)
    #self.hbaseConnection = hbc.HBaseConnectionForCrashReports(config.hbaseHost,
                                                              #config.hbasePort,
                                                              #config.hbaseTimeout)
    self.plugIdCache = {}
    self.quit = False
    #self.logger.debug('finished init')

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
  def quitCheck(self):
    if self.quit:
      raise KeyboardInterrupt

  #-----------------------------------------------------------------------------------------------------------------
  def responsiveSleep (self, seconds):
    for x in xrange(int(seconds)):
      self.quitCheck()
      time.sleep(1.0)

  #-----------------------------------------------------------------------------------------------------------------
  def responsiveJoin(self, thread):
    while True:
      try:
        #if self.quit:
          #self.logger.debug('waiting for %s, %s', str(thread), thread.isAlive())
        thread.join(1.0)
        if not thread.isAlive():
          #self.logger.debug('%s is dead', str(thread))
          break
      except KeyboardInterrupt:
        logger.debug ('quit detected by responsiveJoin')
        self.quit = True

  #-----------------------------------------------------------------------------------------------------------------
  def start (self):
    self.logger.debug('start')
    standardJobThread = threading.Thread(name="standardProcessingThread", target=self.standardProcessingThread)
    standardJobThread.start()
    priorityJobThread = threading.Thread(name="priorityProcessingThread", target=self.priorityProcessingThread)
    priorityJobThread.start()
    self.logger.debug("waiting to join priorityJobThread")
    self.responsiveJoin(priorityJobThread)
    self.logger.debug("waiting to join standardJobThread")
    self.responsiveJoin(standardJobThread)

  #-----------------------------------------------------------------------------------------------------------------
  def standardProcessingThread (self):
    self.logger.debug('standardProcessingThread start')
    threadLocalCrashStorage = self.crashStoragePool.crashStorage()
    try:
      #logger.debug('start - about to threadLocalCrashStorage.dbFeederStandardJobIter()')
      for crash_json in threadLocalCrashStorage.dbFeederStandardJobIter(self.responsiveSleep): # infinite iterator - never StopIteration
        self.quitCheck()
        logger.info("queuing standard job %s", crash_json['uuid'])
        self.standardThreadManager.newTask(self.databaseInsert, (crash_json,))
    except Exception:
      sutil.reportExceptionAndContinue(logger)
    finally:
      self.quit = True
      logger.debug("we're quitting standardProcessingThread")
      logger.debug("waiting for standard worker threads to stop")
      self.standardThreadManager.waitForCompletion()
      logger.debug("all standard worker threads stopped")

  #-----------------------------------------------------------------------------------------------------------------
  def priorityProcessingThread (self):
    self.logger.debug('priorityProcessingThread start')
    threadLocalCrashStorage = self.crashStoragePool.crashStorage()
    try:
      #logger.debug('start - about to threadLocalCrashStorage.dbFeederPriorityJobIter()')
      for crash_json in threadLocalCrashStorage.dbFeederPriorityJobIter(self.responsiveSleep): # infinite iterator - never StopIteration
        self.quitCheck()
        logger.info("queuing priority job %s", crash_json['uuid'])
        self.priorityThreadManager.newTask(self.databaseInsert, (crash_json,))
    except Exception:
      sutil.reportExceptionAndContinue(logger)
    finally:
      self.quit = True
      logger.info("we're quitting priorityProcessingThread")
      logger.info("waiting for priority worker threads to stop")
      self.priorityThreadManager.waitForCompletion()
      logger.info("all priority worker threads stopped")

  #-----------------------------------------------------------------------------------------------------------------
  def getCachedPluginId(self, pluginFilename, pluginName):
    try:
      keyTuple = (pluginFilename, pluginName)
      return self.plugIdCache[keyTuple]
    except KeyError:
      # not in cache, get from the database
      #logger.debug('%s not in cache, getting from database', str(keyTuple))
      threadLocalDbConnection = self.databasePool.connection()
      cursor = threadLocalDbConnection.cursor()
      try:
        id = sdb.singleValueSql(cursor,
                                """select
                                      id
                                  from plugins
                                  where
                                      filename = %s
                                      and name = %s""",
                                  keyTuple)
        self.plugIdCache[keyTuple] = id
        return id
      except sdb.SQLDidNotReturnSingleValue:
        #logger.debug('%s not in database. inserting', str(keyTuple))
        threadLocalDbConnection = self.databasePool.connection("%s.2" % threading.currentThread().getName())
        cursor = threadLocalDbConnection.cursor()
        try:
          self.pluginsTable.insert(cursor, keyTuple)
          result = cursor.fetchall()
          self.plugIdCache[keyTuple] = id = result[0][0]
          threadLocalDbConnection.commit()
          return id
        except:
          threadLocalDbConnection.rollback()
          sutil.reportExceptionAndContinue(logger, logging.WARNING)

  #-----------------------------------------------------------------------------------------------------------------
  def insertPlugin(self, crash_json, reportId):
    threadLocalDbConnection = self.databasePool.connection()
    cursor = threadLocalDbConnection.cursor()
    pluginId = self.getCachedPluginId(crash_json['pluginFilename'],
                                      crash_json['pluginName'])
    #if not pluginId:
      #logger.error("plugin id is bad: %s", pluginId)
    pluginsTuple = (reportId,
                    pluginId,
                    crash_json['date_processed'],
                    crash_json['pluginVersion']
                   )
    self.pluginsReportsTable.insert(cursor,
                                    pluginsTuple,
                                    self.databasePool.connectionCursorPair,
                                    date_processed=crash_json['date_processed'])

  #-----------------------------------------------------------------------------------------------------------------
  def insertAddons(self, crash_json, reportId):
    threadLocalDbConnection = self.databasePool.connection()
    cursor = threadLocalDbConnection.cursor()
    date_processed = crash_json['date_processed']
    for i, x in enumerate(crash_json['addons']):
      addonName = x[0][:100] # limit length
      try:
        addonVersion = x[1]
      except IndexError:
        addonVersion = ''
      if not addonName and not addonVersion:
        continue
      self.extensionsTable.insert(cursor,
                                  (reportId,
                                   date_processed,
                                   i,
                                   addonName,
                                   addonVersion),
                                  self.databasePool.connectionCursorPair,
                                  date_processed=date_processed)

  #-----------------------------------------------------------------------------------------------------------------
  maxLengths = { 'uuid': 50,
                 'product': 30,
                 'version': 16,
                 'build': 30,
                 'signature': 255,
                 'url': 255,
                 'cpu_name': 100,
                 'cpu_info': 100,
                 'reason': 255,
                 'address': 20,
                 'os_name': 100,
                 'os_version': 100,
                 'email': 100,
                 'user_id': 50,
                 'user_comments': 1024,
                 'app_notes': 1024,
                 'distributor': 20,
                 'distributor_version': 20,
               }
  @staticmethod
  def enforceMaxLength(d, key):
    if key in DbFeeder.maxLengths:
      try:
        return d.setdefault(key, '')[:DbFeeder.maxLengths[key]]
      except TypeError:
        return None
    else:
      return d.setdefault(key)
  #-----------------------------------------------------------------------------------------------------------------
  def insertReport(self, crash_json):
    threadLocalDbConnection = self.databasePool.connection()
    rowTuple = tuple((DbFeeder.enforceMaxLength(crash_json, x) for x in self.reportsTable.columns))
    ooid = crash_json['uuid']
    # TODO: debug - remove this
    #items = dict(zip(self.reportsTable.columns, rowTuple))
    #for key, value in items.iteritems():
      #logger.debug('%s: "%s", %s', key, value, str(type(value)))
    logger.debug('insert for %s', ooid)
    #logger.debug('insert for %s: %s', ooid, str(rowTuple))
    date_processed = crash_json['date_processed']
    try:
      cursor = threadLocalDbConnection.cursor()
      self.reportsTable.insert(cursor,
                               rowTuple,
                               self.databasePool.connectionCursorPair,
                               date_processed=date_processed)
    except sdb.databaseModule.IntegrityError:
      logger.info('%s - already in the database, replacing', ooid)
      threadLocalDbConnection.rollback()
      r = sdb.execute(threadLocalDbConnection.cursor(),
                  """delete from reports where uuid = %s and date_processed = %s""",
                  (ooid, date_processed))
      try:   # not quite sure why I've got to try fetching data from the delete
             # but without this, the delete doesn't seem to actually happen
        for x in r:
          pass
      except Exception:
        pass
      threadLocalDbConnection.commit()
      note = 'This record was reprocessed on %s' % str(crash_json['completed_datetime'])
      crash_json['processor_notes'] = "%s; %s" % (crash_json['processor_notes'],
                                                 note)
      rowTuple = tuple((crash_json[x] for x in self.reportsTable.columns))
      cursor = threadLocalDbConnection.cursor()
      self.reportsTable.insert(cursor,
                               rowTuple,
                               self.databasePool.connectionCursorPair,
                               date_processed=date_processed)
    result = cursor.fetchall()
    try:
      return result[0][0]
    except Exception, x:
      sutil.reportExceptionAndContinue(logger, logging.WARNING)
      return None


  #-----------------------------------------------------------------------------------------------------------------
  def databaseInsert (self, crash_json_tuple):
    try:
      threadLocalDbConnection = self.databasePool.connection()
      crash_json = crash_json_tuple[0]
      ooid = crash_json['uuid']
      crashStorage = self.crashStoragePool.crashStorage()
      raw_crash = crashStorage.get_meta(ooid)
      crash_json['url'] = raw_crash.setdefault('URL', '')
      crash_json['email'] = raw_crash.setdefault('Email', '')
      crash_json['user_id'] = ''
      crash_json['process_type'] = raw_crash.setdefault('ProcessType', '')
      crash_json['date_processed'] = \
                sdt.datetimeFromISOdateString(crash_json['date_processed'])
      crash_json['started_datetime'] = \
                sdt.datetimeFromISOdateString(crash_json['started_datetime'])
      crash_json['completed_datetime'] = \
                sdt.datetimeFromISOdateString(crash_json['completed_datetime'])
      crash_json['processor_notes'] = \
                '; '.join(crash_json['processor_notes'])
      # enforce max lengths
      crash_json
      try:
        # Reports table insert
        reportId = self.insertReport(crash_json)
        if reportId:
          # Frames table insert - must reparse pipeDump
          # self.insertFrames(crash_json, reportId)
          # Extentions table (Addons) insert
          self.insertAddons(crash_json, reportId)
          # Plugins table insert
          try:
            if crash_json['processType'] == 'plugin':
              self.insertPlugin(crash_json, reportId)
          except KeyError:
            pass
        else:
          logger.warning("Suspicious behavior: insert of %s didn't return id",
                         ooid)
        threadLocalDbConnection.commit()
      except Exception:
        threadLocalDbConnection.rollback()
        sutil.reportExceptionAndContinue(logger)
    except Exception:
      sutil.reportExceptionAndContinue(logger)





