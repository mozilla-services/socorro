import tempfile
import os

def FixupSourcePath(path):
  """Given a full path of a file in a Mozilla source tree,
     strip off anything prior to mozilla/, and convert
     backslashes into forward slashes."""
  path = path.replace('\\', '/')
  moz_pos = path.find('/mozilla/')
  if moz_pos != -1:
    path = path[moz_pos+1:]
  return path

def TempFileForData(data):
  if data is None:
    raise "Must supply data"
  f = tempfile.NamedTemporaryFile(mode="wb")
  f.write(data)
  return f

class Processor(object):
  def __init__(self, stackwalk_prog, symbol_paths):
    self.stackwalk_prog = stackwalk_prog
    self.symbol_paths = []
    self.symbol_paths.extend(symbol_paths)

  def breakpad_file(self, tmpfile):
    # now call stackwalk and handle the results
    symbol_path = ' '.join(['"%s"' % x for x in self.symbol_paths])
    commandline = '"%s" %s "%s" %s' % (self.stackwalk_prog, "-m", 
                                       tmpfile.name, symbol_path)
    return os.popen(commandline)
