from sqlalchemy import *
from sqlalchemy.ext.assignmapper import assign_mapper
from sqlalchemy.ext.selectresults import SelectResultsExt

from pylons.database import session_context
from datetime import datetime

import sys
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
  Column('email', TruncatingString(100))
)

frames_table = Table('frames', meta,
  Column('report_id', Integer, ForeignKey('reports.id'), primary_key=True),
  Column('frame_num', Integer, nullable=False, primary_key=True, autoincrement=False),
  Column('signature', TruncatingString(255))
)

modules_table = Table('modules', meta,
  Column('report_id', Integer, ForeignKey('reports.id'), primary_key=True),
  Column('module_key', Integer, primary_key=True, autoincrement=False),
  Column('filename', TruncatingString(40), nullable=False),
  Column('debug_id', String(33), nullable=False),
  Column('module_version', TruncatingString(15)),
  Column('debug_filename', TruncatingString(40)),
)

extensions_table = Table('extensions', meta,
  Column('report_id', Integer, ForeignKey('reports.id'), primary_key=True),
  Column('extension_key', Integer, primary_key=True, autoincrement=False),
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

filename_re = re.compile('[/\\\\]([^/\\\\]+)$')

def make_signature(module_name, function, source, source_line, instruction):
  if function is not None:
    return function

  if source is not None and source_line is not None:
    filename = filename_re.search(source)
    if filename is not None:
      source = filename.group(1)

    return '%s#%s' % (source, source_line)

  if module_name is not None:
    return '%s@%s' % (module_name, instruction)

  return '@%s' % instruction

class Frame(object):
  def __str__(self):
    if self.report_id is not None:
      return str(self.report_id)
    else:
      return ""

  def __init__(self, report_id, frame_num, module_name, function, source, source_line, instruction):
    self.report_id = report_id
    self.frame_num = frame_num
    self.signature = make_signature(module_name, function, source, source_line, instruction)

class Report(object):
  def __init__(self):
    self.date = datetime.now()

  def __str__(self):
    if self.id is not None:
      return str(self.id)
    else:
      return ""

  def read_header(self, fh):
    self.dumpText = ""

    crashed_thread = ''
    module_count = 0

    for line in fh:
      self.add_dumptext(line)
      line = line[:-1]
      # empty line separates header data from thread data
      if line == '':
        return crashed_thread
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
      elif values[0] == 'Module':
        # Module|{Filename}|{Version}|{Debug Filename}|{Debug ID}|{Base Address}|Max Address}|{Main}
        self.modules.append(Module(self.id, module_count,
                                   values[1], values[4], values[2], values[3]))
        module_count += 1

  def add_dumptext(self, text):
    self.dumpText += text

  def finish_dumptext(self):
    self.dumps.append(Dump(self.id, self.dumpText))

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
ctx = None
try:
  import paste.deploy
  if paste.deploy.CONFIG.has_key("app_conf"):
    ctx = session_context
except AttributeError:
  from socorro.lib import config
  from sqlalchemy.ext.sessioncontext import SessionContext
  localEngine = create_engine(config.processorDatabaseURI, strategy="threadlocal")
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
