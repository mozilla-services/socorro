import logging
import os
import stat
import gzip

import socorro.lib.ooid as socorro_ooid
import socorro.lib.util as socorro_util

class DmpStorage(object):
  """
  This class, mirrored from JsonDumpStorage in March 2009, implements a gzipped file system storage
  scheme forthe 'cooked raw dump data' from stackwalk_minidump. For historical reasons, these are
  'dmpgz' files.
  Data is stored in the file system using a radix structure based on the ooid or uuid of the data:
  A (nearly) unique identifier assigned at time of collection. The ooid has three parts:
   - The uuid prefix
   - A suffix that encodes the date of assignment
   - information about the appropriate depth of the radix tree (by default: 4, but now usually 2)
  The storage is a file whose name is ooid.suffix, whose path is determined by the ooid itself
  """
  def __init__(self, root = '.', **kwargs):
    """
    Set up the basic conditions for storing gmpgz files. Possible kwargs keys:
     - 'dmpName': The (absolute or relative) path to the top of the storage tree. Default '.'
     - 'dmpSuffix': The storage filename suffix. Default '.gmpgz'
     - 'gzipCompression': The level of compression to use. Default = 9
     - 'logger': A logger. Default: logging.getLogger('dmpStorage')
    """
    super(DmpStorage, self).__init__()
    self.root = root.rstrip(os.sep)
    self.dmpName = kwargs.get('dmpName','dmps')
    self.dmpSuffix = kwargs.get('dmpSuffix','.dmpgz')
    self.gzipCompression = int(kwargs.get('gzipCompression',9))
    if not self.dmpSuffix.startswith('.'):
      self.dmpSuffix = ".%s" % (self.dmpSuffix)
    self.dmpBranch = os.path.join(self.root,self.dmpName)
    self.logger = kwargs.get('logger', logging.getLogger('dmpStorage'))

  def newEntry(self, uuid):
    """
    Given a uuid, create an empty dmp file and hand back a writeable 'file' handle (actually GzipFile)
    """
    dmpDir = self.__makeDmpDir(uuid)
    dname = os.path.join(dmpDir,uuid+self.dmpSuffix)
    df = None
    try:
      df = gzip.open(dname,'w',self.gzipCompression)
    except IOError,x:
      if 2 == x.errno:
        # We might have lost this directory during a cleanup in another thread or process. Do again.
        dmpDir = self.__makeDmpDir(uuid)
        df = gzip.open(dname,'w',self.gzipCompression)
      else:
        raise x
    return df

  def makeDmp(self,uuid,dmpIter):
    """
    Given a uuid and a mini_stackdump iterator or equivalent,
      create the appropriate dmp file
      populate it with newline separated lines from the iterator.
    """
    fh = self.newEntry(uuid)
    try:
      for line in dmpIter:
        fh.write(line.strip()) # be sure we don't have multiple newlines or spaces
        fh.write('\n') # be sure we do have one for each dump line
    finally:
      fh.close()

  def getDmpFile(self,uuid):
    """
    Return an absolute path for the dmp file for a given uuid
    Raise: OSError if the file is missing or unreadable
    """
    path = "%s%s%s%s" % (self.__dmpPath(uuid),os.sep,uuid,self.dmpSuffix)
    # os.stat is moderately faster than trying to open for reading
    self.__readableOrThrow(path)
    return path

  def removeDmpFile(self, uuid):
    """
    Find and remove the dmp file for the given uuid.
    Quietly continue if unfound. Log problem and continue if irremovable.
    """
    try:
      filePath = self.getDmpFile(uuid)
      os.unlink(filePath)
    except OSError,x:
      if 2 != x.errno:
        socorro_util.reportExceptionAndContinue(self.logger)

  def __dmpPath(self, uuid):
    """Return the path to the directory for this uuid"""
    depth = socorro_ooid.depthFromOoid(uuid)
    if not depth: depth = 4
    dirs = [self.dmpBranch]
    dirs.extend([uuid[2*x:2*x+2] for x in range(depth)])
    return os.sep.join(dirs)

  def __makeDmpDir(self,uuid):
    """Make sure the dmp directory exists, and return its path"""
    dpath = self.__dmpPath(uuid)
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
