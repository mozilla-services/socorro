import logging
import logging.handlers
import os
import psycopg2
import psycopg2.extras
import sys

import socorro.lib.util
import socorro.lib.ConfigurationManager as cm
import socorro.database.schema as schema
from   socorro.database.schema import databaseObjectClassListForSetup as dbClasses

class IntDataset:
  def __init__(self, configContext):
    self.initLogging()

    force = configContext.force
    msg = ("Check your configuration, you are about to delete %s" % configContext['databaseName'])
    if force and configContext['databaseName'].find('test') == -1:
      self.log.warn(msg)
    elif configContext['databaseName'].find('test') == -1:
      self.log.fatal(msg)
      os.sys.exit(-1);

    self.log.info("current configuration\n%s", str(configContext))
    databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % configContext
    self.conn = psycopg2.connect(databaseDSN)
    self.configContext = configContext

  def doCommandLineCommand(self):
    if( configContext.command == 'refresh' ):
      self.refresh()
    elif( configContext.command == "touch" ):
      self.touch()
    elif (configContext.command == "dump"):
      if(configContext.dumpDir):
        self.dump(configContext.dumpDir)
      else:
        self.log.fatal("No directory was specified for dump... intdataset.py -C dump <dir_path>")
        os.sys.exit(-1);
    else:
      print "FATAL: unknown command %s" % configContext.command
  
  def initLogging(self):
    self.log = logging.getLogger("intdataset")
    self.log.setLevel(logging.DEBUG)

    stderrLog = logging.StreamHandler()
    stderrLog.setLevel(30)
    stderrLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
    stderrLog.setFormatter(stderrLogFormatter)
    self.log.addHandler(stderrLog)

    rotatingFileLog = logging.handlers.RotatingFileHandler('./log-intdataset.log', "a", 1000000, 50)
    rotatingFileLog.setLevel(logging.DEBUG)
    rotatingFileLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
    rotatingFileLog.setFormatter(rotatingFileLogFormatter)
    self.log.addHandler(rotatingFileLog)

  def dropTables(self):
    self.log.info("Dropping Tables")
    self.cur = self.conn.cursor()
    for klass in dbClasses:
      table = klass(logger=self.log)
      if table.drop( self.cur ):
        self.log.info("Dropped %s ? %s" % (table.name, self.cur.rowcount))
    self.conn.commit()

  def larscreateTables(self):
    #print "using     schema.setupDatabase( self.configContext)"
    schema.setupDatabase( self.configContext, self.log)

  def createTables(self):
# DETAIL:  exceptions.ImportError: No module named  socorro.database.server
#    self.log.info("Creating tables using schema.py setupDatabase");
#    schema.setupDatabase(self.configContext, self.log)
    self.log.info("Creating tables");
    dbClasses.reverse()
    
    for klass in dbClasses:
      self.cur = self.conn.cursor()
      self.log.info(klass)
      table = klass(logger=self.log)
      # if we call table.create then we get partitions and extra stuff
      self.log.debug( table.creationSql )
      try:
        self.cur.execute( table.creationSql )
      except Exception,x:
        self.log.error('Attempting %s: %s says %s'%(table.creationSql,type(x),x))
      self.conn.commit()
    dbClasses.reverse()

  def _loadTable(self, table):
    dataDir = None
    try:
      dataDir = self.configContext.loadDataDirectory
    except:
      dataDir = '../database/dataset/int'
      
    datafile = os.path.join(dataDir,"%s" % table)
    if os.path.isfile( datafile):
      dataset = open(datafile, "r")
      self.log.info("Starting %s COPY" % table)
      self.cur = self.conn.cursor()
      try:
        self.cur.copy_from(dataset, table)
      except Exception,x:
        self.log.error('While loading %s: %s (%s)'%(table,type(x),x))
        raise()
      self.conn.commit()
      self.log.info("Performed %s COPY %s " % (table, self.cur.rowcount))
    else:
      self.log.warn("Skipping %s no such file" % datafile)

  def loadTables(self):
    dbClasses.reverse()
    self.cur = self.conn.cursor()
    #self.cur.execute("DROP TRIGGER dumps_insert_trigger ON dumps")
    #self.cur.execute("DROP TRIGGER extensions_insert_trigger ON extensions")
    #self.cur.execute("DROP TRIGGER frames_insert_trigger ON frames")
    #self.cur.execute("DROP TRIGGER reports_insert_trigger ON reports")
    for klass in dbClasses:
      table = klass(logger=self.log)
      self._loadTable(table.name)
    self.conn.commit()
    dbClasses.reverse()

  def dump(self, dir):
    if not os.path.isdir( dir ):
      self.log.error("%s is not a directory, cannot dump tables" % dir)
    else:
      self.cur = self.conn.cursor()
      for klass in dbClasses:
        table = klass(logger=self.log).name

        if(table == 'parititioningtriggers'):
          table = 'datasetmetadata'
        datafile = open(dir + "/" + table, 'w')

        #TODO check datafile is writable...
        self.log.info("Dumping %s" % datafile)
        self.cur.copy_to(datafile, table)

  def metadata(self):
    cur = self.conn.cursor()
    cur.execute("""
    DROP TABLE IF EXISTS datasetmetadata;
    CREATE TABLE datasetmetadata (
        reference TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
        timeshifted TIMESTAMP WITHOUT TIME ZONE NOT NULL);
      """)
#INSERT INTO datasetmetadata (reference, timeshifted)
#    VALUES( TIMESTAMP '2008-10-18 17:00:02', TIMESTAMP '2008-10-18 17:00:02');
    self.conn.commit()
    self._loadTable('datasetmetadata') 

  def timeshift(self):
    cur = self.conn.cursor()
    #TODO test out set local timezone and get rid of - 1 hour
    cur.execute("""
      SET LOCAL TIMEZONE = 'PST8';
      UPDATE topcrashers SET last_updated = (last_updated + 
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata));
      UPDATE extensions SET date_processed = (date_processed + 
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata));
      UPDATE jobs SET 
        queueddatetime = (queueddatetime + 
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata)),
        starteddatetime = (starteddatetime + 
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata)),
        completeddatetime = (completeddatetime + 
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata));
      UPDATE processors SET 
        startdatetime = (startdatetime + 
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata)),
        lastseendatetime = (lastseendatetime +
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata));
      UPDATE reports SET  
         client_crash_date = (client_crash_date +
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata)),
         date_processed = (date_processed +
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata));
      UPDATE server_status SET  
         date_recently_completed = (date_recently_completed + 
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata)),
         date_oldest_job_queued = (date_oldest_job_queued +
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata)),
         date_created = (date_created +
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata));

      UPDATE datasetmetadata SET timeshifted = (reference +
          (select CURRENT_TIMESTAMP - reference - INTERVAL '1 hour' from datasetmetadata));
      
    """)
    #todo jobstatus oldest_job_queued... and handle nulls in general
    self.conn.commit()

  def refresh(self, useLarsCreate=False):
    "Creates a pristine copy of integration test dataset."
    self.dropTables()
    if useLarsCreate:
      self.larscreateTables()
    else:
      self.createTables()
    self.loadTables()
    self.metadata()
    self.timeshift()

  def touch(self):
    "Updates stale dates to a more current time period. No tables are dropped"
    self.timeshift()


if __name__ == "__main__":

  import commonconfig as config

  config.command = cm.Option()
  config.command.doc = 'command to run avainst intdata - {refresh, dump, touch}'
  config.command.default = 'refresh'
  config.command.singleCharacter = 'C'

  config.force = cm.Option()
  config.force.doc = 'force run regardless of database name'
  config.force.default = False
  config.force.singleCharacter = 'F'
  config.force.fromStringConverter = cm.booleanConverter

  config.dumpDir = cm.Option()
  config.dumpDir.doc = 'Used with the dump command, directory to write out intdataset into'
  config.dumpDir.singleCharacter = 'd'

  configContext = cm.newConfiguration(configurationModule=config, applicationName="Integration Dataset")
  data = IntDataset(configContext)
  data.doCommandLineCommand()
