import errno
import logging
import os

import psycopg2

import socorro.lib.ConfigurationManager as configurationManager
import socorro.database.postgresql as postg
import socorro.database.schema as schema

from   socorro.unittest.testlib.loggerForTest import TestingLogger
from   socorro.unittest.testlib.testDB import TestDB

import dbTestconfig as testConfig

testTableNames = [
  "foo",
  "foo_1",
  "foo_2",
  "a_foo",
  "boot",
  "rip",
  ]
testTablePatterns = {
  'foo%':['foo','foo_1','foo_2',],
  'foo_%':['foo_1','foo_2',],
  '%foo':['foo','a_foo',],
  '%oo%':['foo','foo_1','foo_2','a_foo','boot'],
  'rip':['rip'],
  'rap':[],
  }
class Me(): # not quite "self"
  """
  I need stuff to be initialized once per module. Rather than having a bazillion globals, lets just have 'me'
  """
  pass
me = None

def setup_module():
  global me
  if me:
    return
  me = Me()
  # config gets messed up by some tests. Use this one during module setup and teardown
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Postgresql Utils')
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass
  me.logFilePathname = me.config.logFilePathname
  if not me.logFilePathname:
    me.logFilePathname = 'logs/db_test.log'
  logFileDir = os.path.split(me.logFilePathname)[0]
  try:
    os.makedirs(logFileDir)
  except OSError,x:
    if errno.EEXIST == x.errno: pass
    else: raise
  f = open(me.logFilePathname,'w')
  f.close()
  fileLog = logging.FileHandler(me.logFilePathname, 'a')
  fileLog.setLevel(logging.DEBUG)
  fileLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
  fileLog.setFormatter(fileLogFormatter)
  me.logger = logging.getLogger("testPostresql")
  me.logger.addHandler(fileLog)
  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)

def teardown_module():
  try:
    os.unlink(me.logFilePathname)
  except:
    pass

class TestPostgresql:
  def setUp(self):
    global me
    # config gets messed up by some tests. Use this one by preference
    self.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Postgresql Utils')
    for i in self.config:
      try:
        self.config[i] = self.config.get(i)%(replDict)
      except:
        pass
    self.connection = psycopg2.connect(me.dsn)
    self.testDB = TestDB()

  def tearDown(self):
    cursor = self.connection.cursor()
    dropSql = "drop table if exists %s"
    for tn in testTableNames:
      cursor.execute(dropSql%tn)
    self.connection.commit()
    self.connection.close()
  
  def testTablesMatchingPattern(self):
    cursor = self.connection.cursor()
    createSql = "CREATE TABLE %s (id integer)" # postgresql allows empty tables, but it makes me itch...
    for tn in testTableNames:
      cursor.execute(createSql%tn)
    self.connection.commit()
    for pat in testTablePatterns:
      result = postg.tablesMatchingPattern(pat,cursor)
      expected = testTablePatterns[pat]
      assert set(expected)==set(result), "for %s: expected:%s, result:%s"%(pat,expected,result)
    self.connection.commit()
    
  def testTriggersForTable(self):
    global me
    cursor = self.connection.cursor()
    setupSql = """
    DROP TABLE IF EXISTS ttrigs;
    CREATE TABLE ttrigs (id serial);
    """
    makeTriggerSql = """
    CREATE OR REPLACE FUNCTION check_trigger() returns trigger AS '
      BEGIN
        RETURN new;
      END
      ' LANGUAGE plpgsql;
    CREATE TRIGGER check_trigger_t AFTER INSERT ON ttrigs FOR EACH ROW EXECUTE PROCEDURE check_trigger();
    """
    try:
      cursor.execute(setupSql)
      self.connection.commit()
      theList = postg.triggersForTable('ttrigs',cursor)
      assert [] == theList
      cursor.execute(makeTriggerSql)
      self.connection.commit()
      theList = postg.triggersForTable('ttrigs',cursor)
      assert ['check_trigger_t'] == theList
      cursor.execute("CREATE TRIGGER check_trigger_2 AFTER UPDATE ON ttrigs FOR EACH ROW EXECUTE PROCEDURE check_trigger();")
      self.connection.commit()
      theList = postg.triggersForTable('ttrigs',cursor)
      assert set(['check_trigger_t', 'check_trigger_2']) == set(theList),'but got %s'%(set(theList),)
    finally:
      cursor.execute("DROP TABLE IF EXISTS ttrigs")
      self.connection.commit()
    
  def testIndexesForTable(self):
    global me
    cursor = self.connection.cursor()
    setupSql = """
    DROP TABLE IF EXISTS tindex;
    CREATE TABLE tindex (id serial,i integer, f float);
    """
    try:
      cursor.execute(setupSql)
      self.connection.commit()
      indices = postg.indexesForTable('tindex',cursor)
      assert [] == indices
      cursor.execute("CREATE INDEX ti_id ON tindex (id);")
      self.connection.commit()
      indices = postg.indexesForTable('tindex',cursor)
      assert ['ti_id'] == indices
      cursor.execute("CREATE INDEX ti_i ON tindex (i);")
      self.connection.commit()
      indices = postg.indexesForTable('tindex',cursor)
      assert set(['ti_id','ti_i']) == set(indices), "but got %s"%(set(indices))
      cursor.execute("CREATE INDEX ti_i_f ON tindex (i,f);")
      self.connection.commit()
      indices = postg.indexesForTable('tindex',cursor)
      assert set(['ti_id','ti_i','ti_i_f']) == set(indices), 'but %s'%(indices)
    finally:
      cursor.execute("DROP TABLE IF EXISTS tindex;")
      self.connection.commit()
  
  def testRulesForTable(self):
    global me
    cursor = self.connection.cursor()
    setupSql = """
    DROP TABLE IF EXISTS trules;
    CREATE TABLE trules (id serial,i integer);
    """
    try:
      cursor.execute(setupSql)
      self.connection.commit()
      rules = postg.rulesForTable('trules',cursor)
      assert [] == rules
      cursor.execute("CREATE RULE notify_me AS ON UPDATE TO trules DO NOTIFY trules;")
      self.connection.commit()
      assert ['notify_me'] == postg.rulesForTable('trules',cursor)
    finally:
      cursor.execute("DROP TABLE IF EXISTS trules;")
      self.connection.commit()

  def testContraintsAndTypeForTable(self):
    global me
    setupSql = """
    DROP TABLE IF EXISTS tcnt;
    CREATE TABLE tcnt (id integer, i integer);
    """
    cursor = self.connection.cursor()
    try:
      cursor.execute(setupSql)
      self.connection.commit()
      assert [] == postg.constraintsAndTypeForTable('tcnt',cursor)
      cursor.execute("ALTER TABLE tcnt ADD CONSTRAINT tcnt_pkey PRIMARY KEY(id)")
      self.connection.commit()
      assert [('tcnt_pkey','p')] == postg.constraintsAndTypeForTable('tcnt',cursor)
      cursor.execute("ALTER TABLE tcnt ADD CONSTRAINT tcnt_nnu UNIQUE(i)")
      self.connection.commit()
      assert set([('tcnt_pkey', 'p'), ('tcnt_nnu', 'u')]) == set(postg.constraintsAndTypeForTable('tcnt',cursor))
      fkSql = setupSql.replace('tcnt','fkcnt')
      cursor.execute(fkSql)
      self.connection.commit()
      cursor.execute("ALTER TABLE fkcnt ADD CONSTRAINT fk_cn_id_fkey FOREIGN KEY(i) REFERENCES tcnt(id)")
      self.connection.commit()
      assert [('fk_cn_id_fkey', 'f')] == postg.constraintsAndTypeForTable('fkcnt',cursor)
    finally:
      cursor.execute("DROP TABLE IF EXISTS tcnt, fkcnt CASCADE")
      self.connection.commit()
    
  def testColumnNameTypeDictionaryForTable(self):
    global me
    dropSql = "DROP TABLE IF EXISTS typet;"
    # Each creation sql shall have one new line per column with a comment: --type which is the postgresql type of that column
    # The expected types are programatically extracted from the creation sql and depend on that format
    tableData = [
      ("numeric types",
       """CREATE TABLE typet (
           s serial,         --int4
           z bigserial,      --int8
           i smallint,       --int2
           j integer,        --int4
           i2 int2,          --int2
           i4 int4,          --int4
           i8 int8,          --int8
           k bigint,         --int8
           c3 decimal(3),    --numeric
           n2 numeric(2),    --numeric
           c33 decimal(3,3), --numeric
           n52 numeric(5,2), --numeric
           r real,           --float4
           d double precision --float8
           );
       """,),
      ("char types",
       """CREATE TABLE typet (
           v varchar(10), --varchar
           w varchar(20), --varchar
           x varchar,     --varchar
           b char,        --bpchar
           c char(10),    --bpchar
           d char(20),    --bpchar
           t text         --text
           );
       """,),
      ("date and time types",
       """CREATE TABLE typet (
           ts timestamp,                         --timestamp
           tsp0 timestamp(0),                    --timestamp
           tsp1 timestamp(1),                    --timestamp
           tsz  timestamp without time zone,     --timestamp
           tsz2 timestamp(2) without time zone,  --timestamp
           tsz3 timestamp(3) without time zone,  --timestamp
           tss  timestamp with time zone,        --timestamptz
           tss2 timestamp(2) with time zone,     --timestamptz
           tss3 timestamp(3) with time zone,     --timestamptz
           i  interval,                          --interval
           i0 interval(0),                       --interval
           i4 interval(4),                       --interval
           d date,                               --date
           t time,                               --time
           t0  time(0),                          --time
           t5  time(5),                          --time
           tz  time with time zone,              --timetz
           tz0 time(0) with time zone,           --timetz
           tz6 time(6) with time zone            --timetz
           );
       """,),
      ("geometric types",
       """CREATE TABLE typet (
           pt point,   --point
           l line,     --line
           s lseg,     --lseg
           b box,      --box
           p path,     --path
           pg polygon, --polygon
           c circle    --circle
           );
       """,),
      ("miscellany",
       """CREATE TABLE typet (
           by bytea,              --bytea  
           bo boolean,            --bool   
           c cidr,                --cidr   
           i inet,                --inet   
           m macaddr,             --macaddr
           b1 bit,                --bit    
           b2 bit(2),             --bit    
           bv bit varying,        --varbit 
           bv3 bit varying(3),    --varbit 
           at1_ text[],           --_text  
           ai1_ integer[],        --_int4  
           at1_2 text[2],         --_text  
           ai1_3 integer[3],      --_int4  
           ac2_  char[][],        --_bpchar
           av2_12 varchar[1][2],  --_varchar
           av1_3 varchar ARRAY[3] --_varchar
           );
       """,),
      ]
    cursor = self.connection.cursor()
    cursor.execute(dropSql)
    self.connection.commit()
    for tup in tableData:
      try:
        expected = _extractExpectedFromSql(tup[1])
        cursor.execute(tup[1])
        self.connection.commit()
        got = postg.columnNameTypeDictionaryForTable('typet',cursor)
        assert expected == got, 'For %s, expected %s, got %s'%(tup[0],expected,got)
      finally:
        cursor.execute(dropSql)
        self.connection.commit()
  
  def testChildTablesForTable(self):
    global me
    cursor = self.connection.cursor()
    cursor.execute("DROP TABLE IF EXISTS top,second,third,fourth CASCADE")
    self.connection.commit()
    try:
      cursor.execute("CREATE TABLE top (id serial)")
      self.connection.commit()
      assert [] == postg.childTablesForTable('top',cursor)
      cursor.execute("CREATE TABLE second(arity integer) INHERITS (top)")
      self.connection.commit()
      assert ['second'] == postg.childTablesForTable('top',cursor)
      assert [] == postg.childTablesForTable('second',cursor)
      cursor.execute("CREATE TABLE third(color text) INHERITS (top)")
      self.connection.commit()
      assert set(['second','third']) == set(postg.childTablesForTable('top',cursor))
      assert [] == postg.childTablesForTable('second',cursor)
      assert [] == postg.childTablesForTable('third',cursor)
      cursor.execute("CREATE TABLE fourth(strangeness text) INHERITS (second)")
      self.connection.commit()
      assert set(['second','third']) == set(postg.childTablesForTable('top',cursor))
      assert ['fourth'] == postg.childTablesForTable('second',cursor)
      assert [] == postg.childTablesForTable('third',cursor)
      assert [] == postg.childTablesForTable('fourth',cursor)
    finally:
      cursor.execute("DROP TABLE IF EXISTS top,second,third,fourth CASCADE")
      self.connection.commit()

  def testConnectionStatus(self):
    global me
    cursor = self.connection.cursor()
    assert "Status: READY, Transaction Status: IDLE" == postg.connectionStatus(self.connection)
    try:
      cursor.execute("create table tcon(id integer)")
      assert "Status: BEGIN, Transaction Status: INTRANS" == postg.connectionStatus(self.connection)
      self.connection.commit()
      try:
        cursor.execute("select name from tcon")
      except:
        assert "Status: BEGIN, Transaction Status: INERROR" == postg.connectionStatus(self.connection)
        self.connection.rollback()
    finally:
      cursor.execute("drop table if exists tcon")
      self.connection.commit()
      
def _extractExpectedFromSql(sql):
  """Expect newline separated columns with trailing '--type' per line, nothing interesting unless there is a '--' comment"""
  ret = {}
  cols = sql.split("\n")
  for c in cols:
    if '--' in c:
      cname = c.split()[0]
      ctype = c.split('--')[1].strip()
      ret[cname] = ctype

  return ret
