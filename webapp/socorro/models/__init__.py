from sqlalchemy import *
from sqlalchemy.ext.assignmapper import assign_mapper
from sqlalchemy.ext.selectresults import SelectResultsExt

from pylons.database import session_context
from datetime import datetime

meta = DynamicMetaData()

"""
Define database structure.

The crash reports table is a parent table that all reports partitions
inherit.  No data is actually stored in this table.  If it is, we have
a problem.

Check constraints will be placed on reports to ensure this doesn't
happen.  See the PgsqlSetup class for how partitions and check
constraints are set up.
"""
reports_table = Table('reports', meta,
  Column('id', Integer, primary_key=True, autoincrement=True),
  Column('date', DateTime),
  Column('uuid', String(50), index=True, unique=True, nullable=False),
  Column('product', String(20)),
  Column('version', String(10)),
  Column('build', String(10)),
  Column('signature', String(255), index=True),
  Column('url', String(255), index=True),
  Column('install_age', Integer),
  Column('last_crash', Integer),
  Column('comments', String(500)),
  Column('cpu_name', String(100)),
  Column('cpu_info', String(100)),
  Column('reason', String(255)),
  Column('address', String(20)),
  Column('os_name', String(100)),
  Column('os_version', String(100))
)

frames_table = Table('frames', meta,
  Column('report_id', Integer, ForeignKey('reports.id'), primary_key=True),
  Column('frame_num', Integer, nullable=False, primary_key=True),
  Column('module_name', String(50)),
  Column('function', String(100)),
  Column('source', String(200)),
  Column('source_line', Integer),
  Column('instruction', String(10))
)

dumps_table = Table('dumps', meta,
  Column('report_id', Integer, ForeignKey('reports.id'), primary_key=True),
  Column('data', String(50000))
)

"""
Indexes for our tables based on commonly used queries (subject to change!).

Manual index naming conventions:
  idx_table_col1_col2_col3

Note:
  Many indexes can be defined in table definitions, and those all start with
  "ix_".  Indexes we set up ourselves use "idx" to avoid name conflicts, etc.
"""
# Top crashers index, for use with the top crasher reports query.
Index('idx_reports_product_version_build',reports_table.c.product, reports_table.c.version, reports_table.c.build)


def EmptyFilter(x):
  """Return None if the argument is an empty string, otherwise
     return the argument."""
  if x == '':
    return None
  return x

class Frame(object):
  def __str__(self):
    if self.report_id is not None:
      return str(self.report_id)
    else:
      return ""

  def readline(self, line):
    frame_data = dict(zip(['thread_num', 'frame_num', 'module_name',
                           'function', 'source', 'source_line',
                           'instruction'],
                          map(EmptyFilter, line.split("|"))))
    self.__dict__.update(frame_data)

  def signature(self):
    if self.function is not None:
      return self.function

    if self.source is not None and self.source_line is not None:
      return '%s#%s' % (self.source, self.source_line)

    if self.module_name is not None:
      # Do we want to normalize this against the module base address?
      # Or does breakpad already do this for us? (I doubt it!)
      # This is a moot point until minidump_stackwalk gives us
      # the module enumeration.
      return '%s@%s' % (self.module_name, self.instruction)

    return '@%s' % self.instruction

class Report(object):
  def __init__(self):
    self.date = datetime.now()

  def __str__(self):
    if self.report_id is not None:
      return str(self.report_id)
    else:
      return ""

  def read_header(self, fh):
    crashed_thread = None
    for line in fh:
      line = line[:-1]
      # empty line separates header data from thread data
      if line == '':
        return int(crashed_thread)
      values = line.split("|")
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

class Dump(object):
  def __str__(self):
    if self.report_id is not None:
      return str(self.report_id)
    else:
      return ""

#
# Check whether we're running outside Pylons
#
ctx = None
try:
  import paste.deploy
  if paste.deploy.CONFIG.has_key("app_conf"):
    ctx = session_context
except AttributeError:
  from socorro.lib import config
  from sqlalchemy.ext.sessioncontext import SessionContext
  localEngine = create_engine(config.processorDatabaseURI)
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
    'dumps': relation(Dump, lazy=True, cascade="all, delete-orphan")
  }
)
dump_mapper = assign_mapper(ctx, Dump, dumps_table)
