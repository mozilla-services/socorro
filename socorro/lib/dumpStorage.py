import time
import copy
import datetime
import errno
import logging
import os
from stat import S_IRGRP, S_IXGRP, S_IWGRP, S_IRUSR, S_IXUSR, S_IWUSR, S_ISGID, S_IROTH
import threading

import socorro.lib.filesystem as socorro_fs
import socorro.lib.ooid as socorro_ooid

class DumpStorage(object):
  """
  Base class for storing files that can be quickly accessed based on ooid or date
  Note: ooid is a nearly unique identifier assigned external to this class. See socorro/lib/ooid.py

  The storage system is a tree with multiple daily branches each with two sub-branches: 'name' and 'date'

  The daily subdirectory is created from first available of:
    the timestamp passed to newEntry,
    or if None, from the last 6 characters of the ooid
    or if the ooid is not date-encoded, from today's date

  Thus, the tree looks like root/YYYYmmDD/name/xx/xx
                                         /date/HH/mm

  Within the 'name' branch, files are located using a radix structure based on an ooid
  The 'name' path is as follows:
  - Below the storage root and daily branch is the 'name' directory (can be configured)
  - Below that are one or more subdirectories each named with the next pair of characters from the ooid
    The depth of that path is 2 (can be configured)
    Note that the ooid contains a depth encoding which is ignored
  - One or more files may be stored at that location.
  Example: For the ooid '4dd21cc0-49d9-46ae-a42b-fadb42090928', the name path is
   root/20090928/name/4d/d2 (assuming depth of 2, as defaulted)
                
  The 'date' path is as follows:
  - Below the storage root and daily branch is the 'date' directory (can be configured)
  - Below that are 2 subdirectories corresponding to hour and minute-window
  - For each stored item, a single symbolic link is stored in the date directory.
    The name of the link is the ooid, the value is a relative path to the 'name' directory of the ooid
  """

  def __init__(self, root='.', **kwargs):
    """
    Take note of our root directory, and override defaults if any in kwargs:
     - dateName overrides 'date'
     - indexName overrides 'name'
     - 'storageDepth': the length of branches in the radix storage tree. Default = 2
          Do NOT change from 2 without updateing apache mod-rewrite rules and IT old-file removal scripts
     - minutesPerSlot is the size of each bin in the date path. Default 5
     - dirPermissions sets the permissions for all directories in name and date paths. Default 'rwxrwx---'
     - dumpPermissions sets the permissions for actual stored files (this class creates no files)
     - dumpGID sets the group ID for all directoies in name and date paths. Default None.
    """
    super(DumpStorage, self).__init__()
    self.root = root.rstrip(os.sep)
    self.dateName = kwargs.get('dateName','date')
    self.indexName = kwargs.get('indexName','name')
    self.storageDepth = int(kwargs.get('storageDepth',2))
    self.minutesPerSlot = int(kwargs.get('minutesPerSlot',5))
    self.subSlotCount = int(kwargs.get('subSlotCount',0))
    self.dirPermissions = int(kwargs.get('dirPermissions', '%d'%(S_IRGRP | S_IXGRP | S_IWGRP | S_IRUSR | S_IXUSR | S_IWUSR)))
    self.dumpGID = kwargs.get('dumpGID',None)
    if self.dumpGID: self.dumpGID = int(self.dumpGID)
    self.dumpPermissions = int(kwargs.get('dumpPermissions','%d'%(S_IRGRP | S_IWGRP | S_IRUSR | S_IWUSR)))

    self.logger = kwargs.get('logger', logging.getLogger('dumpStorage'))
    upCount = 3
    self.currentSubSlot = 0

  def newEntry(self,ooid,timestamp=None,webheadName = None):
    """
    Sets up the name and date storage directory branches for the given ooid.
    Creates any needed directories along the path to the appropriate storage location. Sets gid and mode if specified
    Creates one symbolic link in the date leaf directory with name ooid and referencing the name leaf directory
    returns (nameDir,dateDir)
    """
    if not timestamp:
      timestamp = datetime.datetime.now()
    if not os.path.isdir(self.root):
      os.mkdir(self.root)
    nameDir,nparts = self.makeNameDir(ooid,timestamp)
    dateDir,dparts = self.makeDateDir(timestamp,webheadName)
    parts = [os.path.pardir,]*(len(dparts)-2) # lose root and dailypart
    parts.append(self.indexName)
    parts.extend(self.relativeNameParts(ooid))
    relNameDir = os.sep.join(parts)
    try:
      os.symlink(relNameDir,os.path.join(dateDir,ooid))
    except OSError,x:
      if errno.ENOENT == x.errno:
      # maybe a different thread cleaned this out from under us. Try again
        nameDir = self.makeNameDir(ooid) # might be overkill, but reasonably cheap insurance
        dateDir = self.makeDateDir(timestamp) 
        os.symlink(relNameDir,os.path.join(dateDir,ooid))
      else:
        raise
    if self.dumpGID:
      os.chown(os.path.join(dateDir,ooid),-1,self.dumpGID)
    return (nameDir,dateDir)

  def chownGidVisitor(self,path):
    os.chown(path,-1,self.dumpGID)

  def relativeNameParts(self, ooid):
    depth = self.storageDepth
    return [ooid[2*x:2*x+2] for x in range(depth)]

  def dailyPart(self, ooid, timestamp=None):
    """
    return YYYYMMDD
    use the timestamp if any, else the ooid's last 6 chars if reasonable, else now()
    """
    year,month,day = None,None,None
    if timestamp:
      (year,month,day) = (timestamp.year,timestamp.month,timestamp.day)
    else:
      try:
        (year,month,day) = (int('20%s'%(ooid[-6:-4])),int(ooid[-4:-2]),int(ooid[-2:]))
      except ValueError:
        timestamp = datetime.datetime.now()
        (year,month,day) = (timestamp.year,timestamp.month,timestamp.day)
    return "%4d%02d%02d"%(year,month,day)

  def lookupNamePath(self,ooid,timestamp=None):
    """
    Find an existing name-side directory for the given ooid, return (dirPath,dirParts)
    on failure, return (None,[])
    """
    nPath,nParts = self.namePath(ooid,timestamp)
    if os.path.exists(nPath):
      return nPath,nParts
    else:
      dailyDirs = os.listdir(self.root)
      for d in dailyDirs:
        nParts[1] = d
        path = os.sep.join(nParts)
        if os.path.exists(path):
          return path,nParts
    return (None,[])

  def namePath(self, ooid, timestamp=None):
    """
    Return the path to the directory for this ooid and the directory parts of the path
    Ignores encoded ooid depth, uses depth from __init__ (default 2)
    """
    # depth = socorro_ooid.depthFromOoid(ooid)
    # if not depth: depth = 4
    depth = self.storageDepth
    dirs = [self.root,self.dailyPart(ooid,timestamp),self.indexName]
    dirs.extend(self.relativeNameParts(ooid))
    #self.logger.debug("%s - %s -> %s",threading.currentThread().getName(),ooid,dirs)
    return os.sep.join(dirs),dirs

  def makeNameDir(self,ooid, timestamp=None):
    """
    Make sure the name directory exists, and return its path, and list of path components
    Raises OSError on failure
    """
    npath,nparts = self.namePath(ooid,timestamp)
    #self.logger.debug("%s - trying makedirs %s",threading.currentThread().getName(),npath)
    um = os.umask(0)
    try:
      socorro_fs.makedirs(npath,self.dirPermissions)
    except OSError,e:
      if not os.path.isdir(npath):
        #self.logger.debug("%s - in makeNameDir, got not isdir(%s): %s",threading.currentThread().getName(),npath,e)
        raise
    finally:
      os.umask(um)
    if self.dumpGID:
      socorro_fs.visitPath(os.path.join(*nparts[:2]),npath,self.chownGidVisitor)
    return npath,nparts

  def lookupOoidInDatePath(self,date,ooid,webheadName=None):
    """
    Look for the date path holding a symbolic link named 'ooid', return dirPath,dirParts
    on failure return None,[]
    """
    if date:
      datePath,dateParts = self.datePath(date,webheadName)
      if os.path.exists(os.path.join(datePath,ooid)):
        return datePath,dateParts
      
    dailyDirs = os.listdir(self.root)
    for d in dailyDirs:
      # We don't know webhead if any, so avoid confusion by looking everywhere
      for dir,dirs,files in os.walk(os.sep.join((self.root,d,self.dateName))):
        if ooid in dirs or ooid in files: # probably dirs
          dirPath = dir
          ooidPath = os.path.join(dirPath,ooid)
          dirParts = dir.split(os.sep)
          return dirPath,dirParts
    return None,[]

  def datePath(self,date, webheadName = None):
    """Return the absolute path to the date subdirectory for the given date"""
    m = date.minute
    slot = self.minutesPerSlot * (int(m/self.minutesPerSlot))
    parts = [self.root, self.dailyPart('',date),self.dateName,'%02d'%date.hour,'%02d'%slot]
    if self.subSlotCount:
      if webheadName:
        parts.append("%s_%d"%(webheadName,self.currentSubSlot))
      else:
        parts[-1] = '%02d_%d'%(slot,self.currentSubSlot)
      self.currentSubSlot = (self.currentSubSlot+1)%self.subSlotCount
    return os.sep.join(parts),parts

  def makeDateDir(self,date, webheadName = None):
    """Assure existence of date directory for the given date, return path, and list of components"""
    dpath,dparts = self.datePath(date,webheadName)
    um = os.umask(0)
    try:
      socorro_fs.makedirs(dpath,self.dirPermissions)
    except OSError,e:
      if not os.path.isdir(dpath):
        #self.logger.debug("%s - in makeDateDir, got not isdir(%s): %s",threading.currentThread().getName(),dpath,e)
        raise
    finally:
      os.umask(um)
    if self.dumpGID:
      socorro_fs.visitPath(os.path.join(*dparts[:2]),dpath,self.chownGidVisitor)
    return dpath,dparts

  @staticmethod
  def readableOrThrow(path):
    """
    Throws OSError unless user, group or other has read permission
    (Convenience function for derived classes which will all need it)
    """
    if not os.stat(path).st_mode & (S_IRUSR|S_IRGRP|S_IROTH):
      raise OSError(errno.ENOENT,'Cannot read')
