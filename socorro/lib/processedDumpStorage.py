import gzip
import logging
import os
import simplejson
import socorro.lib.dumpStorage as socorro_dumpStorage
import socorro.lib.util as socorro_util

class ProcessedDumpStorage(socorro_dumpStorage.DumpStorage):
  """
  This class, mirrored from JsonDumpStorage in March 2009, implements a gzipped file system storage
  scheme for the 'cooked raw dump data' from stackwalk_minidump. The file format is gzipped json, with
  default suffix '.jsonz'
  Files are located using a radix structure based on the ooid or uuid of the data, a (nearly) unique
  identifier assigned at time of collection. The ooid has three parts:
   - The ooid prefix
   - A suffix that encodes the date of assignment
   - information about the appropriate depth of the radix tree (by default: 4, but now always 2)
  The storage is a file whose name is ooid.suffix, whose path is determined by the ooid itself

  An additional 'date' branch is saved to facilitate finding files by date. It holds paths like
  YYYY/mm/dd/HH/MM_n/ooid where MM is among ['00','05', ... '55'], n is a (small) digit and
  ooid is a symbolic link to the directory in the name branch holding ooid.jsonz
  """
  def __init__(self, root = '.', **kwargs):
    """
    Set up the basic conditions for storing gmpgz files. Possible kwargs keys:
     - 'indexName': The relative path to the top of the name storage tree from root parameter. Default 'name'
     - //deprecated// rootName: now is indexName
     - 'dateName': The relative path to the top of the date storage tree from root parameter. Default 'date'
     - 'fileSuffix': The storage filename suffix. Default '.jsonz'
     - 'gzipCompression': The level of compression to use. Default = 9
     - 'minutesPerSlot': The number of minutes in the lowest date directory. Default = 1
     - 'subSlotCount': If other than 1 (default) distribute data evenly among this many sub timeslots
     - 'dirPermissions': sets the permissions for all directories in name and date paths. Default 'rwxrwx---'
     - 'dumpPermissions': sets the permissions for actual stored files (this class creates no files)
     - 'dumpGID': sets the group ID for all directoies in name and date paths. Default None.
     - 'logger': A logger. Default: logging.getLogger('dumpStorage')
     - 'storageDepth': the length of branches in the radix storage tree. Default = 2
          Do NOT change from 2 without updateing apache mod-rewrite rules and IT old-file removal scripts
    """
    kwargs.setdefault('minutesPerSlot',1)
    kwargs.setdefault('subSlotCount',1)
    rootName = kwargs.get('rootName','name')
    kwargs.setdefault('indexName',rootName)
    super(ProcessedDumpStorage, self).__init__(root=root, **kwargs)
    self.fileSuffix = kwargs.get('fileSuffix','.jsonz')
    self.gzipCompression = int(kwargs.get('gzipCompression',9))
    self.storageDepth = int(kwargs.get('storageDepth',2))
    if not self.fileSuffix.startswith('.'):
      self.fileSuffix = ".%s" % (self.fileSuffix)
    self.logger = kwargs.get('logger', logging.getLogger('dumpStorage'))

  def newEntry(self, ooid, timestamp=None):
    """
    Given a ooid, create an empty file and a writeable 'file' handle (actually GzipFile) to it
    Create the symbolic link from the date branch to the file's storage directory
    Returns the 'file' handle, or None if there was a problem
    """
    nameDir, dateDir = super(ProcessedDumpStorage,self).newEntry(ooid,timestamp)
    dname = os.path.join(nameDir,ooid+self.fileSuffix)
    df = None
    try:
      try:
        df = gzip.open(dname,'w',self.gzipCompression)
      except IOError,x:
        if 2 == x.errno:
          # We might have lost this directory during a cleanup in another thread or process. Do again.
          nameDir,nparts = self.makeNameDir(ooid,timestamp)
          df = gzip.open(dname,'w',self.gzipCompression)
        else:
          raise x
      except Exception,x:
        raise
      os.chmod(dname,self.dumpPermissions)
    finally:
      if not df:
        os.unlink(os.path.join(dateDir,ooid))
    return df

  def putDumpToFile(self,ooid,dumpObject, timestamp=None):
    """
    Given a ooid and an dumpObject, create the appropriate dump file and fill it with object's data
    """
    fh = self.newEntry(ooid, timestamp)
    try:
      simplejson.dump(dumpObject, fh)
    finally:
      fh.close()

  def getDumpFromFile(self,ooid):
    """
    Given a ooid, extract and return a dumpObject from the associated file if possible.
    raises OSError if the file is missing or unreadable
    """
    df = None
    try:
      df = gzip.open(self.getDumpPath(ooid))
      return simplejson.load(df)
    finally:
      if df:
        df.close()

  def getDumpPath(self,ooid):
    """
    Return an absolute path for the file for a given ooid
    Raise: OSError if the file is missing or unreadable
    """
    path = os.path.join(self.namePath(ooid)[0],ooid+self.fileSuffix)
    self.readableOrThrow(path)
    return path

  def removeDumpFile(self, ooid):
    """
    Find and remove the dump file for the given ooid.
    Quietly continue if unfound. Log problem and continue if irremovable.
    """
    try:
      filePath = self.getDumpPath(ooid)
      os.unlink(filePath)
    except OSError,x:
      if 2 != x.errno:
        socorro_util.reportExceptionAndContinue(self.logger)

