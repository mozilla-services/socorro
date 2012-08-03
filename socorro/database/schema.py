# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import psycopg2 as pg
import datetime as dt
import threading

import socorro.lib.prioritize as socorro_pri
import socorro.lib.psycopghelper as socorro_psy
import socorro.database.postgresql as socorro_pg

import socorro.lib.util as socorro_util
"""
Schema.py contains several utility functions and the code which describes most of the database tables used by socorro.
However, large portions of Schema.py are out of date and the file is slated for replacement by different code.
"""

#-----------------------------------------------------------------------------------------------------------------
def mondayPairsIteratorFactory(minDate, maxDate):
  """
  Given a pair of dates, creates iterator that returns (aMonday,theNextMonday) such that
    - the first returned pair defines an interval holding minDate
    - the last returned pair defines an interval holding maxDate
  if minDate or maxDate are not instances of datetime.date, raises TypeError
  if maxDate > minDate, raises ValueError
  """
  if not (isinstance(minDate,dt.date) and isinstance(maxDate,dt.date)):
    raise TypeError("minDate and maxDate must be instances of datetime.date")
  if maxDate < minDate:
    raise ValueError("minDate must be <= maxDate")
  def anIterator():
    oneWeek = dt.timedelta(7)
    aDate = minDate - dt.timedelta(minDate.weekday()) # begin on Monday before minDate
    while aDate <= maxDate:
      nextMonday = aDate + oneWeek
      yield (aDate, nextMonday)
      aDate = nextMonday
  return anIterator()

#-----------------------------------------------------------------------------------------------------------------
# For each database TableClass below,
# databaseDependenciesForSetup[TableClass] = [List of TableClasses on which this TableClass depends]
# NOTE: This requires that new Tables be added textually below every Table on which they depend
databaseDependenciesForSetup = {}
def getOrderedSetupList(whichTables = None):
  """
  A helper function to get the correct order to create tables during setup.
  whichTables is a list of Tables, possibly empty, or None
  If not whichTables, then all the known tables are visited
  """
  # if whichTables is None, then databaseDependenciesForSetup.keys() is used
  return socorro_pri.dependencyOrder(databaseDependenciesForSetup,whichTables)
databaseDependenciesForPartition = {}
def getOrderedPartitionList(whichTables):
  """
  A helper function to get the needed PartionedTables for a given set of PartitionedTables
  """
  if not whichTables:
    return []
  order = socorro_pri.dependencyOrder(databaseDependenciesForPartition,whichTables)
  return order

# This set caches knowledge of existing partition tables to avoid hitting database. Beware cache incoherence
partitionCreationHistory = set()
#-----------------------------------------------------------------------------------------------------------------
def partitionWasCreated(partitionTableName):
  """Helper function to examine partitionCreationHistory"""
  return partitionTableName in partitionCreationHistory
#-----------------------------------------------------------------------------------------------------------------
def markPartitionCreated(partitionTableName):
  """Helper function to update partitionCreationHistory"""
  global partitionCreationHistory
  partitionCreationHistory.add(partitionTableName)

#=================================================================================================================
class PartitionControlParameterRequired(Exception):
  def __init__(self):
    super(PartitionControlParameterRequired, self).__init__("No partition control paramter was supplied")

#=================================================================================================================
class DatabaseObject(object):
  """
  Base class for all objects (Tables, Constraints, Indexes) that may be individually created and used in the database
  Classes that inherit DatabaseObject:
   - Must supply appropriate creationSql parameter to the superclass constructor
   - May override method additionalCreationProcedure(self,aDatabaseCursor). If this is provided, it is
     called after creationSql is executed in method create(self,aDatabaseCursor)
     The cursor's connection is neither committed nor rolled back during the call to create
   - May override methods which do nothing in this class:
       = drop(self,aDatabaseCursor)
       = updateDefinition(self,aDatabaseCursor)
       = createPartitions(self,aDatabaseCursor,aPartitionDetailsIterator)
   Every leaf class that inherits DatabaseObject should be aware of the module-level dictionary: databaseDependenciesForSetup.
   If that leaf class should be created when the database is being set up, the class itself must be added as a key in the
   databaseDependenciesForSetup dictionary. The value associated with that key is a possibly empty iterable containing the
   classes on which the particular leaf class depends: Those that must already be created before the particular instance is
   created. This is often because the particular table has one or more foreign keys referencing tables upon which it depends.
   """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, name=None, logger=None, creationSql=None, **kwargs):
    super(DatabaseObject, self).__init__()
    self.name = name
    self.creationSql = creationSql
    self.logger = logger
  #-----------------------------------------------------------------------------------------------------------------
  def _createSelf(self,databaseCursor):
    databaseCursor.execute(self.creationSql)
    self.additionalCreationProcedures(databaseCursor)
  #-----------------------------------------------------------------------------------------------------------------
  def create(self, databaseCursor):
    orderedDbObjectList = getOrderedSetupList([self.__class__])
    for dbObjectClass in orderedDbObjectList:
      dbObjectObject = self
      if not self.__class__ == dbObjectClass:
        dbObjectObject = dbObjectClass(logger = self.logger)
      databaseCursor.execute("savepoint creating_%s"%dbObjectObject.name)
      try:
        dbObjectObject._createSelf(databaseCursor)
        databaseCursor.execute("release savepoint creating_%s"%dbObjectObject.name)
      except pg.ProgrammingError,x:
        databaseCursor.execute("rollback to creating_%s"%dbObjectObject.name)
        databaseCursor.connection.commit()
        self.logger.debug("%s - in create for %s, dbObject %s exists",threading.currentThread().getName(),self.name,dbObjectObject.name)

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
  """
  Base class for all Table objects that may be created and used in the database.
  Classes that inherit DatabaseObject:
   - Must supply appropriate creationSql parameter to the superclass constructor
   - May override method insert(self,rowTuple, **kwargs) to do the right thing during an insert
   - May provide method alterColumnDefinitions(self,aDatabaseCursor,tableName)
   - May provide method updateDefinition(self,aDatabaseCursor)
   - Must be aware of databaseDependenciesForSetup and how it is used
  class Table inherits method create from DatabaseObject
  class Table provides a reasonable implementation of method drop, overriding the empty one in DatabaseObject
  """
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
  """
  Base class for Tables that will be partitioned or are likely to be programmatically altered.
  Classes that inherit PartitionedTable
   - Must supply self.insertSql with 'TABLENAME' replacing the actual table name
   - Must supply appropriate creationSql and partitionCreationSqlTemplate to the superclass constructor
   - Should NOT override method insert, which does something special for PartitionedTables
   - May override method partitionCreationParameters(self, partitionDetails) which returns a dictionary suitable for string formatting

   Every leaf class that inherits PartitionedTable should be aware of the module-level dictionary: databaseDependenciesForPartition
   If that leaf class has a partition that depends upon some other partition, then it must be added as a key to the dictionary
   databaseDependenciesForPartition. The value associated with that key is an iterable containing the classes that define the partitions
   on which this particular leaf class depends: Those that must already be created before the particular instance is created. This is
   most often because the particular partition table has one or more foreign keys referencing partition tables upon which it depends.
  """
  #-----------------------------------------------------------------------------------------------------------------
  partitionCreationLock = threading.RLock()
  def __init__ (self, name=None, logger=None, creationSql=None, partitionNameTemplate='%s', partitionCreationSqlTemplate='', weekInterval=None, **kwargs):
    super(PartitionedTable, self).__init__(name=name, logger=logger, creationSql=creationSql)
    self.partitionNameTemplate = partitionNameTemplate
    self.partitionCreationSqlTemplate = partitionCreationSqlTemplate
    self.weekInterval = weekInterval
    if not weekInterval:
      today = dt.date.today()
      self.weekInterval = mondayPairsIteratorFactory(today,today)
    self.insertSql = None

  #-----------------------------------------------------------------------------------------------------------------
  #def additionalCreationProcedures(self, databaseCursor):
    #self.createPartitions(databaseCursor, self.weekInterval)
  #-----------------------------------------------------------------------------------------------------------------
  def _createOwnPartition(self, databaseCursor, uniqueItems):
    """
    Internal method that assumes all precursor partitions are already in place before creating this one. Called
    from createPartitions(same parameters) to avoid bottomless recursion. Creates one or more partitions for
    this particular table, (more if uniqueItems has more than one element)
    side effect: Cursor's connection has been committed() by the time we return
    """
    self.logger.debug("%s - in createOwnPartition for %s",threading.currentThread().getName(),self.name)
    for x in uniqueItems:
      #self.logger.debug("DEBUG - item value is %s",x)
      partitionCreationParameters = self.partitionCreationParameters(x)
      partitionName = self.partitionNameTemplate % partitionCreationParameters["partitionName"]
      if partitionWasCreated(partitionName):
        #self.logger.debug("DEBUG - skipping creation of %s",partitionName)
        continue
      partitionCreationSql = self.partitionCreationSqlTemplate % partitionCreationParameters
      #self.logger.debug("%s - Sql for %s is %s",threading.currentThread().getName(),self.name,partitionCreationSql)
      aPartition = Table(name=partitionName, logger=self.logger, creationSql=partitionCreationSql)
      self.logger.debug("%s - savepoint createPartitions_%s",threading.currentThread().getName(), partitionName)
      databaseCursor.execute("savepoint createPartitions_%s" % partitionName)
      try:
        self.logger.debug("%s - creating %s", threading.currentThread().getName(), partitionName)
        aPartition._createSelf(databaseCursor)
        markPartitionCreated(partitionName)
        self.logger.debug("%s - successful - releasing savepoint", threading.currentThread().getName())
        databaseCursor.execute("release savepoint createPartitions_%s" % partitionName)
      except pg.ProgrammingError, x:
        self.logger.debug("%s -- Rolling back and releasing savepoint: Creating %s failed in createPartitions: %s", threading.currentThread().getName(), partitionName, str(x).strip())
        databaseCursor.execute("rollback to createPartitions_%s; release savepoint createPartitions_%s;" % (partitionName, partitionName))
      databaseCursor.connection.commit()

  #-----------------------------------------------------------------------------------------------------------------
  def createPartitions(self, databaseCursor, iterator):
    """
    Create this table's partition(s) and all the precursor partition(s) needed to support this one
    databaseCursor: as always
    iterator: Supplies at least one unique identifier (a date). If more than one then more than one (family of)
              partition(s) is created
    side effects: The cursor's connection will be rolled back or committed by the end of this method
    """
    self.logger.debug("%s - in createPartitions", threading.currentThread().getName())
    partitionTableClasses = getOrderedPartitionList([self.__class__])
    #self.logger.debug("DEBUG - Classes are %s",partitionTableClasses)
    uniqueItems = [x for x in iterator]
    for tableClass in partitionTableClasses:
      tableObject = self
      if not self.__class__ == tableClass:
        tableObject = tableClass(logger = self.logger)
      #self.logger.debug("DEBUG - Handling %s /w/ sql %s",tableObject.name,tableObject.partitionCreationSqlTemplate)
      tableObject._createOwnPartition(databaseCursor,uniqueItems)

  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self,partitioningData):
    """returns: a dictionary of string substitution parameters"""
    return {}
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
    dateRangeTuple = mondayPairsIteratorFactory(uniqueIdentifier, uniqueIdentifier).next()# create iterator and throw away
    partitionName = self.partitionCreationParameters(dateRangeTuple)["partitionName"]
    insertSql = self.insertSql.replace('TABLENAME', partitionName)
    try:
      databaseCursor.execute("savepoint %s" % partitionName)
      #self.logger.debug("%s - Trying to insert into %s", threading.currentThread().getName(), self.name)
      databaseCursor.execute(insertSql, row)
      databaseCursor.execute("release savepoint %s" % partitionName)
    except pg.ProgrammingError, x:
      self.logger.debug('%s - Rolling back and releasing savepoint: failed: %s', threading.currentThread().getName(), str(x).strip())
      databaseCursor.execute("rollback to %s; release savepoint %s;" % (partitionName, partitionName))
      databaseCursor.connection.commit() # This line added after of hours of blood, sweat, tears. Remove only per deathwish.

      altConnection, altCursor = alternateCursorFunction()
      dateIterator = mondayPairsIteratorFactory(uniqueIdentifier, uniqueIdentifier)
      try:
        self.createPartitions(altCursor,dateIterator)
      except pg.DatabaseError,x:
        self.logger.debug("%s - Failed to create partition(s) %s: %s:%s", threading.currentThread().getName(), partitionName, type(x), x)
      self.logger.debug("%s - trying to insert into %s for the second time", threading.currentThread().getName(), self.name)
      databaseCursor.execute(insertSql, row)

#=================================================================================================================
class ReportsTable(PartitionedTable):
  """Define the table 'reports'"""
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(ReportsTable, self).__init__(name='reports', logger=logger,
                                       creationSql="""
                                          CREATE TABLE reports (
                                              id serial NOT NULL,
                                              client_crash_date timestamp with time zone,
                                              date_processed timestamp with time zone,
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
                                              user_id character varying(50),
                                              started_datetime timestamp with time zone,
                                              completed_datetime timestamp with time zone,
                                              success boolean,
                                              truncated boolean,
                                              processor_notes text,
                                              user_comments character varying(1024),
                                              app_notes character varying(1024),
                                              distributor character varying(20),
                                              distributor_version character varying(20),
                                              topmost_filenames TEXT,
                                              addons_checked boolean,
                                              flash_version TEXT,
                                              hangid TEXT,
                                              process_type TEXT,
                                              release_channel TEXT
                                          );
                                          --CREATE TRIGGER reports_insert_trigger
                                          --    BEFORE INSERT ON reports
                                          --    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""",
                                       partitionCreationSqlTemplate="""
                                          CREATE TABLE %(partitionName)s (
                                              CONSTRAINT %(partitionName)s_date_check CHECK (TIMESTAMP with time zone '%(startDate)s UTC' <= date_processed and date_processed < TIMESTAMP with time zone '%(endDate)s UTC'),
                                              CONSTRAINT %(partitionName)s_unique_uuid unique (uuid),
                                              PRIMARY KEY(id)
                                          )
                                          INHERITS (reports);
                                          CREATE INDEX %(partitionName)s_date_processed_key ON %(partitionName)s (date_processed);
                                          CREATE INDEX %(partitionName)s_uuid_key ON %(partitionName)s (uuid);
                                          CREATE INDEX %(partitionName)s_url_key ON %(partitionName)s (url);
                                          CREATE INDEX %(partitionName)s_build_key ON %(partitionName)s (build);
                                          CREATE INDEX %(partitionName)s_product_version_key ON %(partitionName)s (product, version);
                                          CREATE INDEX %(partitionName)s_signature_date_processed_build_key ON %(partitionName)s (signature, date_processed, build);
                                          CREATE INDEX %(partitionName)s_hangid_idx ON %(partitionName)s (hangid);
                                          CREATE INDEX %(partitionName)s_reason ON %(partitionName)s (reason);
                                          """
                                      )
    self.columns = ("uuid", "client_crash_date", "date_processed", "product", "version", "build", "url", "install_age", "last_crash", "uptime", "email", "user_id", "user_comments", "app_notes", "distributor", "distributor_version", "topmost_filenames", "addons_checked", "flash_version", "hangid", "process_type", "release_channel")
    self.insertSql = """insert into TABLENAME
                            (uuid, client_crash_date, date_processed, product, version, build, url, install_age, last_crash, uptime, email, user_id, user_comments, app_notes, distributor, distributor_version, topmost_filenames, addons_checked, flash_version, hangid, process_type, release_channel) values
                            (%s,   %s,                %s,             %s,      %s,      %s,    %s,  %s,          %s,         %s,     %s,    %s,      %s,            %s,        %s,          %s,                  %s,                %s,             %s,            %s,     %s,           %s)"""
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

  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    databaseCursor.execute("""DROP RULE IF EXISTS rule_reports_partition ON reports;""")
    self.updateColumnDefinitions(databaseCursor)
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)

databaseDependenciesForSetup[ReportsTable] = []

#=================================================================================================================
class PriorityJobsTable(Table):
  """Define the table 'priorityjobs'"""
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, name="priorityjobs", logger=None, **kwargs):
    super(PriorityJobsTable, self).__init__(name=name, logger=logger,
                                            creationSql = """
                                                CREATE TABLE %s (
                                                    uuid varchar(255) NOT NULL PRIMARY KEY
                                                );""" % name)
databaseDependenciesForSetup[PriorityJobsTable] = []

#=================================================================================================================
class ProcessorsTable(Table):
  """Define the table 'processors'"""
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(ProcessorsTable, self).__init__(name = "processors", logger=logger,
                                        creationSql = """
                                            CREATE TABLE processors (
                                                id serial NOT NULL PRIMARY KEY,
                                                name varchar(255) NOT NULL UNIQUE,
                                                startdatetime timestamp with time zone NOT NULL,
                                                lastseendatetime timestamp with time zone
                                            );""")
  def updateDefinition(self, databaseCursor):
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)
    #if 'idx_processor_name' in indexesList:
      #databaseCursor.execute("""DROP INDEX idx_processor_name;
                                #ALTER TABLE processors ADD CONSTRAINT processors_name_key UNIQUE (name);""")
databaseDependenciesForSetup[ProcessorsTable] = []

#=================================================================================================================
class JobsTable(Table):
  """Define the table 'jobs'"""
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
                                            queueddatetime timestamp with time zone,
                                            starteddatetime timestamp with time zone,
                                            completeddatetime timestamp with time zone,
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
databaseDependenciesForSetup[JobsTable] = [ProcessorsTable]

#=================================================================================================================
class BugsTable(Table):
  """Define the table 'bug_associations'"""
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(BugsTable, self).__init__(name = "bugs", logger=logger,
                                        creationSql = """
                                            CREATE TABLE bugs (
                                                id int NOT NULL,
                                                status text,
                                                resolution text,
                                                short_desc text
                                            );
                                            ALTER TABLE ONLY bugs
                                                ADD CONSTRAINT bugs_pkey PRIMARY KEY (id);
                                            """)
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    if socorro_pg.tablesMatchingPattern(self.name) == []:
      #this table doesn't exist yet, create it
      self.create(databaseCursor)

databaseDependenciesForSetup[BugsTable] = []

#=================================================================================================================
class BugAssociationsTable(Table):
  """Define the table 'bug_associations'"""
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(BugAssociationsTable, self).__init__(name = "bug_associations", logger=logger,
                                        creationSql = """
                                            CREATE TABLE bug_associations (
                                                signature text NOT NULL,
                                                bug_id int NOT NULL
                                            );
                                            ALTER TABLE ONLY bug_associations
                                                ADD CONSTRAINT bug_associations_pkey PRIMARY KEY (signature, bug_id);
                                            CREATE INDEX idx_bug_associations_bug_id ON bug_associations (bug_id);
                                            ALTER TABLE bug_associations
                                                ADD CONSTRAINT bug_associations_bug_id_fkey FOREIGN KEY (bug_id) REFERENCES bugs(id) ON DELETE CASCADE;
                                            """)
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    if socorro_pg.tablesMatchingPattern(self.name) == []:
      #this table doesn't exist yet, create it
      self.create(databaseCursor)

databaseDependenciesForSetup[BugAssociationsTable] = [BugsTable]


#=================================================================================================================
class ServerStatusTable(Table):
  """Define the table 'server_status'"""
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(ServerStatusTable, self).__init__(name='server_status', logger=logger,
                                       creationSql="""
                                          CREATE TABLE server_status (
                                              id serial NOT NULL,
                                              date_recently_completed timestamp with time zone,
                                              date_oldest_job_queued timestamp with time zone,
                                              avg_process_sec real,
                                              avg_wait_sec real,
                                              waiting_job_count integer NOT NULL,
                                              processors_count integer NOT NULL,
                                              date_created timestamp with time zone NOT NULL
                                          );
                                          ALTER TABLE ONLY server_status
                                              ADD CONSTRAINT server_status_pkey PRIMARY KEY (id);
                                          CREATE INDEX idx_server_status_date ON server_status USING btree (date_created, id);
                                          """)
databaseDependenciesForSetup[ServerStatusTable] = []

#=================================================================================================================
class ReleaseEnum(DatabaseObject):
  def __init__(self,logger, **kwargs):
    super(ReleaseEnum, self).__init__(name='release_enum', logger=logger,
                                      creationSql="CREATE TYPE release_enum AS ENUM ('major', 'milestone', 'development');"
                                      )
  def drop(self, databaseCursor):
    databaseCursor.execute("drop type if exists %s cascade"%self.name)
databaseDependenciesForSetup[ReleaseEnum] = []

#=================================================================================================================
class ExtensionsTable(PartitionedTable):
  """Define the table 'extensions'"""
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(ExtensionsTable, self).__init__(name='extensions', logger=logger,
                                          creationSql="""
                                              CREATE TABLE extensions (
                                                  report_id integer NOT NULL,
                                                  date_processed timestamp with time zone,
                                                  extension_key integer NOT NULL,
                                                  extension_id text NOT NULL,
                                                  extension_version text
                                              );
                                              --CREATE TRIGGER extensions_insert_trigger
                                              --    BEFORE INSERT ON extensions
                                              --    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""",
                                          partitionCreationSqlTemplate="""
                                              CREATE TABLE %(partitionName)s (
                                                  CONSTRAINT %(partitionName)s_date_check CHECK (TIMESTAMP with time zone '%(startDate)s UTC' <= date_processed and date_processed < TIMESTAMP with time zone '%(endDate)s UTC'),
                                                  PRIMARY KEY (report_id, extension_key)
                                                  )
                                                  INHERITS (extensions);
                                              CREATE INDEX %(partitionName)s_report_id_date_key ON %(partitionName)s (report_id, date_processed, extension_key);
                                              CREATE INDEX %(partitionName)s_extension_id_extension_version_idx ON %(partitionName)s (extension_id, extension_version);
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
databaseDependenciesForPartition[ExtensionsTable] = [ReportsTable]
databaseDependenciesForSetup[ExtensionsTable] = []

#=================================================================================================================
class FramesTable(PartitionedTable):
  """Define the table 'frames'"""
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(FramesTable, self).__init__(name='frames', logger=logger,
                                      creationSql="""
                                          CREATE TABLE frames (
                                              report_id integer NOT NULL,
                                              date_processed timestamp with time zone,
                                              frame_num integer NOT NULL,
                                              signature varchar(255)
                                          );""",
                                      partitionCreationSqlTemplate="""
                                          CREATE TABLE %(partitionName)s (
                                              CONSTRAINT %(partitionName)s_date_check CHECK (TIMESTAMP with time zone '%(startDate)s UTC' <= date_processed and date_processed < TIMESTAMP with time zone '%(endDate)s UTC'),
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

  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    self.updateColumnDefinitions(databaseCursor)
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)

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
databaseDependenciesForPartition[FramesTable] = [ReportsTable]
databaseDependenciesForSetup[FramesTable] = []

#=================================================================================================================
class PluginsTable(Table):
  """Define the table 'plugins'"""
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, name="plugins", logger=None, **kwargs):
    super(PluginsTable, self).__init__(name=name, logger=logger,
                                            creationSql = """
                                                CREATE TABLE %s (
                                                    id SERIAL NOT NULL,
                                                    filename TEXT NOT NULL,
                                                    name TEXT NOT NULL,
                                                    PRIMARY KEY (id),
                                                    CONSTRAINT filename_name_key UNIQUE (filename, name)
                                                );""" % name)

  def insert(self, databaseCursor, rowTuple=None):
    databaseCursor.execute("insert into plugins (filename, name) values (%s, %s)", rowTuple)

databaseDependenciesForSetup[PluginsTable] = []

#=================================================================================================================
class PluginsReportsTable(PartitionedTable):
  """Define the table 'plugins_reports'"""
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(PluginsReportsTable, self).__init__(name='plugins_reports', logger=logger,
                                          creationSql="""
                                              CREATE TABLE plugins_reports (
                                                  report_id integer NOT NULL,
                                                  plugin_id integer NOT NULL,
                                                  date_processed timestamp with time zone,
                                                  version TEXT NOT NULL
                                              );""",

                                          partitionCreationSqlTemplate="""
                                              CREATE TABLE %(partitionName)s (
                                                  CONSTRAINT %(partitionName)s_date_check CHECK (TIMESTAMP with time zone '%(startDate)s UTC' <= date_processed and date_processed < TIMESTAMP with time zone '%(endDate)s UTC'),
                                                  PRIMARY KEY (report_id, plugin_id)
                                                  )
                                                  INHERITS (plugins_reports);
                                              CREATE INDEX %(partitionName)s_report_id_date_key ON %(partitionName)s (report_id, date_processed, plugin_id);
                                              ALTER TABLE %(partitionName)s
                                                  ADD CONSTRAINT %(partitionName)s_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_%(compressedStartDate)s(id) ON DELETE CASCADE;
                                              ALTER TABLE %(partitionName)s
                                                  ADD CONSTRAINT %(partitionName)s_plugin_id_fkey FOREIGN KEY (plugin_id) REFERENCES plugins(id) ON DELETE CASCADE;
                                              """)
    self.insertSql = """insert into TABLENAME (report_id, plugin_id, date_processed, version) values
                                              (%s, %s, %s, %s)"""
  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self, uniqueIdentifier):
    startDate, endDate = uniqueIdentifier
    startDateAsString = "%4d-%02d-%02d" % startDate.timetuple()[:3]
    compressedStartDateAsString = startDateAsString.replace("-", "")
    endDateAsString = "%4d-%02d-%02d" % endDate.timetuple()[:3]
    return { "partitionName": "plugins_reports_%s" % compressedStartDateAsString,
             "startDate": startDateAsString,
             "endDate": endDateAsString,
             "compressedStartDate": compressedStartDateAsString
           }
databaseDependenciesForPartition[PluginsReportsTable] = [ReportsTable]
databaseDependenciesForSetup[PluginsReportsTable] = [PluginsTable]

class RawAduTable(Table):
  """Define the table raw_adu"""
  def __init__(self, logger, **kwargs):
    super(RawAduTable,self).__init__(name='raw_adu', logger=logger,
                                     creationSql = """
                                       CREATE TABLE raw_adu (
                                         adu_count integer,
                                         date timestamp with time zone,
                                         product_name text,
                                         product_os_platform text,
                                         product_os_version text,
                                         product_version text
                                         );
                                         CREATE INDEX raw_adu_1_idx ON raw_adu (date,
                                         product_name,
                                         product_version,
                                         product_os_platform,
                                         product_os_version);
                                       """
                                    )
databaseDependenciesForSetup[RawAduTable] = []


#=================================================================================================================
class ReleasesRawTable(Table):
  """Define the table 'releases_raw'"""
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(ReleasesRawTable, self).__init__(name = "releases_raw", logger=logger,
                                        creationSql = """
                                            CREATE TABLE releases_raw (
                                                product_name citext not null,
                                                version text,
                                                platform text,
                                                build_id numeric,
                                                build_type text,
                                                beta_number int,
                                                repository text
                                            );
                                        """)
    self.insertSql = """INSERT INTO TABLENAME
                        (product, version, platform, buildid, buildtype,
                         beta_number, repository)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)"""

  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    if socorro_pg.tablesMatchingPattern(self.name) == []:
      #this table doesn't exist yet, create it
      self.create(databaseCursor)

databaseDependenciesForSetup[ReleasesRawTable] = []

#=================================================================================================================
class EmailCampaignsTable(Table):
  """Define the table 'email_campaigns'
     Notes: * email_count is populated after the record is inserted (TBD)
            * product/versions is denormalized to record versions used, but isn't searchable
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(EmailCampaignsTable, self).__init__(name = "email_campaigns", logger=logger,
                                        creationSql = """
                                            CREATE TABLE email_campaigns (
                                                id serial NOT NULL PRIMARY KEY,
                                                product TEXT NOT NULL,
                                                versions TEXT NOT NULL,
                                                signature TEXT NOT NULL,
                                                subject TEXT NOT NULL,
                                                body TEXT NOT NULL,
                                                start_date timestamp with time zone NOT NULL,
                                                end_date timestamp with time zone NOT NULL,
                                                email_count INTEGER DEFAULT 0,
                                                author TEXT NOT NULL,
                                                status TEXT NOT NULL DEFAULT 'stopped',
                                                date_created timestamp with time zone NOT NULL DEFAULT now());
                                            CREATE INDEX email_campaigns_product_signature_key ON email_campaigns (product, signature);
                                        """)
    self.insertSql = """INSERT INTO email_campaigns (product, versions, signature, subject, body, start_date, end_date, email_count, author)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id"""

  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    if socorro_pg.tablesMatchingPattern(self.name) == []:
      #this table doesn't exist yet, create it
      self.create(databaseCursor)

databaseDependenciesForSetup[EmailCampaignsTable] = []

#=================================================================================================================
class EmailContactsTable(Table):
  """Define the table 'email_contacts'
     Notes: subscribe_token - UUID which is used in urls for a user to manage their subscription.
            subscribe_status - Captures user's opt-out status. True - we can email, False - no email
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(EmailContactsTable, self).__init__(name = "email_contacts", logger=logger,
                                        creationSql = """
                                            CREATE TABLE email_contacts (
                                                id serial NOT NULL PRIMARY KEY,
                                                email              TEXT NOT NULL,
                                                subscribe_token    TEXT NOT NULL,
                                                subscribe_status   BOOLEAN DEFAULT TRUE,
                                                ooid               TEXT NOT NULL,
                                                crash_date         TIMESTAMP with time zone,
                                                CONSTRAINT email_contacts_email_unique UNIQUE (email),
                                                CONSTRAINT email_contacts_token_unique UNIQUE (subscribe_token)
                                                );
                                        """)
    self.insertSql = """INSERT INTO email_contacts (email, subscribe_token, ooid, crash_date) VALUES (%s, %s, %s, %s) RETURNING id"""
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    if socorro_pg.tablesMatchingPattern(self.name) == []:
      #this table doesn't exist yet, create it
      self.create(databaseCursor)

databaseDependenciesForSetup[EmailContactsTable] = []

#=================================================================================================================
class EmailCampaignsContactsTable(Table):
  """Define the table 'email_campaigns_contacts'
     Notes: Mapping table many to many
            Tracks status of emails to-be-sent
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(EmailCampaignsContactsTable, self).__init__(name = "email_campaigns_contacts", logger=logger,
                                        creationSql = """
                                            CREATE TABLE email_campaigns_contacts (
                                                email_campaigns_id INTEGER REFERENCES email_campaigns (id),
                                                email_contacts_id  INTEGER REFERENCES email_contacts (id),
                                                -- status will be ready, allocated to mailer _mailerid, sent, or failed (return code)
                                                status TEXT NOT NULL DEFAULT 'ready',
                                            CONSTRAINT email_campaigns_contacts_mapping_unique UNIQUE (email_campaigns_id, email_contacts_id)
                                            );
                                        """)
    self.insertSql = """INSERT INTO email_campaigns_contacts (email_campaigns_id, email_contacts) VALUES (%s, %s) RETURNING id"""

  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    if socorro_pg.tablesMatchingPattern(self.name) == []:
      #this table doesn't exist yet, create it
      self.create(databaseCursor)

databaseDependenciesForSetup[EmailCampaignsContactsTable] = [EmailCampaignsTable, EmailContactsTable]

#=================================================================================================================
class ReportsDuplicatesTable(Table):
  """Define the table 'reports_duplicates' and related functions
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(ReportsDuplicatesTable, self).__init__(name = "reports_duplicates", logger=logger,
                                        creationSql = """
                                           -- create table for possible duplicates
                                           -- not partitioned, for now

                                           create table reports_duplicates (
                                            uuid text not null primary key,
                                            duplicate_of text not null,
                                            date_processed timestamp not null
                                           );

                                           create index reports_duplicates_leader on reports_duplicates(duplicate_of);

                                           -- SQL function to make comparing timestamp deltas a bit
                                           -- less verbose

                                           create or replace function same_time_fuzzy(
                                            date1 timestamptz, date2 timestamptz,
                                            interval_secs1 int, interval_secs2 int
                                           ) returns boolean
                                           language sql as $f$
                                           SELECT
                                           -- return true if either interval is null
                                           -- so we don't exclude crashes missing data
                                           CASE WHEN $3 IS NULL THEN
                                            TRUE
                                           WHEN $4 IS NULL THEN
                                            TRUE
                                           -- otherwise check that the two timestamp deltas
                                           -- and the two interval deltas are within 60 sec
                                           -- of each other
                                           ELSE
                                            (
                                                extract ('epoch' from ( $2 - $1 ) ) -
                                                ( $4 - $3 )
                                            ) BETWEEN -60 AND 60
                                           END;
                                           $f$;

                                           -- function to be called hourly to update
                                           -- possible duplicates table

                                           create or replace function update_reports_duplicates (
                                            start_time timestamp, end_time timestamp )
                                           returns int
                                           set work_mem = '256MB'
                                           set temp_buffers = '128MB'
                                           language plpgsql as $f$
                                           declare new_dups INT;
                                           begin

                                           -- create a temporary table with the new duplicates
                                           -- for the hour
                                           -- this query contains the duplicate-finding algorithm
                                           -- so it will probably change frequently

                                           create temporary table new_reports_duplicates
                                           on commit drop
                                           as
                                           select follower.uuid as uuid,
                                            leader.uuid as duplicate_of,
                                            follower.date_processed
                                           from
                                           (
                                           select uuid,
                                               install_age,
                                               uptime,
                                               client_crash_date,
                                               date_processed,
                                             first_value(uuid)
                                             over ( partition by
                                                       product,
                                                       version,
                                                       build,
                                                       signature,
                                                       cpu_name,
                                                       cpu_info,
                                                       os_name,
                                                       os_version,
                                                       address,
                                                       topmost_filenames,
                                                       reason,
                                                       app_notes,
                                                       url
                                                    order by
                                                       client_crash_date,
                                                       uuid
                                                   ) as leader_uuid
                                              from reports
                                              where date_processed BETWEEN start_time AND end_time
                                            ) as follower
                                           JOIN
                                             ( select uuid, install_age, uptime, client_crash_date
                                               FROM reports
                                               where date_processed BETWEEN start_time AND end_time ) as leader
                                             ON follower.leader_uuid = leader.uuid
                                           WHERE ( same_time_fuzzy(leader.client_crash_date, follower.client_crash_date,
                                                             leader.uptime, follower.uptime)
                                                  OR follower.uptime < 60
                                                  )
                                             AND
                                            same_time_fuzzy(leader.client_crash_date, follower.client_crash_date,
                                                             leader.install_age, follower.install_age)
                                             AND follower.uuid <> leader.uuid;

                                           -- insert a copy of the leaders

                                           insert into new_reports_duplicates
                                           select uuid, uuid, date_processed
                                           from reports
                                           where uuid IN ( select duplicate_of
                                            from new_reports_duplicates )
                                            and date_processed BETWEEN start_time AND end_time;

                                           analyze new_reports_duplicates;

                                           select count(*) into new_dups from new_reports_duplicates;

                                           -- insert new duplicates into permanent table

                                           insert into reports_duplicates (uuid, duplicate_of, date_processed )
                                           select new_reports_duplicates.*
                                           from new_reports_duplicates
                                            left outer join reports_duplicates USING (uuid)
                                           where reports_duplicates.uuid IS NULL;

                                           -- done return number of dups found and exit
                                           RETURN new_dups;
                                           end;$f$;
                                        """)

databaseDependenciesForSetup[ReportsDuplicatesTable] = []

#=================================================================================================================
class ProductIdMapTable(Table):
  """Define the table 'product_productid_map'
     Notes: Provides override mapping for product name based on productID
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(ProductIdMapTable, self).__init__(name = "product_productid_map", logger=logger,
                                        creationSql = """
                                            CREATE TABLE product_productid_map (
                                              product_name citext NOT NULL,
                                              productid text NOT NULL,
                                              rewrite boolean NOT NULL DEFAULT FALSE,
                                              version_began numeric NOT NULL,
                                              version_ended numeric
                                            );
                                        """)
    self.insertSql = """INSERT INTO product_productid_map (product_name, productid, rewrite, version_began,
                        version_ended) values (%s, %s, %s, %s, %s)"""

databaseDependenciesForSetup[ProductIdMapTable] = []


#=================================================================================================================
class TransformRules(Table):
  """a single source for transformation rules based on the TransformRules classes
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger, **kwargs):
    super(TransformRules, self).__init__(name = "transform_rules", logger=logger,
                                        creationSql = """
                                        CREATE TABLE transform_rules (
                                          transform_rule_id SERIAL NOT NULL PRIMARY KEY,
                                          category CITEXT NOT NULL,
                                          rule_order INT NOT NULL,
                                          predicate TEXT NOT NULL DEFAULT '',
                                          predicate_args TEXT NOT NULL DEFAULT '',
                                          predicate_kwargs TEXT NOT NULL DEFAULT '',
                                          action TEXT NOT NULL DEFAULT '',
                                          action_args TEXT NOT NULL DEFAULT '',
                                          action_kwargs TEXT NOT NULL DEFAULT '',
                                          constraint transform_rules_key UNIQUE (category, rule_order)
                                              DEFERRABLE INITIALLY DEFERRED
                                        );
                                        """)
    self.insertSql = """INSERT INTO transform_rules (category, predicate, predicate_args, predicate_kwargs,
                        action, action_args, action_args) values (%s, %s, %s, %s, %s)"""

databaseDependenciesForSetup[TransformRules] = []


#-----------------------------------------------------------------------------------------------------------------
def connectToDatabase(config, logger):
  databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % config
  databaseConnection = pg.connect(databaseDSN)
  #databaseCursor = databaseConnection.cursor(cursor_factory=socorro_psy.LoggingCursor)
  #databaseCursor.setLogger(logger)
  databaseCursor = databaseConnection.cursor()
  return (databaseConnection, databaseCursor)

#-----------------------------------------------------------------------------------------------------------------
def setupDatabase(config, logger):
  databaseConnection, databaseCursor = connectToDatabase(config, logger)

  try:
    databaseCursor.execute("CREATE LANGUAGE plpgsql")
  except:
    databaseConnection.rollback()

  try:
    for aDatabaseObjectClass in getOrderedSetupList():
      aDatabaseObject = aDatabaseObjectClass(logger=logger)
      aDatabaseObject._createSelf(databaseCursor)
    databaseConnection.commit()
  except Exception,x:
    databaseConnection.rollback()
    socorro_util.reportExceptionAndAbort(logger)

#-----------------------------------------------------------------------------------------------------------------
def teardownDatabase(config,logger):
  global partitionCreationHistory
  databaseConnection,databaseCursor = connectToDatabase(config,logger)
  try:
    for databaseObjectClass in getOrderedSetupList():
      aDatabaseObject = databaseObjectClass(logger=logger)
      aDatabaseObject.drop(databaseCursor)
    databaseConnection.commit()
    partitionCreationHistory = set()
  except:
    databaseConnection.rollback()
    socorro_util.reportExceptionAndContinue(logger)

#-----------------------------------------------------------------------------------------------------------------
databaseObjectClassListForUpdate = [#ReportsTable,
                                    #DumpsTable,
                                    ExtensionsTable,
                                    FramesTable,
                                    ProcessorsTable,
                                    JobsTable,
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
# list all the tables that should have weekly partitions pre-created. This is a subclass of all the PartitionedTables
# since it may be that some PartitionedTables should not be pre-created.
databaseObjectClassListForWeeklyPartitions = [ReportsTable,
                                              #DumpsTable,
                                              FramesTable,
                                              ExtensionsTable,
                                              PluginsReportsTable,
                                             ]
#-----------------------------------------------------------------------------------------------------------------
def createPartitions(config, logger):
  """
  Create a set of partitions for all the tables known to be efficient when they are created prior to being needed.
  see the list databaseObjectClassListForWeeklyParitions above
  """
  databaseConnection, databaseCursor = connectToDatabase(config, logger)
  try:
    for aDatabaseObjectClass in databaseObjectClassListForWeeklyPartitions:
      weekIterator = mondayPairsIteratorFactory(config.startDate, config.endDate)
      aDatabaseObject = aDatabaseObjectClass(logger=logger)
      aDatabaseObject.createPartitions(databaseCursor, weekIterator)
      databaseConnection.commit()
  except:
    databaseConnection.rollback()
    socorro_util.reportExceptionAndAbort(logger)

