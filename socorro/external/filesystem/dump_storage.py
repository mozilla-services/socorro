import time
import copy
import datetime
import errno
import logging
import os
from stat import S_IRGRP, S_IXGRP, S_IWGRP, S_IRUSR, S_IXUSR, S_IWUSR, S_ISGID, S_IROTH
import threading

import socorro.external.filesystem.filesystem as socorro_fs
import socorro.lib.ooid as socorro_ooid
from socorro.lib.datetimeutil import utc_now, UTC


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
    The depth of that path is 2 (as encoded in the ooid when it is generated)
  - One or more files may be stored at that location.
  Example: For the ooid '4dd21cc0-49d9-46ae-a42b-fadb42090928', the name path is
   root/20090928/name/4d/d2 (depth of 2 is encoded at ooid[-7])

  The 'date' path is as follows:
  - Below the storage root and daily branch is the 'date' directory (name can be configured)
  - Below that are 2 subdirectories corresponding to hour and minute-window
  - For each stored item, a single symbolic link is stored in the date directory.
    The name of the link is the ooid, the value is a relative path to the 'name' directory of the ooid
  """

  def __init__(self, root='.', osModule=os, **kwargs):
    """
    Take note of our root directory, and override defaults if any in kwargs:
     - dateName overrides 'date'
     - indexName overrides 'name'
     - minutesPerSlot is the size of each bin in the date path. Default 5
     - dirPermissions sets the permissions for all directories in name and date paths. Default 'rwxrwx---'
     - dumpPermissions sets the permissions for actual stored files (this class creates no files)
     - dumpGID sets the group ID for all directoies in name and date paths. Default None.
    """
    super(DumpStorage, self).__init__()
    self.osModule = osModule
    self.root = root.rstrip(os.sep)
    self.dateName = kwargs.get('dateName','date')
    self.indexName = kwargs.get('indexName','name')
    self.minutesPerSlot = int(kwargs.get('minutesPerSlot',5))
    self.subSlotCount = int(kwargs.get('subSlotCount',0))
    self.dirPermissions = int(kwargs.get('dirPermissions', '%d'%(S_IRGRP | S_IXGRP | S_IWGRP | S_IRUSR | S_IXUSR | S_IWUSR)))
    self.dumpPermissions = int(kwargs.get('dumpPermissions','%d'%(S_IRGRP | S_IWGRP | S_IRUSR | S_IWUSR)))
    self.dumpGID = kwargs.get('dumpGID', None)
    try:
      if self.dumpGID:
        self.dumpGID = int(self.dumpGID)
    except ValueError:
        if self.dumpGID == '':
          self.dumpGID = None
        else:
          raise

    self.logger = kwargs.get('logger', logging.getLogger('dumpStorage'))
    self.currentSubSlots = {}
    self.logger.debug("""Constructor has set the following values:
      self.root: %s
      self.dateName: %s
      self.indexName: %s
      self.minutesPerSlot: %s
      self.subSlotCount: %s
      self.dirPermissions: %o
      self.dumpPermissions: %o
      self.dumpGID: %s"""%(self.root,self.dateName,self.indexName,self.minutesPerSlot,self.subSlotCount,self.dirPermissions,self.dumpPermissions,self.dumpGID))

  def newEntry(self,ooid,timestamp=None,webheadName = None):
    """
    Sets up the name and date storage directory branches for the given ooid.
    Creates any needed directories along the path to the appropriate storage location. Sets gid and mode if specified
    Creates one symbolic link in the date leaf directory with name ooid and referencing the name leaf directory
    returns (nameDir,dateDir)
    """
    if not timestamp:
      timestamp = socorro_ooid.dateFromOoid(ooid)
      if not timestamp:
        timestamp = utc_now()
    if not self.osModule.path.isdir(self.root):
      um = self.osModule.umask(0)
      try:
        self.osModule.mkdir(self.root,self.dirPermissions)
      finally:
        self.osModule.umask(um)
    nameDir,nparts = self.makeNameDir(ooid,timestamp)
    dateDir,dparts = self.makeDateDir(timestamp,webheadName)
    # adjust the current subslot only when inserting a new entry
    if self.subSlotCount:
      k = dparts[-1].split('_')[0]
      curcount = self.currentSubSlots.setdefault(k,0)
      self.currentSubSlots[k] = (curcount + 1)%self.subSlotCount
    parts = [os.path.pardir,]*(len(dparts)-2) # lose root and dailypart
    parts.append(self.indexName)
    parts.extend(self.relativeNameParts(ooid))
    relNameDir = os.sep.join(parts)
    try:
      self.osModule.symlink(relNameDir,os.path.join(dateDir,ooid))
    except OSError,x:
      if errno.ENOENT == x.errno:
      # maybe a different thread cleaned this out from under us. Try again
        nameDir = self.makeNameDir(ooid) # might be overkill, but reasonably cheap insurance
        dateDir = self.makeDateDir(timestamp)
        self.osModule.symlink(relNameDir,os.path.join(dateDir,ooid))
      elif errno.EEXIST == x.errno:
        self.osModule.unlink(os.path.join(dateDir,ooid))
        self.osModule.symlink(relNameDir,os.path.join(dateDir,ooid))
      else:
        raise
    if self.dumpGID:
      self.osModule.chown(os.path.join(dateDir,ooid),-1,self.dumpGID)
    return (nameDir,dateDir)

  def chownGidVisitor(self,path):
    """a convenience function"""
    self.osModule.chown(path,-1,self.dumpGID)

  def relativeNameParts(self, ooid):
    depth = socorro_ooid.depthFromOoid(ooid)
    if not depth: depth = 4
    return [ooid[2*x:2*x+2] for x in range(depth)]

  def dailyPart(self, ooid, timestamp=None):
    """
    return YYYYMMDD
    use the timestamp if any, else the ooid's last 6 chars if reasonable, else now()
    """
    year,month,day = None,None,None
    if not timestamp:
      timestamp = socorro_ooid.dateFromOoid(ooid)
    if not timestamp:
      timestamp = utc_now()
    (year,month,day) = (timestamp.year,timestamp.month,timestamp.day)
    return "%4d%02d%02d"%(year,month,day)

  def pathToDate(self,datePath):
    """
    Given a path to the date branch leaf node, return a corresponding datetime.datetime()
    Note that because of bucketing, the minute will be no more accurate than the bucket size
    """
    # normalize to self.root
    if not datePath:
      return None
    parts = os.path.abspath(datePath).split(os.sep)
    root = os.path.split(self.root)[1]
    parts = parts[parts.index(root):]
    minute = 0
    hour = 0
    try:
      minute = int(parts[-1].split('_')[0])
      hour = int(parts[-2])
    except ValueError:
      try:
        minute = int(parts[-2].split('_')[0])
        hour = int(parts[-3])
      except ValueError:
        pass
    return datetime.datetime(int(parts[1][:4]),int(parts[1][4:6]),int(parts[1][-2:]),int(hour),minute,tzinfo=UTC)

  def lookupNamePath(self,ooid,timestamp=None):
    """
    Find an existing name-side directory for the given ooid, return (dirPath,dirParts)
    on failure, return (None,[])
    """
    nPath,nParts = self.namePath(ooid,timestamp)
    if self.osModule.path.exists(nPath):
      return nPath,nParts
    else:
      dailyDirs = self.osModule.listdir(self.root)
      for d in dailyDirs:
        nParts[1] = d
        path = os.sep.join(nParts)
        if self.osModule.path.exists(path):
          return path,nParts
    return (None,[])

  def namePath(self, ooid, timestamp=None):
    """
    Return the path to the directory for this ooid and the directory parts of the path
    Ignores encoded ooid depth, uses depth from __init__ (default 2)
    """
    ooidDay,depth = socorro_ooid.dateAndDepthFromOoid(ooid)
    if not depth: depth = 4
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
    um = self.osModule.umask(0)
    try:
      try:
        socorro_fs.makedirs(npath,self.dirPermissions,self.osModule)
      except OSError,e:
        if not self.osModule.path.isdir(npath):
          #self.logger.debug("%s - in makeNameDir, got not isdir(%s): %s",threading.currentThread().getName(),npath,e)
          raise
    finally:
      self.osModule.umask(um)
    if self.dumpGID:
      socorro_fs.visitPath(os.path.join(*nparts[:2]),npath,self.chownGidVisitor)
    return npath,nparts

  def lookupOoidInDatePath(self,date,ooid,webheadName=None):
    """
    Look for the date path holding a symbolic link named 'ooid', return datePath,dateParts
    on failure return None,[]
    """
    if not date:
      date = socorro_ooid.dateFromOoid(ooid)
    if date:
      datePath,dateParts = self.datePath(date,webheadName)
      if self.osModule.path.exists(os.path.join(datePath,ooid)):
        return datePath,dateParts
    for d in self.osModule.listdir(self.root):
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
        subSlot = self.currentSubSlots.setdefault(webheadName,0)
        parts.append("%s_%d"%(webheadName,subSlot))
      else:
        subSlot = self.currentSubSlots.setdefault(slot,0)
        parts[-1] = '%02d_%d'%(slot,subSlot)
    return os.sep.join(parts),parts

  def makeDateDir(self,date, webheadName = None):
    """Assure existence of date directory for the given date, return path, and list of components"""
    dpath,dparts = self.datePath(date,webheadName)
    um = self.osModule.umask(0)
    try:
      try:
        socorro_fs.makedirs(dpath,self.dirPermissions,self.osModule)
      except OSError,e:
        if not self.osModule.path.isdir(dpath):
          #self.logger.debug("%s - in makeDateDir, got not isdir(%s): %s",threading.currentThread().getName(),dpath,e)
          raise
    finally:
      self.osModule.umask(um)
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
      raise OSError(errno.ENOENT,'Cannot read %s' % path)
