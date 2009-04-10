import gzip
import logging
import os
import simplejson
import stat

import socorro.lib.ooid as socorro_ooid
import socorro.lib.util as socorro_util

class ProcessedDumpStorage(object):
  """
  This class, mirrored from JsonDumpStorage in March 2009, implements a gzipped file system storage
  scheme for the 'cooked raw dump data' from stackwalk_minidump. The file format is gzipped json, with
  default suffix '.jsonz'
  Files are located using a radix structure based on the ooid or uuid of the data, a (nearly) unique
  identifier assigned at time of collection. The ooid has three parts:
   - The uuid prefix
   - A suffix that encodes the date of assignment
   - information about the appropriate depth of the radix tree (by default: 4, but now always 2)
  The storage is a file whose name is ooid.suffix, whose path is determined by the ooid itself
  """
  def __init__(self, root = '.', **kwargs):
    """
    Set up the basic conditions for storing gmpgz files. Possible kwargs keys:
     - 'rootName': The (absolute or relative) path to the top of the storage tree. Default '.'
     - 'fileSuffix': The storage filename suffix. Default '.gmpgz'
     - 'gzipCompression': The level of compression to use. Default = 9
     - 'logger': A logger. Default: logging.getLogger('dumpStorage')
     - 'storageDepth': the lenght of branches in the radix storage tree. Default = 2
    """
    super(ProcessedDumpStorage, self).__init__()
    self.root = root.rstrip(os.sep)
    self.rootName = kwargs.get('rootName','.')
    self.fileSuffix = kwargs.get('fileSuffix','.jsonz')
    self.gzipCompression = int(kwargs.get('gzipCompression',9))
    self.storageDepth = int(kwargs.get('storageDepth',2))
    if not self.fileSuffix.startswith('.'):
      self.fileSuffix = ".%s" % (self.fileSuffix)
    self.storageBranch = os.path.join(self.root,self.rootName)
    self.logger = kwargs.get('logger', logging.getLogger('dumpStorage'))

  def newEntry(self, uuid):
    """
    Given a uuid, create an empty file and hand back a writeable 'file' handle (actually GzipFile)
    """
    dumpDir = self.__makeDumpDir(uuid)
    dname = os.path.join(dumpDir,uuid+self.fileSuffix)
    df = None
    try:
      df = gzip.open(dname,'w',self.gzipCompression)
    except IOError,x:
      if 2 == x.errno:
        # We might have lost this directory during a cleanup in another thread or process. Do again.
        dumpDir = self.__makeDumpDir(uuid)
        df = gzip.open(dname,'w',self.gzipCompression)
      else:
        raise x
    return df

  def putDumpToFile(self,uuid,dumpObject):
    """
    Given a uuid and an dumpObject, create the appropriate dump file and fill it with object's data
    """
    fh = self.newEntry(uuid)
    try:
      simplejson.dump(dumpObject,fh)
    finally:
      fh.close()

  def getDumpFromFile(self,uuid):
    """
    Given a uuid, extract and return a dumpObject from the associated file if possible.
    raises OSError if the file is missing or unreadable
    """
    df = None
    try:
      df = gzip.open(self.getDumpPath(uuid))
      return simplejson.load(df)
    finally:
      if df:
        df.close()

  def getDumpPath(self,uuid):
    """
    Return an absolute path for the file for a given uuid
    Raise: OSError if the file is missing or unreadable
    """
    path = "%s%s%s%s" % (self.__dumpPath(uuid),os.sep,uuid,self.fileSuffix)
    # os.stat is moderately faster than trying to open for reading
    self.__readableOrThrow(path)
    return path

  def removeDumpFile(self, uuid):
    """
    Find and remove the dump file for the given uuid.
    Quietly continue if unfound. Log problem and continue if irremovable.
    """
    try:
      filePath = self.getDumpPath(uuid)
      os.unlink(filePath)
    except OSError,x:
      if 2 != x.errno:
        socorro_util.reportExceptionAndContinue(self.logger)

  def __dumpPath(self, uuid):
    """Return the path to the directory for this uuid"""
    # depth = socorro_ooid.depthFromOoid(uuid)
    # if not depth: depth = 4
    depth = self.storageDepth
    dirs = [self.storageBranch]
    dirs.extend([uuid[2*x:2*x+2] for x in range(depth)])
    return os.sep.join(dirs)

  def __makeDumpDir(self,uuid):
    """Make sure the dump directory exists, and return its path"""
    dpath = self.__dumpPath(uuid)
    try:
      os.makedirs(dpath)
    except OSError,e:
      if not os.path.isdir(dpath):
        raise e
    return dpath

  def __readableOrThrow(self, path):
    """ raises OSError if not """
    if not os.stat(path).st_mode & (stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH):
      raise OSError('Cannot read')
