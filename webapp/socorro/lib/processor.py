import os
import config
import socorro.models as model
import simplejson
from socorro.lib import EmptyFilter
from datetime import datetime, tzinfo, timedelta
import re

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

  def process(self, dumpDirPath, dumpID, report=None):
    """read the output of minidump_stackwalk"""
    dumpPath = os.path.join(dumpDirPath, dumpID) + config.dumpFileSuffix
    jsonPath = os.path.join(dumpDirPath, dumpID) + config.jsonFileSuffix
    report = self.processDump(dumpPath, jsonPath, dumpID, report)
    return report

  def processDump(self, dumpPath, jsonPath, dumpID, report):
    fh = None
    if report is None:
      report = model.Report()

    try:
      try:
        fh = self.__breakpad_file(dumpPath)
        self.processJSON(jsonPath, report)
        crashed_thread = report.read_header(fh)
        threads = report.read_stackframes(fh)
        if crashed_thread < len(threads):
          for f in threads[crashed_thread]:
            report.frames.append(Frame(f.report_id,
                                       f.frame_num,
                                       f.module_name,
                                       f.function,
                                       f.source,
                                       f.source_line,
                                       f.instruction))
      finally:
        self.__finishReport(report)
    finally:
      if fh:
        fh.close()

    return report

  def __finishReport(self, report):
    if len(report.frames) > 0:
      report.signature = report.frames[0].signature
    if self.reportHook is not None:
      self.reportHook(report)
    report.finish_dumptext()
    report.flush()

  def processJSON(self, jsonPath, report):
    jsonFile = open(jsonPath)
    try:
      json = simplejson.load(jsonFile)
      report.build = json["BuildID"]
      try:
        (y, m, d, h) = map(int,
                           buildDatePattern.match(json["BuildID"]).groups())
        report.build_date = datetime(y, m, d, h)
      except (AttributeError, ValueError):
        pass
      
      if json["timestamp"]:
        report.date = datetime.fromtimestamp(json["timestamp"], utctz)
      report.version = json["Version"]
      report.vendor = json["Vendor"]
      report.product = json["ProductName"]
    finally:
      jsonFile.close()
