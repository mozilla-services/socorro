import os
import config
import socorro.models as model
import simplejson
from datetime import datetime

def fixupSourcePath(path):
  """Given a full path of a file in a Mozilla source tree,
     strip off anything prior to mozilla/, and convert
     backslashes into forward slashes."""
  path = path.replace('\\', '/')
  moz_pos = path.find('/mozilla/')
  if moz_pos != -1:
    path = path[moz_pos+1:]
  return path

def firefoxHook(report):
  for frame in report.frames:
    if frame.source is not None:
      frame.source = fixupSourcePath(frame.source)
      
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

  def process(self, dumpDirPath, dumpID):
    """read the output of minidump_stackwalk"""
    dumpPath = os.path.join(dumpDirPath, dumpID) + config.dumpFileSuffix
    jsonPath = os.path.join(dumpDirPath, dumpID) + config.jsonFileSuffix
    report = self.processDump(dumpPath, jsonPath, dumpID)

    if self.reportHook is not None:
      self.reportHook(report)

    return report

  def processDump(self, dumpPath, jsonPath, dumpID):
    #
    # XXX too much flushing
    #
    fh = None
    report = model.Report()
    report.uuid = dumpID
    try:
      try:
        fh = self.__breakpad_file(dumpPath)
        self.processJSON(jsonPath, report)
        crashed_thread = report.read_header(fh)
        report.flush()
        
        for line in fh:
          if line.startswith(str(crashed_thread)):
            frame = model.Frame()
            frame.readline(line[:-1])
            frame.report_id = report.id
            report.frames.append(frame)
            frame.flush()

      except Error, e:
        report.flush()
        raise e
    finally:
      if fh:
        fh.close()

    return report

  def processJSON(self, jsonPath, report):
    jsonFile = open(jsonPath)
    try:
      json = simplejson.load(jsonFile)
      report.build = json["BuildID"]
      if json["timestamp"]:
        report.date = datetime.utcfromtimestamp(json["timestamp"])
      report.version = json["Version"]
      report.vendor = json["Vendor"]
      report.product = json["ProductName"]
    finally:
      jsonFile.close()
