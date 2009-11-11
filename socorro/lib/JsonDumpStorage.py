import time
import datetime
import errno
import os
import shutil
from stat import S_IRGRP, S_IXGRP, S_IWGRP, S_IRUSR, S_IXUSR, S_IWUSR, S_ISGID, S_IROTH
import threading

import socorro.lib.dumpStorage as socorro_dumpStorage
import socorro.lib.filesystem as socorro_fs
import socorro.lib.util as socorro_util
import socorro.lib.ooid as socorro_ooid

class NoSuchUuidFound(Exception):
  pass

#=================================================================================================================
class JsonDumpStorage(socorro_dumpStorage.DumpStorage):
  """
  This class implements a file system storage scheme for the JSON and dump files of the Socorro project.
  It create a tree with two branches: the name branch and the date branch.
   - The name branch consists of paths based on the first 8 characters of the uuid file name. It holds the two
     data files and a relative symbolic link to the date branch directory associated with the particular uuid.
     For the uuid:  22adfb61-f75b-11dc-b6be-001321b0783d
      - the json file is stored as %(root)s/name/22/ad/fb/61/22adfb61-f75b-11dc-b6be-001321b0783d.json
      - the dump file is stored as %(root)s/name/22/ad/fb/61/22adfb61-f75b-11dc-b6be-001321b0783d.dump
      - the symbolic link is stored as %(root)s/name/22/ad/fb/61/22adfb61-f75b-11dc-b6be-001321b0783d
        and (see below) references %(toDateFromName)s/date/2008/09/30/12/05/webhead01_0
   - The date branch consists of paths based on the year, month, day, hour, minute-segment, webhead host name and
     a small sequence number.
     For each uuid, it holds a relative symbolic link referring to the actual storage (name) directory holding
     the data for that uuid.
     For the uuid above, submitted at 2008-09-30T12:05 from webhead01
      - the symbolic link is stored as %(root)s/date/2008/09/30/12/05/webhead01_0/22adfb61-f75b-11dc-b6be-001321b0783d
        and references %(toNameFromDate)s/name/22/ad/fb/61

  Note: The symbolic links are relative, so they begin with several rounds of '../'. This is to avoid issues that
  might arise from variously mounted nfs volumes. If the layout changes, self.toNameFromDate and toDateFromName
  must be changed to match, as well as a number of the private methods.

  Note: If the number of links in a particular webhead subdirectory would exceed maxDirectoryEntries, then a new
  webhead directory is created by appending a larger '_N' : .../webhead01_0 first, then .../webhead01_1 etc.
  For the moment, maxDirectoryEntries is ignored for the name branch. If this becomes a problem, another name
  level might be added, either skipping the '-' that is next, or perhaps better, using the last two characters.
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, root=".", **kwargs):
    """
    Take note of our root directory and other necessities.
    Yes, it is perfectly legal to call super(...).__init__() after doing some other code.
    ... As long as you expect the behavior you get, anyway...
    """
    kwargs.setdefault('minutesPerSlot',1)
    kwargs.setdefault('subSlotCount',1)
    super(JsonDumpStorage, self).__init__(root=root,**kwargs)
    tmp = kwargs.get('cleanIndexDirectories','false')
    self.cleanIndexDirectories = 'true' == tmp.lower()
    self.jsonSuffix = kwargs.get('jsonSuffix','.json')
    if not self.jsonSuffix.startswith('.'):
      self.jsonSuffix = ".%s" % (self.jsonSuffix)
    self.dumpSuffix = kwargs.get('dumpSuffix','.dump')
    if not self.dumpSuffix.startswith('.'):
      self.dumpSuffix = ".%s" % (self.dumpSuffix)
    self.logger = kwargs.get('logger', socorro_util.FakeLogger())

  #-----------------------------------------------------------------------------------------------------------------
  def newEntry (self, uuid, webheadHostName='webhead01', timestamp=None):
    """
    Sets up the name and date storage directory branches for the given uuid.
    Creates any directories that it needs along the path to the appropriate storage location.
    Creates two relative symbolic links: the date branch link pointing to the name directory holding the files;
    the name branch link pointing to the date branch directory holding that link.
    Returns a 2-tuple containing files open for writing: (jsonfile,dumpfile)
    If self.dumpGID, then the file tree from root to and including the data files are chown'd
    If self.dumpPermissions, then chmod is called on the data files
    """
    # note: after this call, dateDir already holds link to nameDir
    nameDir, dateDir = super(JsonDumpStorage,self).newEntry(uuid,timestamp,webheadHostName)
    df,jf = None,None
    jname = os.path.join(nameDir,uuid+self.jsonSuffix)
    try:
      jf = open(jname,'w')
    except IOError,x:
      if 2 == x.errno:
        nameDir = self.makeNameDir(uuid,timestamp) # deliberately leave this dir behind if next line throws
        jf = open(jname,'w')
      else:
        raise x
    try:
      # Do all this in a try/finally block to unroll in case of error
      os.chmod(jname,self.dumpPermissions)
      dname = os.path.join(nameDir,uuid+self.dumpSuffix)
      df = open(dname,'w')
      os.chmod(dname,self.dumpPermissions)
      rparts = [os.path.pardir,]*(1+self.storageDepth)
      rparts.append(self.dateName)
      partsLength = self.storageDepth
      if webheadHostName and self.subSlotCount:
        partsLength = 1 + partsLength
      dateParts = dateDir.split(os.path.sep)[-partsLength:]
      rparts.extend(dateParts)
      os.symlink(os.path.sep.join(rparts),os.path.join(nameDir,uuid))
      if self.dumpGID:
        def chown1(path):
          os.chown(path,-1,self.dumpGID)
        socorro_fs.visitPath(self.root,os.path.join(nameDir,uuid+self.jsonSuffix),chown1)
        os.chown(os.path.join(nameDir,uuid+self.dumpSuffix),-1,self.dumpGID)
        #socorro_fs.visitPath(self.root,os.path.join(dateDir,uuid),chown1)
    finally:
      if not jf or not df:
        if jf: jf.close()
        if df: df.close()
        try:
          os.unlink(os.path.join(dateDir,uuid))
        except:
          pass # ok if not there
        try:
          os.unlink(os.path.join(nameDir,uuid))
        except:
          pass # ok if not there
        df,jf = None,None
    return (jf,df)

  #-----------------------------------------------------------------------------------------------------------------
  def copyFrom(self, uuid, jsonpath, dumppath, webheadHostName, timestamp, createLinks = False, removeOld = False):
    """
    Copy the two crash files from the given path to our current storage location in name branch
    If createLinks, use webheadHostName and timestamp to insert links to and from the date branch
    If removeOld, after the files are copied, attempt to unlink the originals
    raises OSError if the paths are unreadable or if removeOld is true and either file cannot be unlinked

    """
    nameDir,nparts = self.makeNameDir(uuid,timestamp) # deliberately leave this dir behind if next line throws
    jsonNewPath = '%s%s%s%s' % (nameDir,os.sep,uuid,self.jsonSuffix)
    dumpNewPath = '%s%s%s%s' % (nameDir,os.sep,uuid,self.dumpSuffix)
    try:
      shutil.copy2(jsonpath,jsonNewPath)
    except IOError,x:
      if 2 == x.errno:
        nameDir = self.makeNameDir(uuid,timestamp) # deliberately leave this dir behind if next line throws
        shutil.copy2(jsonpath,jsonNewPath)
      else:
        raise x
    os.chmod(jsonNewPath,self.dumpPermissions)
    try:
      shutil.copy2(dumppath,dumpNewPath)
      os.chmod(dumpNewPath,self.dumpPermissions)
      if self.dumpGID:
        os.chown(dumpNewPath,-1,self.dumpGID)
        os.chown(jsonNewPath,-1,self.dumpGID)
    except OSError, e:
      try:
        os.unlink(jsonNewPath)
      finally:
        raise e
    if createLinks:
      dateDir,dparts = self.makeDateDir(timestamp,webheadHostName)
      dateRelativeParts = [os.pardir,]*(1+self.storageDepth)
      dateRelativeParts.extend(dparts[2:])
      os.symlink(os.sep.join(dateRelativeParts),os.path.join(nameDir,uuid))
      try:
        nameRelativeParts = [os.pardir,]*(len(dparts)-2)
        nameRelativeParts.extend(nparts[2:])
        os.symlink(os.sep.join(nameRelativeParts),os.path.join(dateDir,uuid))
      except OSError, e:
        os.unlink(os.path.join(nameDir,uuid))
        raise e
    if removeOld:
      try:
        os.unlink(jsonpath)
      except OSError:
        self.logger.warning("cannot unlink Json", jsonpath, os.listdir(os.path.split(jsonpath)[0]))
        return False
      try:
        os.unlink(dumppath)
      except OSError:
        self.logger.warning("cannot unlink Dump", dumppath, os.listdir(os.path.split(dumppath)[0]))
        return False
    return True

  #-----------------------------------------------------------------------------------------------------------------
  def getJson (self, uuid):
    """
    Returns an absolute pathname for the json file for a given uuid.
    Raises OSError if the file is missing
    """
    fname = "%s%s"%(uuid,self.jsonSuffix)
    path,parts = self.lookupNamePath(uuid)
    if path:
      fullPath = os.path.join(path,fname)
      # os.stat is moderately faster than trying to open for reading
      self.readableOrThrow(fullPath)
      return fullPath
    raise OSError(errno.ENOENT,'No such file: %s%s'%(uuid,fname))

  #-----------------------------------------------------------------------------------------------------------------
  def getDump (self, uuid):
    """
    Returns an absolute pathname for the dump file for a given uuid.
    Raises OSError if the file is missing
    """
    fname = "%s%s"%(uuid,self.dumpSuffix)
    path,parts = self.lookupNamePath(uuid)
    if path:
      fullPath = os.path.join(path,fname)
      # os.stat is moderately faster than trying to open for reading
      self.readableOrThrow(fullPath)
      return fullPath
    raise OSError(errno.ENOENT,'No such file: %s%s'%(uuid,fname))

  #-----------------------------------------------------------------------------------------------------------------
  def markAsSeen (self,uuid):
    """
    Removes the links associated with the two data files for this uuid, thus marking them as seen.
    Quietly returns if the uuid has no associated links.
    """
    namePath,parts = self.namePath(uuid)
    dpath = None
    state = 'find'
    try:
      dpath = os.path.join(namePath,os.readlink(os.path.join(namePath,uuid)))
      state = 'unlink'
      os.unlink(os.path.join(dpath,uuid))
    except OSError, e:
      if 2 == e.errno: # no such file or directory
        pass
      else:
        raise e
    try:
      os.unlink(os.path.join(namePath,uuid))
    except OSError, e:
      if 2 == e.errno: # no such file or directory
        pass
      else:
        raise e

  #-----------------------------------------------------------------------------------------------------------------
  def destructiveDateWalk (self):
    """
    This function is a generator that yields all uuids found by walking the date branch of the file system.
    Just before yielding a value, it deletes both the links (from date to name and from name to date)
    After visiting all the uuids in a given date branch, recursively travels up, deleting any empty subdirectories
    Since the file system may be manipulated in a different thread, if no .json or .dump file is found, the
    links are left, and we do not yield that uuid
    """
    def handleLink(dir,name):
      nameDir = self.namePath(name)[0]
      if not os.path.isfile(os.path.join(nameDir,name+self.jsonSuffix)):
        return None
      if not os.path.isfile(os.path.join(nameDir,name+self.dumpSuffix)):
        return None
      if os.path.islink(os.path.join(nameDir,name)):
        os.unlink(os.path.join(nameDir,name))
        os.unlink(os.path.join(dir,name))
        return name
        
    dailyParts = os.listdir(self.root)
    for daily in dailyParts:
      for dir,dirs,files in os.walk(os.sep.join((self.root,daily,self.dateName))):
        if os.path.split(dir)[0] == os.path.split(self.datePath(datetime.datetime.now())[0]):
         continue
        # the links are all to (relative) directories, so we need not look at files
        for d in dirs:
          if os.path.islink(os.path.join(dir,d)):
            r = handleLink(dir,d)
            if r:
              yield r
        # after finishing a given directory...
        socorro_fs.cleanEmptySubdirectories(os.path.join(self.root,daily),dir)

  #-----------------------------------------------------------------------------------------------------------------
  def remove (self,uuid, timestamp=None):
    """
    Removes all instances of the uuid from the file system including
      the json file, the dump file, and the two links if they still exist.
    If it finds no trace of the uuid: No links, no data files, it raises a NoSuchUuidFound exception.
    Attempts to remove root/daily/date subtree for empty levels above this date storage
    If self.cleanIndexDirectories, attempts to remove root/daily subtree, for empty levels above this name storage
    """
    namePath,nameParts = self.lookupNamePath(uuid,timestamp)
    x = '^'*(len('/Users/griswolf/work/Mozilla/socorro/socorro/unittest/lib')-2)
    something = 0j
    if namePath:
      try:
        datePath = os.path.join(namePath,os.readlink(os.path.join(namePath,uuid)))
        if os.path.exists(datePath) and os.path.isdir(datePath):
          # We have a date and name path
          print 'DP: ',x,datePath
          print 'ADP:',os.path.abspath(datePath)
          self._remove(uuid,namePath,nameParts,os.path.abspath(datePath),[])
          something += 1
        else:
          raise OSError # just to get to the next block
      except OSError:
        datePath,dateParts = self.lookupOoidInDatePath(timestamp,uuid)
        if datePath:
          print 'DP: ',x,datePath
          print 'ADP:',os.path.abspath(datePath)
          self._remove(uuid,namePath,nameParts,os.path.abspath(datePath),dateParts)
          something += 1
        else:
          self._remove(uuid,namePath,nameParts,None,[])
          something += 1
    else:
      datePath,dateParts = self.lookupOoidInDatePath(timestamp,uuid)
      if datePath:
        self._remove(uuid,None,None,datePath,dateParts)
        something += 1
    if not something:
      self.logger.warning("%s - %s was totally unknown" % (threading.currentThread().getName(), uuid))
      raise NoSuchUuidFound, "no trace of %s was found" % uuid

  def _remove(self,uuid,namePath,nameParts,datePath,dateParts):
    seenCount = 0
    dailyPart = None
    if nameParts:
      dailyPart = nameParts[1]
    elif namePath:
      dailyPart = namePath.split(os.sep,2)[1]
    elif dateParts:
      dailyPart = dateParts[1]
    elif datePath:
      dailyPart = datePath.split(os.sep,2)[1]
    if not dailyPart:
      return
    stopper = os.path.join(self.root,dailyPart)
    # unlink on the name side first, thereby erasing any hope of removing relative paths from here...
    if namePath:
      try:
        os.unlink(os.path.join(namePath,uuid))
        seenCount += 1
      except:
        pass
      try:
        os.unlink(os.path.join(namePath,uuid+self.jsonSuffix))
        seenCount += 1
      except:
        pass
      try:
        os.unlink(os.path.join(namePath,uuid+self.dumpSuffix))
        seenCount += 1
      except:
        pass
      if self.cleanIndexDirectories:
        try:
          socorro_fs.cleanEmptySubdirectories(stopper,namePath) #clean out name side if possible
        except OSError, x:
          print 'OH OH',x
          pass
    # and the date directory
    if datePath:
      try:
        os.unlink(os.path.join(datePath,uuid))
        seenCount += 1
      except:
        pass
      try:
        socorro_fs.cleanEmptySubdirectories(stopper,datePath)
      except:
        pass
    if not seenCount:
      self.logger.warning("%s - %s was totally unknown" % (threading.currentThread().getName(), uuid))
      raise NoSuchUuidFound, "no trace of %s was found" % uuid
    
#   #-----------------------------------------------------------------------------------------------------------------
#   def move (self, uuid, newAbsolutePath):
#     """
#     Moves the json file then the dump file to newAbsolutePath.
#     Removes associated symbolic links if they still exist.
#     Raises IOError if either the json or dump file for the uuid is not found, and retains any links, but does not roll
#     back the json file if the dump file is not found.
#     """
#     namePath = self.namePath(uuid)[0]
#     shutil.move(os.path.join(namePath,uuid+self.jsonSuffix), os.path.join(newAbsolutePath, uuid+self.jsonSuffix))
#     shutil.move(os.path.join(namePath,uuid+self.dumpSuffix), os.path.join(newAbsolutePath, uuid+self.dumpSuffix))
#     try:
#       self.remove(uuid) # remove links, if any
#     except NoSuchUuidFound:
#       pass # there were no links


#   #-----------------------------------------------------------------------------------------------------------------
#   def removeOlderThan (self, timestamp):
#     """
#     Walks the date branch removing all entries strictly older than the timestamp.
#     Removes the corresponding entries in the name branch as well as cleans up empty date directories
#     """
#     dailyparts = os.listdir(self.root)
#     for day in dailyparts:
#       dir = os.path.join(self.root,day)
#       if not os.isdir(dir):
#         continue
#       stamp = datetime.datetime(int(day[:4]),int(day[4:6]),int(day[6:8]))
#       if stamp < timestamp:
#         shutil.rmtree(dir,True)

#   def toDateFromName(self,uuid):
#     """Given uuid, get the relative path to the top of the date directory from the name location"""
#     depth = socorro_ooid.depthFromOoid(uuid)
#     if not depth: depth = 4 # prior, when hardcoded depth=4, uuid[-8:] was yyyymmdd, year was always (20xx)
#     ups = [os.pardir for x in range(depth+1)]
#     ups.append(self.dateName)
#     return os.sep.join(ups)


