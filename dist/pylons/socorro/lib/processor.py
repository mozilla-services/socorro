import os
import config
import socorro.models as model
import simplejson
from socorro.lib import EmptyFilter
from datetime import datetime, tzinfo, timedelta
import re, sys, traceback

def print_exception():
  print "Caught Error:", sys.exc_info()[0]
  print sys.exc_info()[1]
  traceback.print_tb(sys.exc_info()[2])
  sys.stdout.flush()

ZERO = timedelta(0)
buildDatePattern = re.compile('^(\\d{4})(\\d{2})(\\d{2})(\\d{2})')

class UTC(tzinfo):
  def utcoffset(self, dt):
    return ZERO

  def tzname(self, dt):
    return "UTC"

  def dst(self, dt):
    return ZERO

utctz = UTC()


def createReport(id, jsonPath):
  """Tries to create a report in the database with the given ID and JSON
  metadata. The database will throw SQLError if the report has already
  been processed."""
    
  jsonFile = open(jsonPath)
  try:
    json = simplejson.load(jsonFile)

    if not isValidReport(json):
      return False

    crash_time = None
    report_date = datetime.now()
    install_age = None

    if 'CrashTime' in json and 'InstallTime' in json:
      crash_time = int(json['CrashTime'])
      report_date = datetime.fromtimestamp(crash_time, utctz)
      install_age = crash_time - int(json["InstallTime"])
    elif 'timestamp' in json:
      report_date = datetime.fromtimestamp(json["timestamp"], utctz)

    build_date = None
    try:
      (y, m, d, h) = map(int,
                         buildDatePattern.match(json["BuildID"]).groups())
      build_date = datetime(y, m, d, h)
    except (AttributeError, ValueError, KeyError):
      pass

    last_crash = None
    if 'SecondsSinceLastCrash' in json:
      last_crash = int(json["SecondsSinceLastCrash"])

    return model.Report.create(uuid=id,
                               date=report_date,
                               product=json.get('ProductName', None),
                               version=json.get('Version', None),
                               build=json.get('BuildID', None),
                               url=json.get('URL', None),
                               install_age=install_age,
                               last_crash=last_crash,
                               email=json.get('Email', None),
                               build_date=build_date,
                               user_id=json.get('UserID', None))
  finally:
    jsonFile.close()

def isValidReport(json):
  """Given a json dict passed from simplejson, we need to verify that required
  fields exist.  If they don't, we should throw away the dump and continue.
  Method returns a boolean value -- true if valid, false if not."""
  
  return 'BuildID' in json and 'Version' in json and 'ProductName' in json

def fixupSourcePath(path):
  """Given a full path of a file in a Mozilla source tree,
     strip off anything prior to mozilla/, and convert
     backslashes into forward slashes."""
  path = path.replace('\\', '/')
  moz_pos = path.find('/mozilla/')
  if moz_pos != -1:
    path = path[moz_pos+1:]
  return path

class Processor(object):
  def __init__(self, stackwalk_prog, symbol_paths, reportHook=None):
    self.stackwalk_prog = stackwalk_prog
    self.symbol_paths = []
    self.symbol_paths.extend(symbol_paths)
    self.reportHook = reportHook

  def __breakpad_file(self, dumpPath):
    # now call stackwalk and handle the results
    symbol_path = ' '.join(['"%s"' % x for x in self.symbol_paths])
    commandline = '"%s" %s "%s" %s' % (self.stackwalk_prog, "-m", 
                                       dumpPath, symbol_path)
    return os.popen(commandline)

  def process(self, dumpDirPath, dumpID, report):
    """read the output of minidump_stackwalk"""
    dumpPath = os.path.join(dumpDirPath, dumpID) + config.dumpFileSuffix

    fh = self.__breakpad_file(dumpPath)
    try:
      report['dump'] = fh.read()
    finally:
      try:
        report.read_dump()
      finally:
        report.flush()
        fh.close()
