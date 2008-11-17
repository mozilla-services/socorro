import datetime as DT
import os
import os.path
import shutil
import stat
import errno
import threading

from stat import S_IRGRP, S_IXGRP, S_IWGRP, S_IRUSR, S_IXUSR, S_IWUSR, S_ISGID

import socorro.lib.util as socorro_util
import socorro.lib.ooid as socorro_ooid

class NoSuchUuidFound(Exception):
  pass

#=================================================================================================================
class JsonDumpStorage(object):
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
  def __init__(self, root=".", maxDirectoryEntries=1024, **kwargs):
    """
    Take note of our root directory, maximum allowed date->name links per directory, some relative relations, and
    whatever else we may need. Much of this (c|sh)ould be read from a config file.
    """
    super(JsonDumpStorage, self).__init__()
    self.root = root
    self.maxDirectoryEntries = maxDirectoryEntries
    self.dateName = kwargs.get('dateName','date')
    self.indexName = kwargs.get('indexName','name')
    tmp = kwargs.get('cleanIndexDirectories','false')
    self.cleanIndexDirectories = 'true' == tmp.lower()
    self.jsonSuffix = kwargs.get('jsonSuffix','.json')
    if not self.jsonSuffix.startswith('.'):
      self.jsonSuffix = ".%s" % (self.jsonSuffix)
    self.dumpSuffix = kwargs.get('dumpSuffix','.dump')
    if not self.dumpSuffix.startswith('.'):
      self.dumpSuffix = ".%s" % (self.dumpSuffix)
    self.dateBranch = os.path.join(self.root,self.dateName)
    self.nameBranch = os.path.join(self.root,self.indexName)
    self.dumpPermissions = int(kwargs.get('dumpPermissions','%d'%(S_IRGRP | S_IWGRP | S_IRUSR | S_IWUSR)))
    self.dirPermissions = int(kwargs.get('dirPermissions', '%d'%(S_IRGRP | S_IXGRP | S_IWGRP | S_IRUSR | S_IXUSR | S_IWUSR)))
    self.dumpGID = kwargs.get('dumpGID',None)
    if self.dumpGID: self.dumpGID = int(self.dumpGID)
    self.logger = kwargs.get('logger', socorro_util.FakeLogger())
    self.toNameFromDate = os.sep.join(('..','..','..','..','..','..','..',self.indexName))
    self.minutesPerSlot = 5
    self.currentSuffix = {} #maps datepath including webhead to an integer suffix

  #-----------------------------------------------------------------------------------------------------------------
  def newEntry (self, uuid, webheadHostName='webhead01', timestamp=None):
    """
    Sets up the name and date storage directory branches for the given uuid.
    Creates any directories that it needs along the path to the appropriate storage location.
    Creates two relative symbolic links: the date branch link pointing to the name directory holding the files;
    the name branch link pointing to the date branch directory holding that link.
    Returns a 2-tuple containing files open for reading: (jsonfile,dumpfile)
    """
    if not timestamp: timestamp = DT.datetime.now()
    df,jf = None,None
    nameDir = self.__makeNameDir(uuid) # deliberately leave this dir behind if next line throws
    jname = os.path.join(nameDir,uuid+self.jsonSuffix)
    try:
      jf = open(jname,'w')
    except IOError,x:
      if 2 == x.errno:
        nameDir = self.__makeNameDir(uuid) # deliberately leave this dir behind if next line throws
        jf = open(jname,'w')
      else:
        raise x
    dateDir = self.__makeDateDir(timestamp,webheadHostName)
    try:
      #os.symlink(self.__dateRelativePath(timestamp,webheadHostName),os.path.join(nameDir,uuid))
      # directly calculate the date relative path rather than calling the method which does a bit more work
      # if this matters at all, we should re-write __dateRelativePath to do the next line and call it both places
      os.symlink(os.path.join(self.toDateFromName(uuid), dateDir[len(self.root)+len(self.dateName)+2:]),os.path.join(nameDir,uuid))
      os.symlink(self.__nameRelativePath(uuid),os.path.join(dateDir,uuid))
      os.chmod(jname,self.dumpPermissions)
      dname = os.path.join(nameDir,uuid+self.dumpSuffix)
      df = open(dname,'w')
      os.chmod(dname,self.dumpPermissions)
      if self.dumpGID:
        os.chown(os.path.join(nameDir,uuid+self.jsonSuffix),-1,self.dumpGID)
        os.chown(os.path.join(nameDir,uuid+self.dumpSuffix),-1,self.dumpGID)
    finally:
      if not jf or not df:
        if jf: jf.close()
        if df: df.close()
        os.unlink(os.path.join(dateDir,uuid))
        os.unlink(os.path.join(nameDir,uuid))
        df,jf = None,None
    return (jf,df)

  #-----------------------------------------------------------------------------------------------------------------
  def copyFrom(self, uuid, jsonpath, dumppath, webheadHostName, timestamp, createLinks = False, removeOld = False):
    """
    Copy the two crash files from the given path to our current storage location in nameBranch
    If createLinks, use webheadHostName and timestamp to insert links to and from the dateBranch
    If removeOld, after the files are copied, attempt to unlink the originals
    raises OSError if the paths are unreadable or if removeOld is true and either file cannot be unlinked

    """
    nameDir = self.__makeNameDir(uuid) # deliberately leave this dir behind if next line throws
    jsonNewPath = '%s%s%s%s' % (nameDir,os.sep,uuid,self.jsonSuffix)
    dumpNewPath = '%s%s%s%s' % (nameDir,os.sep,uuid,self.dumpSuffix)
    try:
      shutil.copy2(jsonpath,jsonNewPath)
    except IOError,x:
      if 2 == x.errno:
        nameDir = self.__makeNameDir(uuid) # deliberately leave this dir behind if next line throws
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
      dateDir = self.__makeDateDir(timestamp,webheadHostName)
      os.symlink(self.__dateRelativePath(timestamp,webheadHostName,uuid),os.path.join(nameDir,uuid))
      try:
        os.symlink(self.__nameRelativePath(uuid),os.path.join(dateDir,uuid))
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
  def transferOne (self, uuid, anotherJsonDumpStorage, copyLinksBoolean=True, makeNewDateLinksBoolean=False, aDate=None):
    """
    Transfer a uuid from anotherJsonDumpStorage into this instance of JsonDumpStorage
    uuid - the id
    anotherJsonDumpStorage - the directory holding the 'date' (if any) and 'name' data for the uuid
    copyLinksBoolean - True: copy links, if any; False: copy no links
    makeNewDateLinksBoolean - make new date entries in self using aDate
    aDate - for creating new date links, None means now
    NOTE: Assumes that the path names and suffixes for anotherJsonDumpStorage are the same as for self
    """
    if copyLinksBoolean and makeNewDateLinksBoolean:
      self.logger.warning("transferOne(...) True == (copyLinksBoolean AND makeNewDateLinksBoolean). Will not copy original links")
    if not aDate: aDate = DT.datetime.now()
    self.__transferOne(uuid,anotherJsonDumpStorage,copyLinksBoolean,makeNewDateLinksBoolean,aDate)

  #-----------------------------------------------------------------------------------------------------------------
  def transferMany (self, iterable, anotherJsonDumpStorage, copyLinksBoolean=True, makeNewDateLinksBoolean=False, aDate=None):
    """
    Transfer a sequences of uuids from anotherJsonDumpStorage into this instance of JsonDumpStorage
    iterable - the iterable giving a sequence of uuids
    anotherJsonDumpStorage - the directory holding the 'date' (if any) and 'name' data for the uuid
    copyLinksBoolean - True: copy links, if any; False: copy no links
    makeNewDateLinksBoolean - make new date entries in self using aDate
    aDate - for creating new date links, None means now
    NOTE: Assumes that the path names and suffixes for anotherJsonDumpStorage are the same as for self
    """
    if copyLinksBoolean and makeNewDateLinksBoolean:
      self.logger.warning("transferOne(...) True == (copyLinksBoolean AND makeNewDateLinksBoolean). Will not copy original links")
    if not aDate: aDate = DT.datetime.now()
    for uuid in iterable:
      self.__transferOne(uuid,anotherJsonDumpStorage,copyLinksBoolean,makeNewDateLinksBoolean,aDate)

  #-----------------------------------------------------------------------------------------------------------------
  def getJson (self, uuid):
    """
    Returns an absolute pathname for the json file for a given uuid.
    Raises OSError if the file is missing
    """
    path = "%s%s%s%s" % (self.__nameAbsPath(uuid),os.sep,uuid,self.jsonSuffix)
    # os.stat is moderately faster than trying to open for reading
    self.__readableOrThrow(path)
    return path

  #-----------------------------------------------------------------------------------------------------------------
  def getDump (self, uuid):
    """
    Returns an absolute pathname for the dump file for a given uuid.
    Raises OSError if the file is missing
    """
    path = "%s%s%s%s" % (self.__nameAbsPath(uuid),os.sep,uuid,self.dumpSuffix)
    # os.stat is moderately faster than trying to open for reading
    self.__readableOrThrow(path)
    return path

  #-----------------------------------------------------------------------------------------------------------------
  def markAsSeen (self,uuid):
    """
    Removes the links associated with the two data files for this uuid, thus marking them as seen.
    Quietly returns if the uuid has no associated links.
    """
    namePath = self.__nameAbsPath(uuid)
    dpath = None
    try:
      dpath = os.path.join(namePath,os.readlink(os.path.join(namePath,uuid)))
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
      nameDir = self.__nameAbsPath(name)
      if not os.path.isfile(os.path.join(nameDir,name+self.jsonSuffix)):
        return None
      if not os.path.isfile(os.path.join(nameDir,name+self.dumpSuffix)):
        return None
      if os.path.islink(os.path.join(nameDir,name)):
        os.unlink(os.path.join(nameDir,name))
        os.unlink(os.path.join(dir,name))
        return name

    for dir,dirs,files in os.walk(self.dateBranch):
      if os.path.split(dir)[0] == os.path.split(self.__dateAbsPath(DT.datetime.now(),'',False))[0]:
        continue
      # the links are all to (relative) directories, so we need not look at files
      for d in dirs:
        if os.path.islink(os.path.join(dir,d)):
          r = handleLink(dir,d)
          if r:
            yield r
      # after finishing a given directory...
      self.__cleanDirectory(dir, self.dateName)

  #-----------------------------------------------------------------------------------------------------------------
  def remove (self,uuid):
    """
    Removes all instances of the uuid from the file system including the json file, the dump file, and the two links if they still exist.
    If it finds no trace of the uuid: No links, no data files, it raises a NoSuchUuidFound exception.
    """
    namePath = self.__nameAbsPath(uuid)
    seenCount = 0
    depth = socorro_ooid.depthFromOoid(uuid)
    if not depth: depth = 4 # prior, when hardcoded depth=4, uuid[-8:] was yyyymmdd, year was always (20xx)
    try:
      datePath = os.path.join(namePath,os.readlink(os.path.join(namePath,uuid)))
      os.unlink(os.path.join(namePath,uuid))
      os.unlink(os.path.join(datePath,uuid))
      seenCount += 1
      self.__cleanDirectory(datePath, self.dateName)
    except OSError:
      self.logger.debug("%s - %s Missing at least one link" % (threading.currentThread().getName(), uuid))
    try:
      os.unlink(os.path.join(namePath,uuid+self.jsonSuffix))
      seenCount += 1
    except:
      self.logger.debug("%s - %s Missing json file" % (threading.currentThread().getName(), uuid))
    try:
      os.unlink(os.path.join(namePath,uuid+self.dumpSuffix))
      seenCount += 1
    except:
      self.logger.debug("%s - %s Missing dump file" % (threading.currentThread().getName(), uuid))
    if self.cleanIndexDirectories:
      try:
        self.__cleanDirectory(namePath,namePath.split(os.sep)[-depth:1-depth][0]) #clean only as far back as the first name level
      except OSError:
        pass
    if not seenCount:
      self.logger.warning("%s - %s was totally unknown" % (threading.currentThread().getName(), uuid))
      raise NoSuchUuidFound, "no trace of %s was found" % uuid

  #-----------------------------------------------------------------------------------------------------------------
  def move (self, uuid, newAbsolutePath):
    """
    Moves the json file then the dump file to newAbsolutePath.
    Removes associated symbolic links if they still exist.
    Raises IOError if either the json or dump file for the uuid is not found, and retains any links, but does not roll
    back the json file if the dump file is not found.
    """
    namePath = self.__nameAbsPath(uuid)
    shutil.move(os.path.join(namePath,uuid+self.jsonSuffix), os.path.join(newAbsolutePath, uuid+self.jsonSuffix))
    shutil.move(os.path.join(namePath,uuid+self.dumpSuffix), os.path.join(newAbsolutePath, uuid+self.dumpSuffix))
    try:
      self.remove(uuid) # remove links, if any
    except NoSuchUuidFound:
      pass # there were no links


  #-----------------------------------------------------------------------------------------------------------------
  def removeOlderThan (self, timestamp):
    """
    Walks the date branch removing all entries strictly older than the timestamp.
    Removes the corresponding entries in the name branch as well as cleans up empty date directories
    """
    for dir,dirs,files in os.walk(self.dateBranch,topdown = False):
      #self.logger.debug("considering: %s", dir)
      thisStamp = self.__pathToDate(dir)
      if thisStamp and (thisStamp < timestamp):
        # The links are all to (relative) directories, so no need to handle files
        for i in dirs:
          if os.path.islink(os.path.join(dir,i)):
            #self.logger.debug("removing: %s", i)
            self.remove(i)
      #contents = os.listdir(dir)
      #if contents == []:
        #self.logger.debug("killing empty date directory: %s", dir)
      #  os.rmdir(dir)

  def toDateFromName(self,uuid):
    """Given uuid, get the relative path to the top of the date directory from the name location"""
    depth = socorro_ooid.depthFromOoid(uuid)
    if not depth: depth = 4 # prior, when hardcoded depth=4, uuid[-8:] was yyyymmdd, year was always (20xx)
    ups = ['..' for x in range(depth+1)]
    ups.append(self.dateName)
    return os.sep.join(ups)
    #= os.sep.join(('..','..','..','..','..',self.dateName))


  #=================================================================================================================
  # private methods
  def __transferOne(self,uuid,fromJson,copyLinksBoolean,makeNewDateLinksBoolean,aDate):
    webheadHostName = "webhead01"
    didCopy = False
    if copyLinksBoolean and not makeNewDateLinksBoolean:
      dpath = fromJson.getJson(uuid)[:-len(fromJson.jsonSuffix)]
      try:
        datePart, webheadHostName = os.path.split(os.readlink(dpath))
        whparts = webheadHostName.split('_')
        if len(whparts) > 1:
          webheadHostName = '_'.join(whparts[:-1]) # lose the trailing sequence number
        datePart = datePart[1+len(fromJson.toDateFromName(uuid)):]
        aDate = DT.datetime(*[int(x) for x in datePart.split(os.sep)])
        self.copyFrom(uuid,fromJson.getJson(uuid), fromJson.getDump(uuid), webheadHostName, aDate, createLinks=True, removeOld = False)
        didCopy = True
      except OSError,e:
        if 2 != e.errno:
          raise e

    if makeNewDateLinksBoolean:
      dpath = fromJson.getJson(uuid)[:-len(fromJson.jsonSuffix)]
      try:
        webheadHostName = os.path.split(os.readlink(dpath))[1]
        whparts = webheadHostName.split('_')
        if len(whparts) > 1:
          webheadHostName = '_'.join(whparts[:-1]) # lose the trailing sequence number
      except OSError,e:
        if 2 != e.errno:
          raise e
      self.copyFrom(uuid,fromJson.getJson(uuid), fromJson.getDump(uuid),webheadHostName,aDate,createLinks=True, removeOld = False)
    elif not didCopy:
      self.copyFrom(uuid,fromJson.getJson(uuid), fromJson.getDump(uuid),webheadHostName,aDate,createLinks=False, removeOld = False)

  def __nameAbsPath(self,uuid):
    """Get a name path in absolute, i.e. %(root)s based format"""
    return self.__namePath(uuid,self.nameBranch)

  def __nameRelativePath(self,uuid):
    """ get a name path relative to a date-based location"""
    return self.__namePath(uuid,self.toNameFromDate)

  def __dateRelativePath(self,dt,head,uuid):
    """Get a date path relative to a name storage location"""
    return self.__datePath(dt,head,self.toDateFromName(uuid))

  def __dateAbsPath(self,dt,head, checkSize = False):
    """Get a date path in absolute, i.e. %(root)s based format"""
    return self.__datePath(dt,head,self.dateBranch, checkSize)

  def __makeNameDir(self, uuid):
    """
    Parse the uuid into a directory path create directory as needed, return path to directory.
    Raises OSError on failure
    """
    path = self.__nameAbsPath(uuid)
    omask = os.umask(0)
    try:
      os.makedirs(path,self.dirPermissions)
      self.__fixupGroup(path,self.dumpGID)
    except OSError, e:
      os.umask(omask)
      if not os.path.isdir(path):
        raise e
    os.umask(omask)
    return path

  def __namePath(self,uuid,startswith):
    """Because the name structure is almost simple, so is the method that creates one"""
    depth = socorro_ooid.depthFromOoid(uuid)
    if not depth: depth = 4 # prior, when hardcoded depth=4, uuid[-8:] was yyyymmdd, year was always (20xx)
    # split the first 2*depth characters into duples, join them, and prepend startswith
    return os.sep.join([startswith,os.sep.join([ uuid[2*x:2*x+2] for x in range(depth)])])

  def __currentSlot(self):
    minute = DT.datetime.now().minute
    return self.minutesPerSlot * int(minute/self.minutesPerSlot)

  def __datePath(self,dt,head,startswith,checkSize=False):
    """A workhorse that makes a path from a date and some other things. Param checkSize is true if we are seeing
    whether to create a new subdirectory (from newEntry())
    """
    m = dt.minute
    slot = self.minutesPerSlot * int(m/self.minutesPerSlot)
    #           bb//yyyy//mmmm//dddd//hhhh//5min//hd
    dpathKey = "%s%s%04d%s%02d%s%02d%s%02d%s%02d%s%s" %  (startswith,os.sep,dt.year,os.sep,dt.month,os.sep,dt.day,os.sep,dt.hour,os.sep,slot,os.sep,head)
    dpath = "%s_%d" %(dpathKey, self.currentSuffix.setdefault(dpathKey,0))
    if checkSize: # then we are potentially creating a directory to hold links, must honor maxDirectoryEntries
      try:
        # because we restart with currentSuffix empty, we need to loop out until we find a good one
        while len(os.listdir(dpath)) >= self.maxDirectoryEntries:
          self.currentSuffix[dpathKey] += 1
          dpath = "%s_%d" %(dpathKey, self.currentSuffix[dpathKey])
      except OSError, e:
        if errno.ENOENT == e.errno:
          pass
        else:
          raise e
    return dpath

  def __pathToDate(self,path):
    """ Parse an index/date path into a datetime instance, or None if not possible"""
    part = path.split(self.dateBranch)[1] # cdr has the date part, starts with '/'
    if part:
      data = part.split(os.sep)[1:-1] # get rid of leading empty, trailing webhead
      if len(data) < 5:
        return None
      return DT.datetime(*[int(x) for x in data])
    return None

  def __makeDateDir(self, dt, head):
    """ parse the datetime.datetime dt and webhead name head into a directory path, check for overflow,
    create directory as needed, return path to directory. Raises OSError on failure.
    """
    dpath = self.__dateAbsPath(dt,head,checkSize=True)
    omask = os.umask(0)
    try:
      os.makedirs(dpath,self.dirPermissions)
      self.__fixupGroup(dpath,self.dumpGID)
    except OSError,e:
      os.umask(omask)
      if not os.path.isdir(dpath):
        raise e
    os.umask(omask)
    return dpath

  def __readableOrThrow(self, path):
    """ raises OSError if not """
    if not os.stat(path).st_mode & (stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH):
      raise OSError('Cannot read')

  def __fixupGroup(self,path,gid):
    if None == gid: return
    while path != self.root:
      os.chown(path,-1,gid)
      path = os.path.split(path)[0]

  def __cleanDirectory(self,basepath,basePathLimit):
    """Look higher and higher up the storage branch until you hit the top or a non-empty sub-directory"""
    opath = basepath
    while True:
      path,tail = os.path.split(opath)
      if basePathLimit == tail:
        break
      try:
        os.rmdir(opath)
      except OSError,e:
        if errno.ENOTEMPTY == e.errno: # Directory not empty
          break
        else:
          raise e
      opath = path




