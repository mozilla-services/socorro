import psycopg2 as pg
import datetime as dt
import threading
import sets

import socorro.lib.psycopghelper as socorro_psy
import socorro.database.postgresql as socorro_pg

import socorro.lib.util as socorro_util

#-----------------------------------------------------------------------------------------------------------------
def iterateBetweenDatesGeneratorCreator(minDate, maxDate):
  def anIterator():
    oneWeek = dt.timedelta(7)
    beginWeekDay = minDate.weekday()
    if beginWeekDay:
      aDate = minDate - dt.timedelta(beginWeekDay) # begin on Monday before minDate
    else:
      aDate = minDate
    while aDate <= maxDate:
      nextMonday = aDate + oneWeek
      yield (aDate, nextMonday)
      aDate = nextMonday
  return anIterator

#-----------------------------------------------------------------------------------------------------------------
def nowIterator():
  oneWeek = dt.timedelta(7)
  now = dt.datetime.now()
  nowWeekDay = now.weekday()
  if nowWeekDay:
    mondayDate = now - dt.timedelta(nowWeekDay) # nearest Monday before now
  else:
    mondayDate = now
  yield (mondayDate, mondayDate + oneWeek)

#-----------------------------------------------------------------------------------------------------------------
def nextWeekIterator(now=None):
  oneWeek = dt.timedelta(7)
  if not now:
    now = dt.datetime.now()
  nowWeekDay = now.weekday()
  if nowWeekDay:
    nextMonday = now - dt.timedelta(nowWeekDay) + oneWeek
  else:
    nextMonday = now
  yield (nextMonday, nextMonday + oneWeek)

#-----------------------------------------------------------------------------------------------------------------
def emptyFunction():
  return ''

#=================================================================================================================
class PartitionControlParameterRequired(Exception):
  def __init__(self):
    super(PartitionControlParameterRequired, self).__init__("No partition control paramter was supplied")

#=================================================================================================================
class DatabaseObject(object):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, name=None, logger=None, creationSql=None, **kwargs):
    super(DatabaseObject, self).__init__()
    self.name = name
    self.creationSql = creationSql
    self.logger = logger
  #-----------------------------------------------------------------------------------------------------------------
  def create(self, databaseCursor):
    databaseCursor.execute(self.creationSql)
    self.additionalCreationProcedures(databaseCursor)
  #-----------------------------------------------------------------------------------------------------------------
  def additionalCreationProcedures(self, databaseCursor):
    pass
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    pass
  #-----------------------------------------------------------------------------------------------------------------
  def drop(self, databaseCursor):
    pass
  #-----------------------------------------------------------------------------------------------------------------
  def createPartitions(self, databaseCursor, iterator):
    pass

#=================================================================================================================
class Table (DatabaseObject):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, name=None, logger=None, creationSql=None, **kwargs):
    super(Table, self).__init__(name=name, logger=logger, creationSql=creationSql, **kwargs)
  #-----------------------------------------------------------------------------------------------------------------
  def drop(self, databaseCursor):
    databaseCursor.execute("drop table if exists %s cascade" % self.name)
  #-----------------------------------------------------------------------------------------------------------------
  def insert(self, rowTuple=None, **kwargs):
    pass

#=================================================================================================================
class PartitionedTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, name=None, logger=None, creationSql=None, partitionNameTemplate='%s', partitionCreationSqlTemplate='', partitionCreationIterablorCreator=nowIterator, **kwargs):
    super(PartitionedTable, self).__init__(name=name, logger=logger, creationSql=creationSql)
    self.partitionNameTemplate = partitionNameTemplate
    self.partitionCreationSqlTemplate = partitionCreationSqlTemplate
    self.partitionCreationIterablorCreator = partitionCreationIterablorCreator
    self.insertSql = None
    self.partitionCreationLock = threading.RLock()
    self.partitionCreationHistory = sets.Set()
    self.dependentDatabaseObjectsList = [self]

  #-----------------------------------------------------------------------------------------------------------------
  #def additionalCreationProcedures(self, databaseCursor):
    #self.createPartitions(databaseCursor, self.partitionCreationIterablorCreator)
  #-----------------------------------------------------------------------------------------------------------------
  def createPartitions(self, databaseCursor, iterator):
    self.logger.debug("%s - in createPartitions", threading.currentThread().getName())
    for x in iterator():
      partitionCreationParameters = self.partitionCreationParameters(x)
      partitionName = self.partitionNameTemplate % partitionCreationParameters["partitionName"]
      partitionCreationSql = self.partitionCreationSqlTemplate % partitionCreationParameters
      aPartition = Table(name=partitionName, logger=self.logger, creationSql=partitionCreationSql)
      self.logger.debug("%s - savepoint createPartitions_%s",threading.currentThread().getName(), partitionName)
      databaseCursor.execute("savepoint createPartitions_%s" % partitionName)
      try:
        self.logger.debug("%s - creating %s", threading.currentThread().getName(), partitionName)
        aPartition.create(databaseCursor)
        #databaseCursor.connection.commit()
        self.logger.debug("%s - successful - releasing savepoint", threading.currentThread().getName())
        databaseCursor.execute("release savepoint createPartitions_%s" % partitionName)
      except pg.ProgrammingError, x:
        self.logger.debug("%s -- creating %s failed in createPartitions: %s", threading.currentThread().getName(), partitionName, x)
        #databaseCursor.connection.rollback()
        self.logger.debug("%s - rolling back and releasing save points", threading.currentThread().getName())
        databaseCursor.execute("rollback to createPartitions_%s; release savepoint createPartitions_%s;" % (partitionName, partitionName))
  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self):
    """must return a dictionary of string substitution parameters"""
    return {}
  #-----------------------------------------------------------------------------------------------------------------
  def setDependents(self, listOfDependentDatabaseObjects):
    """new partitions are created automatically when an insert requires them.  Sometimes other database objects
       should be created at the same time.  For example, if B has a foreign key to A, then the B partition should
       be created when the new A partition is created.

       parameters:
         listOfDependentDatabaseObjects: a list of of database objects to be created"""
    self.dependentDatabaseObjectsList.extend(listOfDependentDatabaseObjects)
  #-----------------------------------------------------------------------------------------------------------------
  def updateColumnDefinitions(self, databaseCursor):
    childTableList = socorro_pg.childTablesForTable(self.name, databaseCursor)
    for aChildTableName in childTableList:
      databaseCursor.execute("alter table %s no inherit %s", (aTable, aChildTableName))
    self.alterColumnDefinitions(databaseCursor, self.name)
    for aChildTableName in childTableList:
      self.alterColumnDefinitions(databaseCursor, aChildTableName)
    for aChildTableName in childTableList:
      databaseCursor.execute("alter table %s inherit %s", (aTable, aChildTableName))
  #-----------------------------------------------------------------------------------------------------------------
  def insert(self, databaseCursor, row, alternateCursorFunction, **kwargs):
    try:
      uniqueIdentifier = kwargs["date_processed"]
    except KeyError:
      raise PartitionControlParameterRequired()
    dateIterator = iterateBetweenDatesGeneratorCreator(uniqueIdentifier, uniqueIdentifier)
    dateRangeTuple = dateIterator().next()
    partitionName = self.partitionCreationParameters(dateRangeTuple)["partitionName"]
    insertSql = self.insertSql.replace('TABLENAME', partitionName)
    try:
      databaseCursor.execute("savepoint %s" % partitionName)
      #self.logger.debug("%s -trying to insert into %s", threading.currentThread().getName(), self.name)
      databaseCursor.execute(insertSql, row)
      databaseCursor.execute("release savepoint %s" % partitionName)
    except pg.ProgrammingError, x:
      self.logger.debug('%s - failed: %s', threading.currentThread().getName(), x)
      self.logger.debug('%s - rolling back and releasing savepoint', threading.currentThread().getName())
      databaseCursor.execute("rollback to %s; release savepoint %s;" % (partitionName, partitionName))
      try:
        self.logger.debug('%s - acquiring %s lock', threading.currentThread().getName(), self.name)
        self.partitionCreationLock.acquire()
        try:
          if partitionName not in self.partitionCreationHistory:
            self.logger.debug('%s - need to create table for %s', threading.currentThread().getName(), partitionName)
            self.partitionCreationHistory.add(partitionName)
            self.logger.debug("%s - trying to create %s", threading.currentThread().getName(), partitionName)
            altConnection, altCursor = alternateCursorFunction()
            self.logger.debug("%s - dependents(%d): %s", threading.currentThread().getName(), len(self.dependentDatabaseObjectsList), str([x.name for x in self.dependentDatabaseObjectsList]))
            for aDatabaseObject in self.dependentDatabaseObjectsList:
              self.logger.debug("%s - trying to partition for %s", threading.currentThread().getName(), aDatabaseObject.name)
              aDatabaseObject.createPartitions(altCursor, dateIterator)
            self.logger.debug("%s - committing creation of %s", threading.currentThread().getName(), partitionName)
            altConnection.commit()
            self.logger.debug("%s - succeeded create %s for %s", threading.currentThread().getName(), partitionName, dateRangeTuple)
        finally:
          self.logger.debug('%s - releasing %s lock', threading.currentThread().getName(), self.name)
          self.partitionCreationLock.release()
      except pg.DatabaseError, x:
        self.logger.debug("%s - the partition %s already exists - no need to create it: %s:%s", threading.currentThread().getName(), partitionName, type(x), x)
        altConnection.rollback()
        altConnection.close()
      self.logger.debug("%s -trying to insert into %s for the second time", threading.currentThread().getName(), self.name)
      databaseCursor.execute(insertSql, row)

#=================================================================================================================
class BranchesTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(BranchesTable, self).__init__(name="branches", logger=logger,
                                        creationSql = """
                                            CREATE TABLE branches (
                                                product character varying(30) NOT NULL,
                                                version character varying(16) NOT NULL,
                                                branch character varying(24) NOT NULL,
                                                PRIMARY KEY (product, version)
                                            );""")

#=================================================================================================================
class DumpsTable(PartitionedTable):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(DumpsTable, self).__init__(name='dumps', logger=logger,
                                     creationSql="""
                                         CREATE TABLE dumps (
                                             report_id integer NOT NULL,
                                             date_processed timestamp without time zone,
                                             data text
                                         );
                                         --CREATE TRIGGER dumps_insert_trigger
                                         --   BEFORE INSERT ON dumps
                                         --   FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""",
                                     partitionCreationSqlTemplate="""
                                         CREATE TABLE %(partitionName)s (
                                             CONSTRAINT %(partitionName)s_date_check CHECK (TIMESTAMP without time zone '%(startDate)s' <= date_processed and date_processed < TIMESTAMP without time zone '%(endDate)s'),
                                             PRIMARY KEY (report_id)
                                         )
                                         INHERITS (dumps);
                                         CREATE INDEX %(partitionName)s_report_id_date_key ON %(partitionName)s (report_id, date_processed);
                                         ALTER TABLE %(partitionName)s
                                             ADD CONSTRAINT %(partitionName)s_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_%(compressedStartDate)s(id) ON DELETE CASCADE;
                                         """)
    self.insertSql = """insert into TABLENAME (report_id, date_processed, data) values (%s, %s, %s)"""
  #-----------------------------------------------------------------------------------------------------------------
  def alterColumnDefinitions(self, databaseCursor, tableName):
    columnNameTypeDictionary = socorro_pg.columnNameTypeDictionaryForTable(tableName, databaseCursor)
    #if 'date_processed' not in columnNameTypeDictionary:
      #databaseCursor.execute("""ALTER TABLE %s
                                    #ADD COLUMN date_processed TIMESTAMP without time zone;""" % tableName)
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    self.updateColumnDefinitions(databaseCursor)
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)
    #if 'dumps_pkey' in indexesList:
      #databaseCursor.execute("""ALTER TABLE dumps
                                    #DROP CONSTRAINT dumps_pkey;""")
    #databaseCursor.execute("""DROP RULE IF EXISTS rule_dumps_partition ON dumps;""")
    #triggersList = socorro_pg.triggersForTable(self.name, databaseCursor)
    #if 'dumps_insert_trigger' not in triggersList:
      #databaseCursor.execute("""CREATE TRIGGER dumps_insert_trigger
                                    #BEFORE INSERT ON dumps
                                    #FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""")
  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self, uniqueIdentifier):
    startDate, endDate = uniqueIdentifier
    startDateAsString = "%4d-%02d-%02d" % startDate.timetuple()[:3]
    compressedStartDateAsString = startDateAsString.replace("-", "")
    endDateAsString = "%4d-%02d-%02d" % endDate.timetuple()[:3]
    return { "partitionName": "dumps_%s" % compressedStartDateAsString,
             "startDate": startDateAsString,
             "endDate": endDateAsString,
             "compressedStartDate": compressedStartDateAsString
           }

#=================================================================================================================
class ExtensionsTable(PartitionedTable):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(ExtensionsTable, self).__init__(name='extensions', logger=logger,
                                          creationSql="""
                                              CREATE TABLE extensions (
                                                  report_id integer NOT NULL,
                                                  date_processed timestamp without time zone,
                                                  extension_key integer NOT NULL,
                                                  extension_id character varying(100) NOT NULL,
                                                  extension_version character varying(16)
                                              );
                                              --CREATE TRIGGER extensions_insert_trigger
                                              --    BEFORE INSERT ON extensions
                                              --    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""",
                                          partitionCreationSqlTemplate="""
                                              CREATE TABLE %(partitionName)s (
                                                  CONSTRAINT %(partitionName)s_date_check CHECK (TIMESTAMP without time zone '%(startDate)s' <= date_processed and date_processed < TIMESTAMP without time zone '%(endDate)s'),
                                                  PRIMARY KEY (report_id)
                                                  )
                                                  INHERITS (extensions);
                                              CREATE INDEX %(partitionName)s_report_id_date_key ON %(partitionName)s (report_id, date_processed);
                                              ALTER TABLE %(partitionName)s
                                                  ADD CONSTRAINT %(partitionName)s_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_%(compressedStartDate)s(id) ON DELETE CASCADE;
                                              """)
    self.insertSql = """insert into TABLENAME (report_id, date_processed, extension_key, extension_id, extension_version) values (%s, %s, %s, %s, %s)"""
  #-----------------------------------------------------------------------------------------------------------------
  def alterColumnDefinitions(self, databaseCursor, tableName):
    columnNameTypeDictionary = socorro_pg.columnNameTypeDictionaryForTable(tableName, databaseCursor)
    #if 'date_processed' not in columnNameTypeDictionary:
      #databaseCursor.execute("""ALTER TABLE %s
                                    #ADD COLUMN date_processed TIMESTAMP without time zone;""" % tableName)
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    self.updateColumnDefinitions(databaseCursor)
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)
    #if 'extensions_pkey' in indexesList:
      #databaseCursor.execute("""ALTER TABLE extensions
                                    #DROP CONSTRAINT extensions_pkey;""")
    #databaseCursor.execute("""DROP RULE IF EXISTS rule_extensions_partition ON extensions;""")
    #triggersList = socorro_pg.triggersForTable(self.name, databaseCursor)
    #if 'extensions_insert_trigger' not in triggersList:
      #databaseCursor.execute("""CREATE TRIGGER extensions_insert_trigger
                                    #BEFORE INSERT ON extensions
                                    #FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""")
  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self, uniqueIdentifier):
    startDate, endDate = uniqueIdentifier
    startDateAsString = "%4d-%02d-%02d" % startDate.timetuple()[:3]
    compressedStartDateAsString = startDateAsString.replace("-", "")
    endDateAsString = "%4d-%02d-%02d" % endDate.timetuple()[:3]
    return { "partitionName": "extensions_%s" % compressedStartDateAsString,
             "startDate": startDateAsString,
             "endDate": endDateAsString,
             "compressedStartDate": compressedStartDateAsString
           }

#=================================================================================================================
class FramesTable(PartitionedTable):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(FramesTable, self).__init__(name='frames', logger=logger,
                                      creationSql="""
                                          CREATE TABLE frames (
                                              report_id integer NOT NULL,
                                              date_processed timestamp without time zone,
                                              frame_num integer NOT NULL,
                                              signature varchar(255)
                                          );
                                          --CREATE TRIGGER frames_insert_trigger
                                          --    BEFORE INSERT ON frames
                                          --    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""",
                                      partitionCreationSqlTemplate="""
                                          CREATE TABLE %(partitionName)s (
                                              CONSTRAINT %(partitionName)s_date_check CHECK (TIMESTAMP without time zone '%(startDate)s' <= date_processed and date_processed < TIMESTAMP without time zone '%(endDate)s'),
                                              PRIMARY KEY (report_id, frame_num)
                                          )
                                          INHERITS (frames);
                                          CREATE INDEX %(partitionName)s_report_id_date_key ON %(partitionName)s (report_id, date_processed);
                                          ALTER TABLE %(partitionName)s
                                              ADD CONSTRAINT %(partitionName)s_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_%(compressedStartDate)s(id) ON DELETE CASCADE;
                                          """
                                     )
    self.insertSql = """insert into TABLENAME (report_id, frame_num, date_processed, signature) values (%s, %s, %s, %s)"""
  #-----------------------------------------------------------------------------------------------------------------
  def alterColumnDefinitions(self, databaseCursor, tableName):
    columnNameTypeDictionary = socorro_pg.columnNameTypeDictionaryForTable(tableName, databaseCursor)
    #if 'date_processed' not in columnNameTypeDictionary:
      #databaseCursor.execute("""ALTER TABLE %s
                                    #ADD COLUMN date_processed TIMESTAMP without time zone;""" % tableName)
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    self.updateColumnDefinitions(databaseCursor)
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)
    #if 'frames_pkey' in indexesList:
      #databaseCursor.execute("""ALTER TABLE frames
                                    #DROP CONSTRAINT frames_pkey;""")
    #databaseCursor.execute("""DROP RULE IF EXISTS rule_frames_partition ON frames;""")
    #triggersList = socorro_pg.triggersForTable(self.name, databaseCursor)
    #if 'frames_insert_trigger' not in triggersList:
      #databaseCursor.execute("""CREATE TRIGGER frames_insert_trigger
                                    #BEFORE INSERT ON frames
                                    #FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""")
  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self, uniqueIdentifier):
    startDate, endDate = uniqueIdentifier
    startDateAsString = "%4d-%02d-%02d" % startDate.timetuple()[:3]
    compressedStartDateAsString = startDateAsString.replace("-", "")
    endDateAsString = "%4d-%02d-%02d" % endDate.timetuple()[:3]
    return { "partitionName": "frames_%s" % compressedStartDateAsString,
             "startDate": startDateAsString,
             "endDate": endDateAsString,
             "compressedStartDate": compressedStartDateAsString
           }

#=================================================================================================================
class JobsTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(JobsTable, self).__init__(name = "jobs",  logger=logger,
                                    creationSql = """
                                        CREATE TABLE jobs (
                                            id serial NOT NULL PRIMARY KEY,
                                            pathname character varying(1024) NOT NULL,
                                            uuid varchar(50) NOT NULL UNIQUE,
                                            owner integer,
                                            priority integer DEFAULT 0,
                                            queueddatetime timestamp without time zone,
                                            starteddatetime timestamp without time zone,
                                            completeddatetime timestamp without time zone,
                                            success boolean,
                                            message text,
                                            FOREIGN KEY (owner) REFERENCES processors (id)
                                        );
                                        CREATE INDEX jobs_owner_key ON jobs (owner);
                                        CREATE INDEX jobs_owner_starteddatetime_key ON jobs (owner, starteddatetime);
                                        CREATE INDEX jobs_owner_starteddatetime_priority_key ON jobs (owner, starteddatetime, priority DESC);
                                        CREATE INDEX jobs_completeddatetime_queueddatetime_key ON jobs (completeddatetime, queueddatetime);
                                        --CREATE INDEX jobs_priority_key ON jobs (priority);
                                        """)
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)
    if 'idx_owner' in indexesList:
      databaseCursor.execute("""
          DROP INDEX idx_owner;
          CREATE INDEX jobs_owner_key ON jobs (owner);""")
    if 'idx_queueddatetime' in indexesList:
      databaseCursor.execute("""
          DROP INDEX idx_queueddatetime;""")
    if 'idx_starteddatetime' in indexesList:
      databaseCursor.execute("""
          DROP INDEX idx_starteddatetime;""")
    if 'jobs_priority_queueddatetime' in indexesList:
      databaseCursor.execute("""
          DROP INDEX jobs_priority_queueddatetime;""")
    if 'jobs_owner_starteddatetime' in indexesList:
      databaseCursor.execute("""
          DROP INDEX jobs_owner_starteddatetime;
          CREATE INDEX jobs_owner_starteddatetime_key ON jobs (owner, starteddatetime);""")
    #if 'jobs_priority_key' not in indexesList:
    #  databaseCursor.execute("""CREATE INDEX jobs_priority_key ON jobs (priority);""")
    if 'jobs_owner_starteddatetime_priority_key' not in indexesList:
      databaseCursor.execute("""CREATE INDEX jobs_owner_starteddatetime_priority_key ON jobs (owner, starteddatetime, priority DESC);""")
    if 'jobs_completeddatetime_queueddatetime_key' not in indexesList:
      databaseCursor.execute("""CREATE INDEX jobs_completeddatetime_queueddatetime_key ON jobs (completeddatetime, queueddatetime);""")
    if 'jobs_success_key' not in indexesList:
      databaseCursor.execute("""CREATE INDEX jobs_success_key ON jobs (success);""")

#=================================================================================================================
class PriorityJobsTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, name="priorityjobs", logger=None, **kwargs):
    super(PriorityJobsTable, self).__init__(name=name, logger=logger,
                                            creationSql = """
                                                CREATE TABLE %s (
                                                    uuid varchar(255) NOT NULL PRIMARY KEY
                                                );""" % name)

#=================================================================================================================
class ProcessorsTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(ProcessorsTable, self).__init__(name = "processors", logger=logger,
                                        creationSql = """
                                            CREATE TABLE processors (
                                                id serial NOT NULL PRIMARY KEY,
                                                name varchar(255) NOT NULL UNIQUE,
                                                startdatetime timestamp without time zone NOT NULL,
                                                lastseendatetime timestamp without time zone
                                            );""")
  def updateDefinition(self, databaseCursor):
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)
    #if 'idx_processor_name' in indexesList:
      #databaseCursor.execute("""DROP INDEX idx_processor_name;
                                #ALTER TABLE processors ADD CONSTRAINT processors_name_key UNIQUE (name);""")

#=================================================================================================================
class ReportsTable(PartitionedTable):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(ReportsTable, self).__init__(name='reports', logger=logger,
                                       creationSql="""
                                          CREATE TABLE reports (
                                              id serial NOT NULL,
                                              client_crash_date timestamp with time zone,
                                              date_processed timestamp without time zone,
                                              uuid character varying(50) NOT NULL,
                                              product character varying(30),
                                              version character varying(16),
                                              build character varying(30),
                                              signature character varying(255),
                                              url character varying(255),
                                              install_age integer,
                                              last_crash integer,
                                              uptime integer,
                                              cpu_name character varying(100),
                                              cpu_info character varying(100),
                                              reason character varying(255),
                                              address character varying(20),
                                              os_name character varying(100),
                                              os_version character varying(100),
                                              email character varying(100),
                                              build_date timestamp without time zone,
                                              user_id character varying(50),
                                              started_datetime timestamp without time zone,
                                              completed_datetime timestamp without time zone,
                                              success boolean,
                                              truncated boolean,
                                              processor_notes text,
                                              user_comments character varying(1024),
                                              app_notes character varying(1024),
                                              distributor character varying(20),
                                              distributor_version character varying(20)
                                          );
                                          --CREATE TRIGGER reports_insert_trigger
                                          --    BEFORE INSERT ON reports
                                          --    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""",
                                       partitionCreationSqlTemplate="""
                                          CREATE TABLE %(partitionName)s (
                                              CONSTRAINT %(partitionName)s_date_check CHECK (TIMESTAMP without time zone '%(startDate)s' <= date_processed and date_processed < TIMESTAMP without time zone '%(endDate)s'),
                                              CONSTRAINT %(partitionName)s_unique_uuid unique (uuid),
                                              PRIMARY KEY(id)
                                          )
                                          INHERITS (reports);
                                          CREATE INDEX %(partitionName)s_date_processed_key ON %(partitionName)s (date_processed);
                                          CREATE INDEX %(partitionName)s_uuid_key ON %(partitionName)s (uuid);
                                          CREATE INDEX %(partitionName)s_signature_key ON %(partitionName)s (signature);
                                          CREATE INDEX %(partitionName)s_url_key ON %(partitionName)s (url);
                                          CREATE INDEX %(partitionName)s_product_version_key ON %(partitionName)s (product, version);
                                          --CREATE INDEX %(partitionName)s_uuid_date_processed_key ON %(partitionName)s (uuid, date_processed);
                                          CREATE INDEX %(partitionName)s_signature_date_processed_key ON %(partitionName)s (signature, date_processed);
                                          """
                                      )
    #self.setDependents([FramesTable(logger=logger), DumpsTable(logger=logger), ExtensionsTable(logger=logger)])
    self.insertSql = """insert into TABLENAME
                            (uuid, client_crash_date, date_processed, product, version, build, url, install_age, last_crash, uptime, email, build_date, user_id, user_comments, app_notes, distributor, distributor_version) values
                            (%s,   %s,                %s,             %s,      %s,      %s,    %s,  %s,          %s,         %s,     %s,    %s,         %s,      %s,            %s,        %s,          %s)"""
  #-----------------------------------------------------------------------------------------------------------------
  def additionalCreationProcedures(self, databaseCursor):
    pass
  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self, uniqueIdentifier):
    startDate, endDate = uniqueIdentifier
    startDateAsString = "%4d-%02d-%02d" % startDate.timetuple()[:3]
    compressedStartDateAsString = startDateAsString.replace("-", "")
    endDateAsString = "%4d-%02d-%02d" % endDate.timetuple()[:3]
    return { "partitionName": "reports_%s" % compressedStartDateAsString,
             "startDate": startDateAsString,
             "endDate": endDateAsString,
             "compressedStartDate": compressedStartDateAsString
           }
  #-----------------------------------------------------------------------------------------------------------------
  def alterColumnDefinitions(self, databaseCursor, tableName):
    columnNameTypeDictionary = socorro_pg.columnNameTypeDictionaryForTable(tableName, databaseCursor)
    #if 'user_comments' not in columnNameTypeDictionary:
      #databaseCursor.execute("""ALTER TABLE %s rename column comments to user_comments""" % tableName)
    #if 'client_crash_date' not in columnNameTypeDictionary:
      #databaseCursor.execute("""ALTER TABLE %s rename column date to client_crash_date""" % tableName)
    #if 'app_notes' not in columnNameTypeDictionary:
      #databaseCursor.execute("""ALTER TABLE %s ADD COLUMN app_notes character varying(1024)""" % tableName)
    #if 'distributor' not in columnNameTypeDictionary:
      #databaseCursor.execute("""ALTER TABLE %s ADD COLUMN distributor character varying(20)""" % tableName)
    #if 'distributor_version' not in columnNameTypeDictionary:
      #databaseCursor.execute("""ALTER TABLE %s ADD COLUMN distributor_version character varying(20)""" % tableName)
    #if 'message' in columnNameTypeDictionary:
      #databaseCursor.execute("""ALTER TABLE %s rename column message to processor_notes""" % tableName)
    #if 'started_datetime' not in columnNameTypeDictionary:
      #databaseCursor.execute("""ALTER TABLE %s rename column starteddatetime to started_datetime""" % tableName)
    #if 'completed_datetime' not in columnNameTypeDictionary:
      #databaseCursor.execute("""ALTER TABLE %s rename column completeddatetime to completed_datetime""" % tableName)
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    databaseCursor.execute("""DROP RULE IF EXISTS rule_reports_partition ON reports;""")
    self.updateColumnDefinitions(databaseCursor)
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)
    #if 'reports_pkey' in indexesList:
      #databaseCursor.execute("""ALTER TABLE reports DROP CONSTRAINT reports_pkey CASCADE;""")
    #if 'idx_reports_date' in indexesList:
      #databaseCursor.execute("""DROP INDEX idx_reports_date;""")
    #if 'ix_reports_signature' in indexesList:
      #databaseCursor.execute("""DROP INDEX ix_reports_signature;""")
    #if 'ix_reports_url' in indexesList:
      #databaseCursor.execute("""DROP INDEX ix_reports_url;""")
    #if 'ix_reports_uuid' in indexesList:
      #databaseCursor.execute("""DROP INDEX ix_reports_uuid;""")
    #triggersList = socorro_pg.triggersForTable(self.name, databaseCursor)
    #if 'reports_insert_trigger' not in triggersList:
      #databaseCursor.execute("""CREATE TRIGGER reports_insert_trigger
                                    #BEFORE INSERT ON reports
                                    #FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""")

#=================================================================================================================
class ServerStatusTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(ServerStatusTable, self).__init__(name='server_status', logger=logger,
                                       creationSql="""
                                          CREATE TABLE server_status (
                                              id serial NOT NULL,
                                              date_recently_completed timestamp without time zone,
                                              date_oldest_job_queued timestamp without time zone,
                                              avg_process_sec real,
                                              avg_wait_sec real,
                                              waiting_job_count integer NOT NULL,
                                              processors_count integer NOT NULL,
                                              date_created timestamp without time zone NOT NULL
                                          );
                                          ALTER TABLE ONLY server_status
                                              ADD CONSTRAINT server_status_pkey PRIMARY KEY (id);
                                          CREATE INDEX idx_server_status_date ON server_status USING btree (date_created, id);
                                          """)

#=================================================================================================================
class SignatureDimsTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(Table, self).__init__(name='signaturedims', logger=logger,
                                       creationSql="""
                                          CREATE TABLE signaturedims (
                                              id serial NOT NULL,
                                              signature character varying(255) NOT NULL);
                                          ALTER TABLE ONLY signaturedims
                                              ADD CONSTRAINT signaturedims_pkey PRIMARY KEY (id);
                                          CREATE UNIQUE INDEX signaturedims_signature_key ON signaturedims USING btree (signature);
                                          """)

#=================================================================================================================
class TCByUrlConfigTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(Table, self).__init__(name='tcbyurlconfig', logger=logger,
                                       creationSql="""
                                          CREATE TABLE tcbyurlconfig (
                                              id serial NOT NULL,
                                              productdims_id integer,
                                              enabled boolean);
                                          ALTER TABLE ONLY tcbyurlconfig
                                              ADD CONSTRAINT tcbyurlconfig_pkey PRIMARY KEY (id);
                                          ALTER TABLE ONLY tcbyurlconfig
                                              ADD CONSTRAINT tcbyurlconfig_productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id);

                                          """)

#=================================================================================================================
class MTBFConfig(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(Table, self).__init__(name='mtbfconfig', logger=logger,
                                       creationSql="""
                                          CREATE TABLE mtbfconfig (
                                              id serial NOT NULL,
                                              productdims_id integer,
                                              start_dt date,
                                              end_dt date);
                                          ALTER TABLE ONLY mtbfconfig
                                              ADD CONSTRAINT mtbfconfig_pkey PRIMARY KEY (id);
                                          CREATE INDEX mtbfconfig_end_dt_key ON mtbfconfig USING btree (end_dt);
                                          CREATE INDEX mtbfconfig_start_dt_key ON mtbfconfig USING btree (start_dt);
                                          CREATE INDEX mtbffacts_day_key ON mtbffacts USING btree (day);
                                          CREATE INDEX mtbffacts_product_id_key ON mtbffacts USING btree (productdims_id);
                                          ALTER TABLE ONLY mtbfconfig
                                              ADD CONSTRAINT mtbfconfig_productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id);
                                          """)

#=================================================================================================================
class MTBFFacts(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(Table, self).__init__(name='mtbffacts', logger=logger,
                                       creationSql="""
                                          CREATE TABLE mtbffacts (
                                              id serial NOT NULL,
                                              avg_seconds integer NOT NULL,
                                              report_count integer NOT NULL,
                                              unique_users integer NOT NULL,
                                              day date,
                                              productdims_id integer);
                                          ALTER TABLE ONLY mtbffacts
                                              ADD CONSTRAINT mtbffacts_pkey PRIMARY KEY (id);
                                          ALTER TABLE ONLY mtbffacts
                                              ADD CONSTRAINT mtbffacts_productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id);

                                          """)

#=================================================================================================================
class ProductDimsTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(Table, self).__init__(name='productdims', logger=logger,
                                       creationSql="""
                                          CREATE TABLE productdims (
                                              id serial NOT NULL,
                                              product character varying(30) NOT NULL,
                                              version character varying(16) NOT NULL,
                                              os_name character varying(100),
                                              release character varying(50) NOT NULL);                                          
                                          ALTER TABLE ONLY productdims
                                              ADD CONSTRAINT productdims_pkey PRIMARY KEY (id);
                                          CREATE INDEX productdims_product_version_key ON productdims USING btree (product, version);
                                          CREATE UNIQUE INDEX productdims_product_version_os_name_release_key ON productdims USING btree (product, version, release, os_name);

                                          """)

#=================================================================================================================
class TopCrashUrlFactsTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(Table, self).__init__(name='topcrashurlfacts', logger=logger,
                                       creationSql="""
                                          CREATE TABLE topcrashurlfacts (
                                              id serial NOT NULL,
                                              count integer NOT NULL,
                                              rank integer,
                                              day date NOT NULL,
                                              productdims_id integer,
                                              urldims_id integer,
                                              signaturedims_id integer
                                          );
                                          ALTER TABLE ONLY topcrashurlfacts
                                              ADD CONSTRAINT topcrashurlfacts_pkey PRIMARY KEY (id);
                                          CREATE INDEX topcrashurlfacts_count_key ON topcrashurlfacts USING btree (count);
                                          CREATE INDEX topcrashurlfacts_day_key ON topcrashurlfacts USING btree (day);
                                          CREATE INDEX topcrashurlfacts_productdims_key ON topcrashurlfacts USING btree (productdims_id);
                                          CREATE INDEX topcrashurlfacts_signaturedims_key ON topcrashurlfacts USING btree (signaturedims_id);
                                          CREATE INDEX topcrashurlfacts_urldims_key ON topcrashurlfacts USING btree (urldims_id);
                                          ALTER TABLE ONLY topcrashurlfacts
                                              ADD CONSTRAINT topcrashurlfacts_productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id);
                                          ALTER TABLE ONLY topcrashurlfacts
                                              ADD CONSTRAINT topcrashurlfacts_signaturedims_id_fkey FOREIGN KEY (signaturedims_id) REFERENCES signaturedims(id);
                                          ALTER TABLE ONLY topcrashurlfacts
                                              ADD CONSTRAINT topcrashurlfacts_urldims_id_fkey FOREIGN KEY (urldims_id) REFERENCES urldims(id);
                                          ALTER TABLE ONLY topcrashurlfactsreports
                                              ADD CONSTRAINT topcrashurlfactsreports_topcrashurlfacts_id_fkey FOREIGN KEY (topcrashurlfacts_id) REFERENCES topcrashurlfacts(id) ON DELETE CASCADE;

                                          """)

#=================================================================================================================
class UrlDimsTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(Table, self).__init__(name='urldims', logger=logger,
                                       creationSql="""
                                          CREATE TABLE urldims (
                                              id serial NOT NULL,
                                              domain character varying(255) NOT NULL,
                                              url character varying(255) NOT NULL);                                   
                                          ALTER TABLE ONLY urldims
                                              ADD CONSTRAINT urldims_pkey PRIMARY KEY (id);
                                          CREATE UNIQUE INDEX urldims_url_domain_key ON urldims USING btree (url, domain);
                                          """)
##=================================================================================================================
class TopCrashUrlFactsReportsTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(Table, self).__init__(name='topcrashurlfactsreports', logger=logger,
                                       creationSql="""
                                          CREATE TABLE topcrashurlfactsreports (
                                              id serial NOT NULL,
                                              uuid character varying(50) NOT NULL,
                                              comments character varying(500),
                                              topcrashurlfacts_id integer);          
                                          ALTER TABLE ONLY topcrashurlfactsreports
                                              ADD CONSTRAINT topcrashurlfactsreports_pkey PRIMARY KEY (id);
                                          CREATE INDEX topcrashurlfactsreports_topcrashurlfacts_id_key ON topcrashurlfactsreports USING btree (topcrashurlfacts_id);
                                          """)

##=================================================================================================================
class TopCrashersTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(TopCrashersTable, self).__init__(name='topcrashers', logger=logger,
                                       creationSql="""
                                          CREATE TABLE topcrashers (
                                              id serial NOT NULL,
                                              signature character varying(255) NOT NULL,
                                              version character varying(30) NOT NULL,
                                              product character varying(30) NOT NULL,
                                              build character varying(30) NOT NULL,
                                              total integer,
                                              win integer,
                                              mac integer,
                                              linux integer,
                                              rank integer,
                                              last_rank integer,
                                              trend character varying(30),
                                              uptime real,
                                              users integer,
                                              last_updated timestamp without time zone
                                          );
                                          ALTER TABLE ONLY topcrashers
                                              ADD CONSTRAINT topcrashers_pkey PRIMARY KEY (id);
                                          """)

#=================================================================================================================
#class ParititioningTriggerScript(DatabaseObject):
  ##-----------------------------------------------------------------------------------------------------------------
  #def __init__ (self, logger):
    #super(ParititioningTriggerScript, self).__init__(name = "partition_insert_trigger", logger=logger,
                                                     #creationSql = """
#CREATE OR REPLACE FUNCTION partition_insert_trigger()
#RETURNS TRIGGER AS $$
#import socorro.database.server as ds
#try:
  #targetTableName = ds.targetTableName(TD["table_name"], TD['new']['date_processed'])
  ##plpy.info(targetTableName)
  #planName = ds.targetTableInsertPlanName (targetTableName)
  ##plpy.info("using plan: %s" % planName)
  #values = ds.getValuesList(TD, SD, plpy)
  ##plpy.info(str(values))
  ##plpy.info('about to execute plan')
  #result = plpy.execute(SD[planName], values)
  #return None
#except KeyError:  #no plan
  ##plpy.info("oops no plan for: %s" % planName)
  #SD[planName] = ds.createNewInsertQueryPlan(TD, SD, targetTableName, planName, plpy)
  ##plpy.info('about to execute plan for second time')
  #result = plpy.execute(SD[planName], values)
  #return None
#$$
#LANGUAGE plpythonu;""")
  #def updateDefinition(self, databaseCursor):
    #databaseCursor.execute(self.creationSql)

#=================================================================================================================
#class ChattyParititioningTriggerScript(DatabaseObject):
  #-----------------------------------------------------------------------------------------------------------------
  #def __init__ (self, logger):
    #super(ChattyParititioningTriggerScript, self).__init__(name = "partition_insert_trigger", logger=logger,
                                                     #creationSql = """
#CREATE OR REPLACE FUNCTION partition_insert_trigger()
#RETURNS TRIGGER AS $$
#import socorro.database.server as ds
#import logging
#import logging.handlers
#try:
  #targetTableName = ds.targetTableName(TD["table_name"], TD['new']['date_processed'])
  #planName = ds.targetTableInsertPlanName (targetTableName)
  #try:
    #logger = SD["logger"]
  #except KeyError:
    #SD["logger"] = logger = logging.getLogger(targetTableName)
    #logger.setLevel(logging.DEBUG)
    #rotatingFileLog = logging.handlers.RotatingFileHandler("/tmp/partitionTrigger.log", "a", 100000000, 10)
    #rotatingFileLog.setLevel(logging.DEBUG)
    #rotatingFileLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
    #rotatingFileLog.setFormatter(rotatingFileLogFormatter)
    #logger.addHandler(rotatingFileLog)
    #logger.debug("---------- beginning new session ----------")
    #SD["counter"] = 0
  #values = ds.getValuesList(TD, SD, plpy)
  #logger.debug("%08d plan: %s", SD["counter"], planName)
  #SD["counter"] += 1
  #result = plpy.execute(SD[planName], values)
  #return 'SKIP'
#except KeyError:  #no plan
  #logger.debug('creating new plan for: %s', planName)
  #SD[planName] = ds.createNewInsertQueryPlan(TD, SD, targetTableName, planName, plpy)
  #result = plpy.execute(SD[planName], values)
  #return 'SKIP'
#$$
#LANGUAGE plpythonu;""")
  ##-----------------------------------------------------------------------------------------------------------------
  #def updateDefinition(self, databaseCursor):
    #databaseCursor.execute(self.creationSql)

#-----------------------------------------------------------------------------------------------------------------
def connectToDatabase(config, logger):
  databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % config
  databaseConnection = pg.connect(databaseDSN)
  databaseCursor = databaseConnection.cursor(cursor_factory=socorro_psy.LoggingCursor)
  databaseCursor.setLogger(logger)
  return (databaseConnection, databaseCursor)

#-----------------------------------------------------------------------------------------------------------------
databaseObjectClassListForSetup = [BranchesTable,
                                   ProcessorsTable,
                                   JobsTable,
                                   PriorityJobsTable,
                                   ReportsTable,
                                   DumpsTable,
                                   FramesTable,
                                   ExtensionsTable,
                                   ServerStatusTable,
                                   TopCrashersTable,
                                   SignatureDimsTable,
                                   ProductDimsTable,
                                   UrlDimsTable,
                                   MTBFFacts,
                                   TopCrashUrlFactsReportsTable,
                                   TopCrashUrlFactsTable,
                                   TCByUrlConfigTable,
                                   MTBFConfig
                                  ]

#-----------------------------------------------------------------------------------------------------------------
def setupDatabase(config, logger):
  databaseConnection, databaseCursor = connectToDatabase(config, logger)
  try:
    #try:
      #databaseCursor.execute("CREATE LANGUAGE plpythonu")
    #except:
      #databaseConnection.rollback()
    for aDatabaseObjectClass in databaseObjectClassListForSetup:
      aDatabaseObject = aDatabaseObjectClass(logger=logger)
      aDatabaseObject.create(databaseCursor)
    databaseConnection.commit()
  except:
    databaseConnection.rollback()
    socorro_util.reportExceptionAndAbort(logger)

#-----------------------------------------------------------------------------------------------------------------
def teardownDatabase(config,logger):
  databaseConnection,databaseCursor = connectToDatabase(config,logger)
  try:
    for databaseObjectClass in databaseObjectClassListForSetup:
      aDatabaseObject = databaseObjectClass(logger=logger)
      aDatabaseObject.drop(databaseCursor)
    databaseConnection.commit()
  except:
    databaseConnection.rollback()
    socorro_util.reportExceptionAndContinue(logger)

#-----------------------------------------------------------------------------------------------------------------
databaseObjectClassListForUpdate = [BranchesTable,
                                   ProcessorsTable,
                                   JobsTable,
                                   PriorityJobsTable,
                                   ReportsTable,
                                   DumpsTable,
                                   FramesTable,
                                   ExtensionsTable,
                                   ServerStatusTable,
                                   TopCrashersTable,
                                   SignatureDimsTable,
                                   ProductDimsTable,
                                   UrlDimsTable,
                                   MTBFFacts,
                                   TopCrashUrlFactsTable,
                                   TopCrashUrlFactsReportsTable,
                                   TCByUrlConfigTable,
                                   MTBFConfig
                                  ]
#-----------------------------------------------------------------------------------------------------------------
def updateDatabase(config, logger):
  databaseConnection, databaseCursor = connectToDatabase(config, logger)
  try:
    #try:
      #databaseCursor.execute("CREATE LANGUAGE plpythonu")
    #except:
      #databaseConnection.rollback()
    for aDatabaseObjectClass in databaseObjectClassListForUpdate:
      aDatabaseObject = aDatabaseObjectClass(logger=logger)
      aDatabaseObject.updateDefinition(databaseCursor)
    databaseConnection.commit()
  except:
    databaseConnection.rollback()
    socorro_util.reportExceptionAndAbort(logger)

#-----------------------------------------------------------------------------------------------------------------
databaseObjectClassListForWeeklyPartitions = [ReportsTable,
                                              DumpsTable,
                                              FramesTable,
                                              ExtensionsTable,
                                             ]
#-----------------------------------------------------------------------------------------------------------------
def createPartitions(config, logger):
  databaseConnection, databaseCursor = connectToDatabase(config, logger)
  weekIterator = iterateBetweenDatesGeneratorCreator(config.startDate, config.endDate)
  try:
    for aDatabaseObjectClass in databaseObjectClassListForWeeklyPartitions:
      aDatabaseObject = aDatabaseObjectClass(logger=logger)
      aDatabaseObject.createPartitions(databaseCursor, weekIterator)
    databaseConnection.commit()
  except:
    databaseConnection.rollback()
    socorro_util.reportExceptionAndAbort(logger)

