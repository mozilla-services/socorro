import datetime
import gzip
import logging
import os
import simplejson
import stat
import threading

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
  
  An additional 'date' branch is saved to facilitate finding files by date. It holds paths like
  YYYY/mm/dd/HH/MM/uuid where MM is among ['00','05', ... '55'] and uuid is a symbolic link to the
  directory in the name branch holding uuid.jsonz
  """
  def __init__(self, root = '.', **kwargs):
    """
    Set up the basic conditions for storing gmpgz files. Possible kwargs keys:
     - 'rootName': The relative path to the top of the name storage tree from root parameter. Default 'name'
     - 'dateName': The relative path to the top of the date storage tree from root parameter. Default 'date'
     - 'fileSuffix': The storage filename suffix. Default '.jsonz'
     - 'gzipCompression': The level of compression to use. Default = 9
     - 'minutesPerSlot': The number of minutes in the lowest date directory. Default = 5
     - 'logger': A logger. Default: logging.getLogger('dumpStorage')
     - 'storageDepth': the length of branches in the radix storage tree. Default = 2
          Do NOT change from 2 without updateing apache mod-rewrite rules and IT old-file removal scripts
    """
    super(ProcessedDumpStorage, self).__init__()
    self.root = root.rstrip(os.sep)
    self.rootName = kwargs.get('rootName','name')
    self.dateName = kwargs.get('dateName','date')
    self.fileSuffix = kwargs.get('fileSuffix','.jsonz')
    self.minutesPerSlot = int(kwargs.get('minutesPerSlot',5))
    self.gzipCompression = int(kwargs.get('gzipCompression',9))
    self.storageDepth = int(kwargs.get('storageDepth',2))
    if not self.fileSuffix.startswith('.'):
      self.fileSuffix = ".%s" % (self.fileSuffix)
    self.storageBranch = os.path.join(self.root,self.rootName)
    self.dateBranch = os.path.join(self.root,self.dateName)
    self.logger = kwargs.get('logger', logging.getLogger('dumpStorage'))

  def newEntry(self, uuid, timestamp=None):
    """
    Given a uuid, create an empty file and a writeable 'file' handle (actually GzipFile) to it
    Create the symbolic link from the date branch to the file's storage directory
    Returns the 'file' handle, or None if there was a problem
    """
    if not timestamp:
      timestamp = datetime.datetime.now()
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
    dateDir = self.__makeDateDir(timestamp)
    try:
      os.symlink(dumpDir,os.path.join(dateDir,uuid))
    finally:
      if not df:
        os.unlink(os.path.join(dateDir,uuid))
    return df

  def putDumpToFile(self,uuid,dumpObject, timestamp=None):
    """
    Given a uuid and an dumpObject, create the appropriate dump file and fill it with object's data
    """
    fh = self.newEntry(uuid, timestamp)
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
    self.logger.debug("%s - %s -> %s",threading.currentThread().getName(),uuid,dirs)
    return os.sep.join(dirs)

  def __makeDumpDir(self,uuid):
    """Make sure the dump directory exists, and return its path"""
    dpath = self.__dumpPath(uuid)
    self.logger.debug("%s - trying makedirs %s",threading.currentThread().getName(),dpath)
    try:
      os.makedirs(dpath)
    except OSError,e:
      if not os.path.isdir(dpath):
        self.logger.debug("%s - OSError when not isdir(%s): %s",threading.currentThread().getName(),dpath,e)
        raise e
    return dpath

  def getDateDir(self,dt):
    m = dt.minute
    slot = self.minutesPerSlot * int(m/self.minutesPerSlot)
    # dtbranch//yyyy//mmmm//dddd//hhhh//5min
    return "%s%s%04d%s%02d%s%02d%s%02d%s%02d" %  (self.dateBranch,os.sep,dt.year,os.sep,dt.month,os.sep,dt.day,os.sep,dt.hour,os.sep,slot)

  def __makeDateDir(self, dt):
    dpath = self.getDateDir(dt)
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
