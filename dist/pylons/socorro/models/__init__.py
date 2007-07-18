from sqlalchemy import *
from sqlalchemy.ext.assignmapper import assign_mapper
from sqlalchemy.ext.selectresults import SelectResultsExt
from datetime import datetime
from socorro.lib import config, EmptyFilter
from cStringIO import StringIO
import sys
import os
import re

meta = DynamicMetaData()

class TruncatingString(types.TypeDecorator):
  """
  Truncating string type.
  
  By default, SQLAlchemy will throw an error if a string that is too long
  is inserted into the database. We subclass the default String type to
  automatically truncate to the correct length.
  """
  impl = types.String

  def convert_bind_param(self, value, engine):
    if value is None:
      return None
    return value[:self.length]

  def convert_result_value(self, value, engine):
    return value

"""
Define database structure.

The crash reports table is a parent table that all reports partitions
inherit.  No data is actually stored in this table.  If it is, we have
a problem.

Check constraints will be placed on reports to ensure this doesn't
happen.  See the PgsqlSetup class for how partitions and check
constraints are set up.
"""
reports_id_sequence = Sequence('seq_reports_id', meta)

reports_table = Table('reports', meta,
  Column('id', Integer, reports_id_sequence,
         default=text("nextval('seq_reports_id')"),
         primary_key=True),
  Column('date', DateTime(timezone=True)),
  Column('uuid', String(50), index=True, unique=True, nullable=False),
  Column('product', String(30)),
  Column('version', String(16)),
  Column('build', String(30)),
  Column('signature', TruncatingString(255), index=True),
  Column('url', TruncatingString(255), index=True),
  Column('install_age', Integer),
  Column('last_crash', Integer),
  Column('comments', TruncatingString(500)),
  Column('cpu_name', TruncatingString(100)),
  Column('cpu_info', TruncatingString(100)),
  Column('reason', TruncatingString(255)),
  Column('address', String(20)),
  Column('os_name', TruncatingString(100)),
  Column('os_version', TruncatingString(100)),
  Column('email', TruncatingString(100)),
  Column('build_date', DateTime()),
  Column('user_id', String(50))
)

def upgrade_reports(dbc):
  cursor = dbc.cursor()
  print "  Checking for reports.build_date...",
  cursor.execute("""SELECT 1 FROM pg_attribute
                    WHERE attrelid = 'reports'::regclass
                    AND attname = 'build_date'""");
  if cursor.rowcount == 0:
    print "adding"
    cursor.execute('ALTER TABLE reports ADD build_date timestamp without time zone')
    cursor.execute("""UPDATE reports
                      SET build_date =
                        (substring(build from 1 for 4) || '-' ||
                         substring(build from 5 for 2) || '-' ||
                         substring(build from 7 for 2) || ' ' ||
                         substring(build from 9 for 2) || ':00')
                           ::timestamp without time zone
                      WHERE build ~ '^\\\\d{10}'""")
    print "  Updated %s rows." % cursor.rowcount
  else:
    print "ok"
  print "  Checking for reports.user_id...",
  cursor.execute("""SELECT 1 FROM pg_attribute
                    WHERE attrelid = 'reports'::regclass
                    AND attname = 'user_id'""");
  if cursor.rowcount == 0:
    print "adding"
    cursor.execute('ALTER TABLE reports ADD user_id character(50)')
  else:
    print "ok"

frames_table = Table('frames', meta,
  Column('report_id', Integer, ForeignKey('reports.id'), primary_key=True),
  Column('frame_num', Integer, nullable=False, primary_key=True, autoincrement=False),
  Column('signature', TruncatingString(255))
)

modules_table = Table('modules', meta,
  Column('report_id', Integer, ForeignKey('reports.id'), primary_key=True),
  Column('module_key', Integer, primary_key=True, autoincrement=False),
  Column('filename', TruncatingString(40), nullable=False),
  Column('debug_id', String(40)),
  Column('module_version', TruncatingString(15)),
  Column('debug_filename', TruncatingString(40)),
)

def upgrade_modules(dbc):
  # See issue 25
  print "  Checking the datatype of modules.debug_id?...",
  cur = dbc.cursor()
  cur.execute("""SELECT atttypmod FROM pg_attribute
                 WHERE attrelid = 'modules'::regclass
                 AND attname = 'debug_id'""")
  (length,) = cur.fetchone()
  if int(length) >= modules_table.c.debug_id.type.length:
    print "ok"
  else:
    print "upgrading, previous size was %s" % length
    cur.execute("""ALTER TABLE modules ALTER debug_id
                   TYPE character varying(%(length)s)""",
                {'length': modules_table.c.debug_id.type.length})
  cur.close()

extensions_table = Table('extensions', meta, Column('report_id', Integer, ForeignKey('reports.id'), primary_key=True), Column('extension_key', Integer, primary_key=True, autoincrement=False),
  Column('extension_id', String(100), nullable=False),
  Column('extension_version', String(16))
)

dumps_table = Table('dumps', meta,
  Column('report_id', Integer, ForeignKey('reports.id'), primary_key=True),
  Column('data', TEXT())
)

branches_table = Table('branches', meta,
  Column('product', String(30), primary_key=True),
  Column('version', String(16), primary_key=True),
  Column('branch', String(24), nullable=False)
)

lock_function_definition = """
declare
begin
    LOCK reports IN ROW EXCLUSIVE MODE;
    LOCK frames IN ROW EXCLUSIVE MODE;
    LOCK dumps IN ROW EXCLUSIVE MODE;
    LOCK modules IN ROW EXCLUSIVE MODE;
    LOCK extensions IN ROW EXCLUSIVE MODE;
end;
"""

latest_partition_definition = """
declare
    partition integer;
begin
    SELECT INTO partition
        max(substring(tablename from '^reports_part(\\\\d+)$')::integer)
        FROM pg_tables WHERE tablename LIKE 'reports_part%';
    RETURN partition;
end;
"""

drop_rules_definition = """
declare
    partition integer;
begin
    SELECT INTO partition get_latest_partition();
    IF partition IS NULL THEN
        RETURN;
    END IF;

    DROP RULE rule_reports_partition ON reports;
    DROP RULE rule_frames_partition ON frames;
    DROP RULE rule_modules_partition ON modules;
    DROP RULE rule_extensions_partition ON extensions;
    DROP RULE rule_dumps_partition ON dumps;
end;
"""

create_rules_definition = """
declare
    cur_partition integer := partition;
    tablename text;
    cmd text;
begin
    IF cur_partition IS NULL THEN
        SELECT INTO cur_partition get_latest_partition();
    END IF;

    tablename := 'reports_part' || cur_partition::text;
    cmd := subst('CREATE OR REPLACE RULE rule_reports_partition AS
                  ON INSERT TO reports
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                 ARRAY[ quote_ident(tablename) ]);
    execute cmd;

    tablename := 'frames_part' || cur_partition::text;
    cmd := subst('CREATE OR REPLACE RULE rule_frames_partition AS
                  ON INSERT TO frames
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                  ARRAY [ quote_ident(tablename) ]);
    execute cmd;

    tablename := 'modules_part' || cur_partition::text;
    cmd := subst('CREATE OR REPLACE RULE rule_modules_partition AS
                  ON INSERT TO modules
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                 ARRAY[ quote_ident(tablename) ]);
    execute cmd;

    tablename := 'extensions_part' || cur_partition::text;
    cmd := subst('CREATE OR REPLACE RULE rule_extensions_partition AS
                  ON INSERT TO extensions
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                 ARRAY[ quote_ident(tablename) ]);
    execute cmd;

    tablename := 'dumps_part' || cur_partition::text;
    cmd := subst('CREATE OR REPLACE RULE rule_dumps_partition AS
                  ON INSERT TO dumps
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                 ARRAY[ quote_ident(tablename) ]);
    execute cmd;
end;
"""

make_partition_definition = """
declare
    new_partition integer;
    old_partition integer;
    old_start_date text;
    old_end_date text;
    old_end_id integer;
    old_tablename text;
    start_id integer := 0;
    tablename text;
    objname text;
    rulename text;
    cmd text;
begin
    PERFORM lock_for_changes();

    SELECT INTO old_partition get_latest_partition();

    IF old_partition IS NOT NULL THEN
        new_partition := old_partition + 1;

        old_tablename := 'reports_part' || old_partition::text;
        cmd := subst('SELECT max(id), min(date), max(date) FROM $$',
                     ARRAY[ quote_ident(old_tablename) ]);

        execute cmd into old_end_id, old_start_date, old_end_date;

        cmd := subst('ALTER TABLE $$ ADD CHECK( id <= $$ ),
                                     ADD CHECK( date >= $$ AND date <= $$)',
                     ARRAY[ quote_ident(old_tablename),
                            quote_literal(old_end_id),
                            quote_literal(old_start_date),
                            quote_literal(old_end_date) ]);
        execute cmd;

        old_tablename := 'frames_part' || old_partition::text;
        cmd := subst('ALTER TABLE $$ ADD CHECK( report_id <= $$ )',
                     ARRAY[ quote_ident(old_tablename),
                            quote_literal(old_end_id) ]);
        execute cmd;

        old_tablename := 'dumps_part' || old_partition::text;
        cmd := subst('ALTER TABLE $$ ADD CHECK( report_id <= $$ )',
                     ARRAY[ quote_ident(old_tablename),
                            quote_literal(old_end_id) ]);
        execute cmd;

        old_tablename := 'modules_part' || old_partition::text;
        cmd := subst('ALTER TABLE $$ ADD CHECK( report_id <= $$ )',
                         ARRAY[ quote_ident(old_tablename),
                            quote_literal(old_end_id) ]);
        execute cmd;

        old_tablename := 'extensions_part' || old_partition::text;
        cmd := subst('ALTER TABLE $$ ADD CHECK( report_id <= $$ )',
                     ARRAY[ quote_ident(old_tablename),
                            quote_literal(old_end_id) ]);
        execute cmd;

        start_id := old_end_id + 1;
    ELSE
        new_partition := 1;
    END IF;

    tablename := 'reports_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    PRIMARY KEY(id),
                    UNIQUE(uuid),
                    CHECK(id >= $$)
                  ) INHERITS (reports)',
                 ARRAY[ quote_ident(tablename),
                        quote_literal(start_id) ]);
    execute cmd;

    objname := 'idx_reports_part' || new_partition::text || '_date';
    cmd := subst('CREATE INDEX $$ ON $$ (date, product, version, build)',
                 ARRAY[ quote_ident(objname),
                        quote_ident(tablename) ]);
    execute cmd;

    objname := 'frames_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    CHECK(report_id >= $$),
                    PRIMARY KEY(report_id, frame_num),
                    FOREIGN KEY(report_id) REFERENCES $$ (id)
                  ) INHERITS (frames)',
                 ARRAY[ quote_ident(objname),
                        quote_literal(start_id),
                        quote_ident(tablename) ]);
    execute cmd;

    objname := 'modules_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    CHECK(report_id >= $$),
                    PRIMARY KEY(report_id, module_key),
                    FOREIGN KEY(report_id) REFERENCES $$ (id)
                  ) INHERITS (modules)',
                 ARRAY[ quote_ident(objname),
                        quote_literal(start_id),
                        quote_ident(tablename) ]);
    execute cmd;

    objname := 'extensions_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    CHECK(report_id >= $$),
                    PRIMARY KEY(report_id, extension_key),
                    FOREIGN KEY(report_id) REFERENCES $$ (id)
                  ) INHERITS (extensions)',
                 ARRAY[ quote_ident(objname),
                        quote_literal(start_id),
                        quote_ident(tablename) ]);
    execute cmd;

    objname := 'dumps_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    CHECK(report_id >= $$),
                    PRIMARY KEY(report_id),
                    FOREIGN KEY(report_id) REFERENCES $$ (id)
                  ) INHERITS (dumps)',
                 ARRAY[ quote_ident(objname),
                        quote_literal(start_id),
                        quote_ident(tablename) ]);
    execute cmd;

    PERFORM create_partition_rules(new_partition);
end;
"""

subst_definition = """
declare
    split text[] := string_to_array(str,'$$');
    result text[] := split[1:1];
begin
    for i in 2..array_upper(split,1) loop
        result := result || vals[i-1] || split[i];
    end loop;
    return array_to_string(result,'');
end;
"""

def define_functions(dbc):
  cur = dbc.cursor()
  cur.execute("""CREATE OR REPLACE FUNCTION lock_for_changes()
                 RETURNS void AS %(def)s
                 LANGUAGE plpgsql VOLATILE""",
              {'def': lock_function_definition})
  cur.execute("""CREATE OR REPLACE FUNCTION get_latest_partition()
                 RETURNS integer AS %(def)s LANGUAGE plpgsql VOLATILE""",
              {'def': latest_partition_definition})
  cur.execute("""CREATE OR REPLACE FUNCTION
                   create_partition_rules(partition integer)
                 RETURNS void AS %(def)s LANGUAGE plpgsql VOLATILE""",
              {'def': create_rules_definition})
  cur.execute("""CREATE OR REPLACE FUNCTION drop_partition_rules()
                 RETURNS void AS %(def)s LANGUAGE plpgsql VOLATILE""",
              {'def': drop_rules_definition})
  cur.execute("""CREATE OR REPLACE FUNCTION make_partition() RETURNS void
                 AS %(def)s LANGUAGE plpgsql VOLATILE""",
              {'def': make_partition_definition})
  cur.execute("""CREATE OR REPLACE FUNCTION subst(str text, vals text[])
                 RETURNS text AS %(def)s LANGUAGE plpgsql IMMUTABLE STRICT""",
              {'def': subst_definition})
  cur.close()

def lock_schema(dbc):
  cur = dbc.cursor()
  cur.execute("SELECT lock_for_changes()")
  cur.close()

def upgrade_db(dbc):
  print "Upgrading old database schema..."
  print "  Dropping old partitioning rules"
  cur = dbc.cursor()
  cur.execute("SELECT drop_partition_rules()")
  cur.close()
  upgrade_reports(dbc)
  upgrade_modules(dbc)

def ensure_partitions(dbc):
  print "Checking for database partitions...",
  cur = dbc.cursor()
  cur.execute("SELECT get_latest_partition()")
  (partition,) = cur.fetchone()
  if partition is None:
    print "No existing partition found, creating."
    cur.execute("SELECT make_partition()")
  else:
    print "Partition %s found." % partition
    cur.execute("SELECT create_partition_rules(%(p)s)", {'p': partition})
  cur.close()

"""
Indexes for our tables based on commonly used queries (subject to change!).

Manual index naming conventions:
  idx_table_col1_col2_col3

Note:
  Many indexes can be defined in table definitions, and those all start with
  "ix_".  Indexes we set up ourselves use "idx" to avoid name conflicts, etc.
"""
# Top crashers index, for use with the top crasher reports query.
Index('idx_reports_date', reports_table.c.date, reports_table.c.product, reports_table.c.version, reports_table.c.build)

fixupSpace = re.compile(r' (?=[\*&,])')
fixupComma = re.compile(r'(?<=,)(?! )')

filename_re = re.compile('[/\\\\]([^/\\\\]+)$')

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

def getEngine():
  """
  Utility function to retrieve the pylons engine in case we need it in a model
  for generic 'get' methods.
  """
  from pylons.database import create_engine
  return create_engine(pool_recycle=config.processorConnTimeout)

class BaseFrame(object):
  def __init__(self, report_id, frame_num, module_name, function, source, source_line, instruction):
    self.report_id = report_id
    self.frame_num = frame_num
    self.module_name = module_name
    self.signature = make_signature(module_name, function, source, source_line, instruction)
    self.function = function
    self.source = source
    self.source_line = source_line
    self.instruction = instruction
    self.source_filename = None
    self.source_link = None
    if source is not None:
      vcsinfo = source.split(":")
      if len(vcsinfo) == 4:
        (type, root, source_file, revision) = vcsinfo
        self.source_filename = source_file
        if type in config.vcsMappings:
          if root in config.vcsMappings[type]:
            self.source_link = config.vcsMappings[type][root] % {'file': source_file,
                                                                 'revision': revision, 
                                                                 'line': source_line} 
      else:
        self.source_filename = os.path.split(source)[1]

class Frame(BaseFrame):
  def __str__(self):
    if self.report_id is not None:
      return str(self.report_id)
    else:
      return ""

class Report(object):
  def __init__(self):
    self.date = datetime.now()
  def __str__(self):
    if self.id is not None:
      return str(self.id)
    else:
      return ""

  def read_header(self, fh):
    crashed_thread = ''
    module_count = 0

    for line in fh:
      self.add_dumptext(line)
      line = line[:-1]
      # empty line separates header data from thread data
      if line == '':
        return crashed_thread
      values = map(EmptyFilter, line.split("|"))
      if values[0] == 'OS':
        self.os_name = values[1]
        self.os_version = values[2]
      elif values[0] == 'CPU':
        self.cpu_name = values[1]
        self.cpu_info = values[2]
      elif values[0] == 'Crash':
        self.reason = values[1]
        self.address = values[2]
        crashed_thread = values[3]
      elif values[0] == 'Module':
        # Module|{Filename}|{Version}|{Debug Filename}|{Debug ID}|{Base Address}|Max Address}|{Main}
        # we should ignore modules with no filename
        if values[1]:
          self.modules.append(Module(self.id, module_count, values[1],
                                     values[4], values[2], values[3]))
          module_count += 1
  
  def read_stackframes(self, fh):
        threads = []
        for line in fh:
          self.add_dumptext(line)
          line = line.strip()
          (thread_num, frame_num, module_name, function, source, source_line, instruction) = map(EmptyFilter, line.split("|"))
          thread_num = int(thread_num)
          while thread_num >= len(threads):
            threads.append([])
          threads[thread_num].append(BaseFrame(self.id,
                                               frame_num,
                                               module_name,
                                               function,
                                               source,
                                               source_line,
                                               instruction))
        return threads
  
  def add_dumptext(self, text):
    dump = getattr(self, 'dumpText', '')
    self.dumpText = dump + text
  
  def finish_dumptext(self):
    if hasattr(self, 'dumpText'):
      self.dumps.append(Dump(self.id, self.dumpText))
  
  def get_all_threads(self):
    if "_threads" not in dir(self):
      if len(self.dumps) > 0 and len(self.dumps[0].data) > 0:
        try:
          # this sort of sucks, eh?
          r = Report()
          s = StringIO(self.dumps[0].data)
          self._crashed_thread = int(r.read_header(s))
          self._threads = r.read_stackframes(s)
        except:
          print >> sys.stderr, "Unexpected error: ", sys.exc_info()[0]
          self._crashed_thread = -1
          self._threads = []
      else:
        self._crashed_thread = -1
        self._threads = []
    return self._threads

  def get_crashed_thread(self):
    if "_crashed_thread" not in dir(self):
      self.get_all_threads()
    return self._crashed_thread
  
  threads = property(get_all_threads)
  crashed_thread = property(get_crashed_thread)

class Dump(object):
  def __init__(self, report_id, text):
    self.report_id = report_id
    self.data = text

  def __str__(self):
    return str(self.report_id)

class Branch(object):
  def __init__(self, product, version, branch):
    self.product = product
    self.version = version
    self.branch = branch
  
  @staticmethod
  def getBranches():
    """
    Return a list of distinct [branch] sorted by branch.
    """
    return select([branches_table.c.branch],
                  distinct=True,
                  order_by=[branches_table.c.branch],
                  engine=getEngine()).execute()

  @staticmethod
  def getProductBranches():
    """
    Return a list of distinct [product, branch] sorted by product name and branch.
    """
    return select([branches_table.c.product, branches_table.c.branch], 
                  distinct=True,
                  order_by=[branches_table.c.product, 
                            branches_table.c.branch],engine=getEngine()).execute()

  @staticmethod
  def getProducts():
    """
    Return a list of distinct [product] sorted by product.
    """
    return select([branches_table.c.product], 
                  distinct=True,
                  order_by=branches_table.c.product,engine=getEngine()).execute()

  @staticmethod
  def getProductVersions():
    """
    Return a list of distinct [product, version] sorted by product name and
    version.
    """
    return select([branches_table.c.product, branches_table.c.version],
                  distinct=True,
                  order_by=[branches_table.c.product,
                  branches_table.c.version], engine=getEngine()).execute()

def getCachedBranchData():
  """
  Return the result of getProductBranches, getProducts,
  and getProductVersions in a cached tuple.
  """
  import pylons
  # cache calls to this
  def branchData():
    products = [p for p in Branch.getProducts()]
    branches = [b for b in Branch.getBranches()]
    prodversions = [v for v in Branch.getProductVersions()]
    return (products, branches, prodversions)

  branchcache = pylons.cache.get_cache('query_branch_data')
  return branchcache.get_value("formfields", createfunc=branchData,
                               type="memory", expiretime=360)

class Module(object):
  def __init__(self, report_id, module_key, filename, debug_id, 
               module_version, debug_filename):
    self.report_id = report_id
    self.module_key = module_key
    self.filename = filename
    self.debug_id = debug_id
    self.module_version = module_version
    self.debug_filename = debug_filename

class Extension(object):
  def __init__(self, report_id, extension_key, extension_id, extension_version):
    self.report_id = report_id
    self.exension_key = extension_key
    self.extension_id = extension_id
    self.extension_version = extension_version

#
# Check whether we're running outside Pylons
#
try:
  ctx = None
  import socorro.lib.helpers
  from pylons.database import session_context, get_engine_conf
  ctx = session_context
  test = get_engine_conf()
except (ImportError, TypeError):
  from sqlalchemy.ext.sessioncontext import SessionContext
  localEngine = create_engine(config.processorDatabaseURI,
                              strategy="threadlocal",
                              poolclass=pool.QueuePool, 
                              pool_recycle=config.processorConnTimeout,
                              pool_size=1)
  def make_session():
    return create_session(bind_to=localEngine)
  ctx = SessionContext(make_session)

"""
This defines our relationships between the tables assembled above.  It
has to be near the bottom since it uses the objects defined after the
table definitions.
"""
frame_mapper = assign_mapper(ctx, Frame, frames_table)
report_mapper = assign_mapper(ctx, Report, reports_table, 
  properties = {
    'frames': relation(Frame, lazy=True, cascade="all, delete-orphan", 
                       order_by=[frames_table.c.frame_num]),
    'dumps': relation(Dump, lazy=True, cascade="all, delete-orphan"),
    'modules': relation(Module, lazy=True, cascade="all, delete-orphan"),
    'extensions': relation(Extension, lazy=True, cascade="all, delete-orphan"),
  }
)
dump_mapper = assign_mapper(ctx, Dump, dumps_table)
branch_mapper = assign_mapper(ctx, Branch, branches_table)
module_mapper = assign_mapper(ctx, Module, modules_table)
extension_mapper = assign_mapper(ctx, Extension, extensions_table)
