import psycopg2 as pg
import datetime as dt

import socorro.lib.psycopghelper as socorro_psy
import socorro.database.postgresql as socorro_pg

import socorro.lib.util as socorro_util

class FakeCursor(object):
  def __init__(self):
    pass
  def execute(self, sql):
    print sql

#-----------------------------------------------------------------------------------------------------------------
def iterateBetweenDatesByIsoWeekGeneratorCreator(minDate, maxDate):
  def anIterator():
    beginIsoYear, beginIsoWeek, beginIsoDay = minDate.isocalendar()
    oneWeek = dt.timedelta(7)
    aDate = minDate - dt.timedelta(beginIsoDay - 1) # begin on Monday before minDate
    while aDate < maxDate:
      yield aDate.isocalendar()[:2]
      aDate += oneWeek
  return anIterator

#-----------------------------------------------------------------------------------------------------------------
def emptyFunction():
  return ''

#==========================================================
class DatabaseObject(object):
  def __init__(self, name=None, logger=None, creationSql=None, **kwargs):
    super(Table, self).__init__()
    self.name = name
    self.creationSql = creationSql
    self.logger = logger
  def create(self, databaseCursor):
    databaseCursor.execute(self.creationSql)
    self.additionalCreationProcedures(databaseCursor)
  def additionalCreationProcedures(self, databaseCursor):
    pass
  def updateDefinition(self, databaseCursor):
    pass
  def createPartitions(self, databaseCursor, iterator):
    pass

Table = DatabaseObject

#-----------------------------------------------------------------------------------------------------------------
def nowIterator():
  yield dt.datetime.now().isocalendar()[:2]

#==========================================================
class PartitionedTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, name=None, logger=None, creationSql=None, partitionNameTemplate='%s', partitionCreationSqlTemplate='', partitionCreationIterablorCreator=nowIterator, **kwargs):
    super(PartitionedTable, self).__init__(name=name, logger=logger, creationSql=creationSql)
    self.partitionNameTemplate = partitionNameTemplate
    self.partitionCreationSqlTemplate = partitionCreationSqlTemplate
    self.partitionCreationIterablorCreator = partitionCreationIterablorCreator
  #-----------------------------------------------------------------------------------------------------------------
  def additionalCreationProcedures(self, databaseCursor):
    self.createPartitions(databaseCursor, self.partitionCreationIterablorCreator)
  #-----------------------------------------------------------------------------------------------------------------
  def createPartitions(self, databaseCursor, iterator):
    for x in iterator():
      partitionCreationParameters = self.partitionCreationParameters(x)
      partitionName = self.partitionNameTemplate % partitionCreationParameters["partitionName"]
      partitionCreationSql = self.partitionCreationSqlTemplate % partitionCreationParameters
      aPartition = Table(name=partitionName, logger=self.logger, creationSql=partitionCreationSql)
      databaseCursor.execute("savepoint %s" % partitionName)
      try:
        aPartition.create(databaseCursor)
        databaseCursor.execute("release savepoint %s" % partitionName)
      except:
        socorro_util.reportExceptionAndContinue(self.logger)
        databaseCursor.execute("rollback to %s; release savepoint %s;" % (partitionName, partitionName))
  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self):
    """must return a dictionary of string substitution parameters"""
    return {}

#==========================================================
class BranchesTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger):
    super(BranchesTable, self).__init__(name = "branches", logger=logger,
                                        creationSql = """
                                            CREATE TABLE branches (
                                                product character varying(30) NOT NULL,
                                                version character varying(16) NOT NULL,
                                                branch character varying(24) NOT NULL,
                                                PRIMARY KEY (product, version)
                                            );""")

#==========================================================
class DumpsTable(PartitionedTable):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger):
    super(DumpsTable, self).__init__(name='dumps', logger=logger,
                                     creationSql="""
                                         CREATE TABLE dumps (
                                             report_id integer NOT NULL,
                                             date timestamp NOT NULL,
                                             data text
                                         );
                                         CREATE TRIGGER dumps_insert_trigger
                                             BEFORE INSERT ON dumps
                                             FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""",
                                     partitionCreationSqlTemplate="""
                                         CREATE TABLE %(partitionName)s (
                                             CONSTRAINT %(partitionName)s_date_check CHECK ((to_char(date, 'IW') = '%(isoweek)s')),
                                             PRIMARY KEY (report_id)
                                         )
                                         INHERITS (dumps);
                                         CREATE INDEX %(partitionName)s_report_id_date_key ON %(partitionName)s (report_id, date);
                                         ALTER TABLE %(partitionName)s
                                             ADD CONSTRAINT %(partitionName)s_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_%(year)s%(isoweek)02s(id) ON DELETE CASCADE;
                                         """
                                    )
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    self.columnNameTypeDictionary = socorro_pg.columnNameTypeDictionaryForTable(self.name, databaseCursor)
    if 'date' not in self.columnNameTypeDictionary:
      databaseCursor.execute("""ALTER TABLE dumps
                                    ADD COLUMN date TIMESTAMP;""")
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)
    if 'dumps_pkey' in indexesList:
      databaseCursor.execute("""ALTER TABLE dumps
                                    DROP CONSTRAINT dumps_pkey;""")
    databaseCursor.execute("""DROP RULE IF EXISTS rule_dumps_partition ON dumps;""")
    triggersList = socorro_pg.triggersForTable(self.name, databaseCursor)
    if 'dumps_insert_trigger' not in triggersList:
      databaseCursor.execute("""CREATE TRIGGER dumps_insert_trigger
                                    BEFORE INSERT ON dumps
                                    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""")
  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self, uniqueIdentifier):
    year, isoweek = uniqueIdentifier
    return { "partitionName": "dumps_%d%02d" % (year, isoweek),
             "isoweek": "%02d" % isoweek,
             "year": "%d" % year
           }

#==========================================================
class ExtensionsTable(PartitionedTable):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger):
    super(ExtensionsTable, self).__init__(name='extensions', logger=logger,
                                          creationSql="""
                                              CREATE TABLE extensions (
                                                  report_id integer NOT NULL,
                                                  date timestamp NOT NULL,
                                                  extension_key integer NOT NULL,
                                                  extension_id character varying(100) NOT NULL,
                                                  extension_version character varying(16)
                                              );
                                              CREATE TRIGGER extensions_insert_trigger
                                                  BEFORE INSERT ON extensions
                                                  FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""",
                                          partitionCreationSqlTemplate="""
                                              CREATE TABLE %(partitionName)s (
                                                  CONSTRAINT %(partitionName)s_date_check CHECK ((to_char(date, 'IW') = '%(isoweek)s')),
                                                  PRIMARY KEY (report_id)
                                                  )
                                                  INHERITS (extensions);
                                              CREATE INDEX %(partitionName)s_report_id_date_key ON %(partitionName)s (report_id, date);
                                              ALTER TABLE %(partitionName)s
                                                  ADD CONSTRAINT %(partitionName)s_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_%(year)s%(isoweek)02s(id) ON DELETE CASCADE;
                                              """
                                          )
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    self.columnNameTypeDictionary = socorro_pg.columnNameTypeDictionaryForTable(self.name, databaseCursor)
    if 'date' not in self.columnNameTypeDictionary:
      databaseCursor.execute("""ALTER TABLE extensions
                                    ADD COLUMN date TIMESTAMP;""")
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)
    if 'extensions_pkey' in indexesList:
      databaseCursor.execute("""ALTER TABLE extensions
                                    DROP CONSTRAINT extensions_pkey;""")
    databaseCursor.execute("""DROP RULE IF EXISTS rule_extensions_partition ON extensions;""")
    triggersList = socorro_pg.triggersForTable(self.name, databaseCursor)
    if 'extensions_insert_trigger' not in triggersList:
      databaseCursor.execute("""CREATE TRIGGER extensions_insert_trigger
                                    BEFORE INSERT ON extensions
                                    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""")
  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self, uniqueIdentifier):
    year, isoweek = uniqueIdentifier
    return { "partitionName": "extensions_%d%02d" % (year, isoweek),
             "isoweek": "%02d" % isoweek,
             "year": "%d" % year
           }

#==========================================================
class FramesTable(PartitionedTable):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger):
    super(FramesTable, self).__init__(name='frames', logger=logger,
                                      creationSql="""
                                          CREATE TABLE frames (
                                              report_id integer NOT NULL,
                                              date timestamp NOT NULL,
                                              frame_num integer NOT NULL,
                                              signature varchar(255)
                                          );
                                          CREATE TRIGGER frames_insert_trigger
                                              BEFORE INSERT ON frames
                                              FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""",
                                      partitionCreationSqlTemplate="""
                                          CREATE TABLE %(partitionName)s (
                                              CONSTRAINT %(partitionName)s_date_check CHECK ((to_char(date, 'IW') = '%(isoweek)s')),
                                              PRIMARY KEY (report_id)
                                          )
                                          INHERITS (frames);
                                          CREATE INDEX %(partitionName)s_report_id_date_key ON %(partitionName)s (report_id, date);
                                          ALTER TABLE %(partitionName)s
                                              ADD CONSTRAINT %(partitionName)s_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_%(year)s%(isoweek)02s(id) ON DELETE CASCADE;
                                          """
                                     )
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    self.columnNameTypeDictionary = socorro_pg.columnNameTypeDictionaryForTable(self.name, databaseCursor)
    if 'date' not in self.columnNameTypeDictionary:
      databaseCursor.execute("""ALTER TABLE frames
                                    ADD COLUMN date TIMESTAMP;""")
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)
    if 'frames_pkey' in indexesList:
      databaseCursor.execute("""ALTER TABLE frames
                                    DROP CONSTRAINT frames_pkey;""")
    databaseCursor.execute("""DROP RULE IF EXISTS rule_frames_partition ON frames;""")
    triggersList = socorro_pg.triggersForTable(self.name, databaseCursor)
    if 'frames_insert_trigger' not in triggersList:
      databaseCursor.execute("""CREATE TRIGGER frames_insert_trigger
                                    BEFORE INSERT ON frames
                                    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""")
  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self, uniqueIdentifier):
    year, isoweek = uniqueIdentifier
    return { "partitionName": "frames_%d%02d" % (year, isoweek),
             "isoweek": "%02d" % isoweek,
             "year": "%d" % year
           }

#==========================================================
class JobsTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger):
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

#==========================================================
class PriorityJobsTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, name="priorityjobs", logger=None):
    super(PriorityJobsTable, self).__init__(name=name, logger=logger,
                                            creationSql = """
                                                CREATE TABLE %s (
                                                    uuid varchar(255) NOT NULL PRIMARY KEY
                                                );""" % name)

#==========================================================
class ProcessorsTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger):
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
    if 'idx_processor_name' in indexesList:
      databaseCursor.execute("""DROP INDEX idx_processor_name;
                                ALTER TABLE processors ADD CONSTRAINT processors_name_key UNIQUE (name);""")

#==========================================================
class ReportsTable(PartitionedTable):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger):
    super(ReportsTable, self).__init__(name='reports', logger=logger,
                                       creationSql="""
                                          CREATE TABLE reports (
                                              id serial NOT NULL,
                                              date timestamp with time zone NOT NULL,
                                              date_processed timestamp without time zone DEFAULT now() NOT NULL,
                                              uuid character varying(50) NOT NULL,
                                              product character varying(30),
                                              version character varying(16),
                                              build character varying(30),
                                              signature character varying(255),
                                              url character varying(255),
                                              install_age integer,
                                              last_crash integer,
                                              uptime integer,
                                              comments character varying(500),
                                              cpu_name character varying(100),
                                              cpu_info character varying(100),
                                              reason character varying(255),
                                              address character varying(20),
                                              os_name character varying(100),
                                              os_version character varying(100),
                                              email character varying(100),
                                              build_date timestamp without time zone,
                                              user_id character varying(50),
                                              starteddatetime timestamp without time zone,
                                              completeddatetime timestamp without time zone,
                                              success boolean,
                                              message text,
                                              truncated boolean
                                          );
                                          CREATE TRIGGER reports_insert_trigger
                                              BEFORE INSERT ON reports
                                              FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""",
                                       partitionCreationSqlTemplate="""
                                          CREATE TABLE %(partitionName)s (
                                              CONSTRAINT %(partitionName)s_date_check CHECK ((to_char(date, 'IW') = '%(isoweek)s')),
                                              PRIMARY KEY(id)
                                          )
                                          INHERITS (reports);
                                          CREATE INDEX %(partitionName)s_date_key ON %(partitionName)s (date);
                                          CREATE INDEX %(partitionName)s_uuid_key ON %(partitionName)s (uuid);
                                          CREATE INDEX %(partitionName)s_signature_key ON %(partitionName)s (signature);
                                          CREATE INDEX %(partitionName)s_url_key ON %(partitionName)s (url);
                                          --CREATE INDEX %(partitionName)s_uuid_date_key ON %(partitionName)s (uuid, date);
                                          CREATE INDEX %(partitionName)s_signature_date_key ON %(partitionName)s (signature, date);
                                          """
                                      )
  #-----------------------------------------------------------------------------------------------------------------
  def partitionCreationParameters(self, uniqueIdentifier):
    year, isoweek = uniqueIdentifier
    return { "partitionName": "reports_%d%02d" % (year, isoweek),
             "isoweek": "%02d" % isoweek,
             "year": "%d" % year
           }
  #-----------------------------------------------------------------------------------------------------------------
  def updateDefinition(self, databaseCursor):
    indexesList = socorro_pg.indexesForTable(self.name, databaseCursor)
    if 'reports_pkey' in indexesList:
      databaseCursor.execute("""ALTER TABLE reports DROP CONSTRAINT reports_pkey CASCADE;""")
    if 'idx_reports_date' in indexesList:
      databaseCursor.execute("""DROP INDEX idx_reports_date;""")
    if 'ix_reports_signature' in indexesList:
      databaseCursor.execute("""DROP INDEX ix_reports_signature;""")
    if 'ix_reports_url' in indexesList:
      databaseCursor.execute("""DROP INDEX ix_reports_url;""")
    if 'ix_reports_uuid' in indexesList:
      databaseCursor.execute("""DROP INDEX ix_reports_uuid;""")
    databaseCursor.execute("""DROP RULE IF EXISTS rule_reports_partition ON reports;""")
    triggersList = socorro_pg.triggersForTable(self.name, databaseCursor)
    if 'reports_insert_trigger' not in triggersList:
      databaseCursor.execute("""CREATE TRIGGER reports_insert_trigger
                                    BEFORE INSERT ON reports
                                    FOR EACH ROW EXECUTE PROCEDURE partition_insert_trigger();""")

#==========================================================
class ServerStatusTable(Table):
  #-----------------------------------------------------------------------------------------------------------------
  def __init__ (self, logger):
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

#==========================================================
class ParititioningTriggerScript(DatabaseObject):
  def __init__ (self, logger):
    super(ParititioningTriggerScript, self).__init__(name = "partition_insert_trigger", logger=logger,
                                                     creationSql = """
CREATE OR REPLACE FUNCTION partition_insert_trigger()
RETURNS TRIGGER AS $$
import socorro.database.server as ds
try:
  targetTableName = ds.targetTableName(TD["table_name"], TD['new']['date'])
  plpy.info(targetTableName)
  planName = ds.targetTableInsertPlanName (targetTableName)
  plpy.info("using plan: %s" % planName)
  values = ds.getValuesList(TD, SD, plpy)
  plpy.info(str(values))
  plpy.info('about to execute plan')
  result = plpy.execute(SD[planName], values)
  return None
except KeyError:  #no plan
  plpy.info("oops no plan for: %s" % planName)
  SD[planName] = ds.createNewInsertQueryPlan(TD, SD, targetTableName, planName, plpy)
  plpy.info('about to execute plan for second time')
  result = plpy.execute(SD[planName], values)
  return None
$$
LANGUAGE plpythonu;""")
  def updateDefinition(self, databaseCursor):
    databaseCursor.execute(self.creationSql)

#-----------------------------------------------------------------------------------------------------------------
def connectToDatabase(config, logger):
  databaseDSN = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % config
  databaseConnection = pg.connect(databaseDSN)
  databaseCursor = databaseConnection.cursor(cursor_factory=socorro_psy.LoggingCursor)
  databaseCursor.setLogger(logger)
  return (databaseConnection, databaseCursor)

#-----------------------------------------------------------------------------------------------------------------
databaseObjectClassListForSetup = [ParititioningTriggerScript,
                                   BranchesTable,
                                   ProcessorsTable,
                                   JobsTable,
                                   PriorityJobsTable,
                                   ReportsTable,
                                   DumpsTable,
                                   FramesTable,
                                   ExtensionsTable,
                                   ServerStatusTable,
                                  ]

#-----------------------------------------------------------------------------------------------------------------
def setupDatabase(config, logger):
  databaseConnection, databaseCursor = connectToDatabase(config, logger)
  try:
    try:
      databaseCursor.execute("CREATE LANGUAGE plpythonu")
    except:
      databaseConnection.rollback()
    for aDatabaseObjectClass in databaseObjectClassListForSetup:
      aDatabaseObject = aDatabaseObjectClass(logger=logger)
      aDatabaseObject.create(databaseCursor)
    databaseConnection.commit()
  except:
    databaseConnection.rollback()
    socorro_util.reportExceptionAndAbort(logger)

#-----------------------------------------------------------------------------------------------------------------
databaseObjectClassListForUpdate = [ParititioningTriggerScript,
                                   BranchesTable,
                                   ProcessorsTable,
                                   JobsTable,
                                   PriorityJobsTable,
                                   ReportsTable,
                                   DumpsTable,
                                   FramesTable,
                                   ExtensionsTable,
                                   ServerStatusTable
                                  ]
#-----------------------------------------------------------------------------------------------------------------
def updateDatabase(config, logger):
  databaseConnection, databaseCursor = connectToDatabase(config, logger)
  try:
    try:
      databaseCursor.execute("CREATE LANGUAGE plpythonu")
    except:
      databaseConnection.rollback()
    for aDatabaseObjectClass in databaseObjectClassListForUpdate:
      aDatabaseObject = aDatabaseObjectClass(logger=logger)
      aDatabaseObject.updateDefinition(databaseCursor)
    databaseConnection.commit()
  except:
    databaseConnection.rollback()
    socorro_util.reportExceptionAndAbort(logger)


