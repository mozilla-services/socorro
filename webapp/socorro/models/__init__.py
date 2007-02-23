from sqlalchemy import *
from sqlalchemy.ext.assignmapper import assign_mapper
from pylons.database import session_context
from datetime import datetime

meta = DynamicMetaData()

crash_reports_table = Table('crash_reports', meta,
  Column('crash_id', Integer, primary_key=True, autoincrement=True),
  Column('report_time', DateTime),
  Column('product_name', String(20)),
  Column('build_id', CHAR(10)),
  Column('platform', CHAR(10)),
  Column('url', String(200)),
  Column('comment', String(500)),
  Column('os_name', String(50)),
  Column('os_version', String(50)),
  Column('cpu_name', String(20)),
  Column('cpu_info', String(50)),
  Column('crash_reason', String(50)),
  Column('crash_address', String(10))
)

stack_frames_table = Table('stack_frames', meta,
  Column('stack_id', Integer, primary_key=True, autoincrement=True),
  Column('crash_id', Integer, ForeignKey('crash_reports.crash_id')),
  Column('thread_num', Integer, nullable=False),
  Column('frame_num', Integer, nullable=False),
  Column('module_name', String(20)),
  Column('function', String(100)),
  Column('source', String(200)),
  Column('source_line', Integer),
  Column('instruction', String(10))
)

class CrashReport(object):
  def __init__(self):
    self.report_time = datetime.now()

  def __str__(self):
    return self.crash_id

  def read_header(self, fh):
    for line in fh:
      line = line[:-1]
      # empty line separates header data from thread data
      if line == '':
        break
      values = line.split("|")
      if values[0] == 'OS':
        self.os_name = values[1]
        self.os_version = values[2]
      elif values[0] == 'CPU':
        self.cpu_name = values[1]
        self.cpu_info = values[2]
      elif values[0] == 'Crash':
        self.crash_reason = values[1]
        self.crash_address = values[2]        

def EmptyFilter(x):
  """Return None if the argument is an empty string, otherwise
     return the argument."""
  if x == '':
    return None
  return x

class StackFrame(object):
  def __str__(self):
    return self.stack_id
  
  def readline(self, line):
    values = line.split("|")
    frame_data = dict(zip(['thread_num', 'frame_num', 'module_name',
                           'function', 'source', 'source_line', 'instruction'],
                          map(EmptyFilter, line.split("|"))))
    self.__dict__.update(frame_data)

crash_mapper = assign_mapper(session_context, CrashReport, crash_reports_table)
stack_mapper = assign_mapper(session_context, StackFrame, stack_frames_table)  
