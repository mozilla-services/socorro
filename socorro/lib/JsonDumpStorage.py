import datetime as DT
import os
import stat
import errno

#-----------------------------------------------------------------------------------------------------------------
class JsonDumpStorage(object):
  """ This class implements a file system storage scheme for the JSON and dump files of the Socorro project.
  It create a tree with two branches: the radix branch and the date branch.
  The radix branch consists of paths based on the first 8 characters of the uuid file name. It holds the two
  data files and a relative symbolic link to the date branch directory associated with the particular uuid.
    For the uuid:  22adfb61-f75b-11dc-b6be-001321b0783d
      the json file is stored as %(root)s/radix/22/ad/fb/61/22adfb61-f75b-11dc-b6be-001321b0783d.json
      the dump file is stored as %(root)s/radix/22/ad/fb/61/22adfb61-f75b-11dc-b6be-001321b0783d.dump
      the symbolic link is stored as %(root)s/radix/22/ad/fb/61/22adfb61-f75b-11dc-b6be-001321b0783d
        and (see below) references %(toDateFromRadix)s/date/2008/09/30/12/05/webhead01_0
  The date branch consists of paths based on the year, month, day, hour, minute-segment, webhead host name and
  a small sequence number
  For each uuid, it holds a relative symbolic link referring to the actual storage (radix) directory holding
  the data for that uuid.
    For the uuid above, submitted at 2008-09-30T12:05 from webhead01
      the symbolic link is stored as %(root)s/date/2008/09/30/12/05/webhead01_0/22adfb61-f75b-11dc-b6be-001321b0783d
        and references %(toRadixFromDate)s/radix/22/ad/fb/61

  Note: The symbolic links are relative, so they begin with several rounds of '../'. This is to avoid issues that
  might arise from variously mounted nfs volumes. If the layout changes, self.toRadixFromDate and toDateFromRadix
  must be changed to match, as well as a number of the private methods.

  Note: If the number of links in a particular webhead subdirectory would exceed maxDirectoryEntries, then a new
  webhead directory is created by appending a larger '_N' : .../webhead01_0 first, then .../webhead01_1 etc.
  For the moment, maxDirectoryEntries is ignored for the radix branch. If this becomes a problem, another radix
  level might be added, either skipping the '-' that is next, or perhaps better, using the last two characters.
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, root=".", maxDirectoryEntries=1024, **kwargs):
    """
    Take note of our root directory, maximum allowed date->radix links per directory, some relative relations, and
    whatever else we may need. Much of this (c|sh)ould be read from a config file.
    """
    super(JsonDumpStorage, self).__init__()
    self.root = root
    self.maxDirectoryEntries = maxDirectoryEntries
    self.dateName = kwargs.get('dateName','date')
    self.indexName = kwargs.get('indexName','radix')
    self.jsonSuffix = kwargs.get('jsonSuffix','.json')
    if not self.jsonSuffix.startswith('.'):
      self.jsonSuffix = ".%s" % (self.jsonSuffix)
    self.dumpSuffix = kwargs.get('dumpSuffix','.dump')
    if not self.dumpSuffix.startswith('.'):
      self.dumpSuffix = ".%s" % (self.dumpSuffix)
    self.dateBranch = os.path.join(self.root,self.dateName)
    self.radixBranch = os.path.join(self.root,self.indexName)
    self.toRadixFromDate = os.sep.join(('..','..','..','..','..','..','..',self.indexName))
    self.toDateFromRadix = os.sep.join(('..','..','..','..','..',self.dateName))
    self.minutesPerSlot = 5
    self.slotRange = range(self.minutesPerSlot, 60, self.minutesPerSlot)
    self.currentSuffix = {} #maps datepath including webhead to an integer suffix
  #-----------------------------------------------------------------------------------------------------------------
  def newEntry (self, uuid, webheadHostName='webhead01', timestamp=DT.datetime.now()):
    """
    Sets up the radix and date storage directory branches for the given uuid.
    Creates any directories that it needs along the path to the appropriate storage location.
    Creates two relative symbolic links: the date branch link pointing to the radix directory holding the files;
    the radix branch link pointing to the date branch directory holding that link.
    Returns a 2-tuple containing files open for reading: (jsonfile,dumpfile)
    """
    df,jf = None,None
    radixDir = self.__makeRadixDir(uuid) # deliberately leave this dir behind if next line throws
    dateDir = self.__makeDateDir(timestamp,webheadHostName)
    try:
      os.symlink(self.__dateRelativePath(timestamp,webheadHostName),os.path.join(radixDir,uuid))
      os.symlink(self.__radixRelativePath(uuid),os.path.join(dateDir,uuid))
      jf = open(os.path.join(radixDir,uuid+self.jsonSuffix),'w')
      df = open(os.path.join(radixDir,uuid+self.dumpSuffix),'w')
    finally:
      if not jf or not df:
        if jf: jf.close()
        if df: df.close()
        os.unlink(os.path.join(dateDir,uuid))
        os.unlink(os.path.join(radixDir,uuid))
        df,jf = None,None
    return (jf,df)
  
  #-----------------------------------------------------------------------------------------------------------------
  def getJson (self, uuid):
    """
    Returns an absolute pathname for the json file for a given uuid.
    Raises OSError if the file is missing
    """
    path = "%s%s%s%s" % (self.__radixAbsPath(uuid),os.sep,uuid,self.jsonSuffix)
    # os.stat is moderately faster than trying to open for reading
    self.__readableOrThrow(path)
    return path
    
  #-----------------------------------------------------------------------------------------------------------------
  def getDump (self, uuid):
    """
    Returns an absolute pathname for the dump file for a given uuid.
    Raises OSError if the file is missing
    """
    path = "%s%s%s%s" % (self.__radixAbsPath(uuid),os.sep,uuid,self.dumpSuffix)
    # os.stat is moderately faster than trying to open for reading
    self.__readableOrThrow(path)
    return path
  
  #-----------------------------------------------------------------------------------------------------------------
  def markAsSeen (self,uuid):
    """
    Removes the links associated with the two data files for this uuid, thus marking them as seen.
    Quietly returns if the uuid has no associated links.
    """
    rpath = self.__radixAbsPath(uuid)
    dpath = None
    try:
      dpath = os.path.join(rpath,os.readlink(os.path.join(rpath,uuid)))
      os.unlink(os.path.join(dpath,uuid))
    except OSError, e:
      if 2 == e.errno: # no such file or directory
        pass
      else:
        raise e
    try:
      os.unlink(os.path.join(rpath,uuid))
    except OSError, e:
      if 2 == e.errno: # no such file or directory
        pass
      else:
        raise e

  
  #-----------------------------------------------------------------------------------------------------------------
  def destructiveDateWalk (self):
    """
    This function is a generator that yields all uuids found by walking the date branch of the file system.
    Just before yielding a value, it deletes both the links (from date to radix and from radix to date)
    After visiting all the uuids in a given date branch, recursively travels up, deleting any empty subdirectories
    Since the file system may be manipulated in a different thread, if no .json or .dump file is found, the
    links are left, and we do not yield that uuid
    """
    def handleLink(dir,name):
      radixDir = self.__radixAbsPath(name)
      if not os.path.isfile(os.path.join(radixDir,name+self.jsonSuffix)):
        return None
      if not os.path.isfile(os.path.join(radixDir,name+self.dumpSuffix)):
        return None
      if os.path.islink(os.path.join(radixDir,name)):
        os.unlink(os.path.join(radixDir,name))
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
      self.__cleanDirectory(dir)
  
  #-----------------------------------------------------------------------------------------------------------------
  def remove (self,uuid):
    """
    Removes all instances of the uuid from the file system including the json file, the dump
    file, and the two links if they still exist.
    Ignores missing link, json and dump files: You may call it with bogus data, though of course you
    should not
    """
    rpath = self.__radixAbsPath(uuid)
    dpath = None
    try:
      try:
        dpath = os.path.join(rpath,os.readlink(os.path.join(rpath,uuid)))
        os.unlink(os.path.join(dpath,uuid))
        os.unlink(os.path.join(rpath,uuid))
      except:
        pass
    finally:
      try:
        os.unlink(os.path.join(rpath,uuid+self.jsonSuffix))
      except:
        pass
      try:
        os.unlink(os.path.join(rpath,uuid+self.dumpSuffix))
      except:
        pass
    
  #-----------------------------------------------------------------------------------------------------------------
  def move (self, uuid, newAbsolutePath):
    """
    Moves the json file then the dump file to newAbsolutePath.
    Removes associated symbolic links if they still exist.
    Recursively travels up from the date location deleting any empty subdirectories
    Raises IOError if either the json or dump file for the uuid is not found, and retains any links, but does not roll
    back the json file if the dump file is not found.
    """
    rpath = self.__radixAbsPath(uuid)
    os.rename(os.path.join(rpath,uuid+self.jsonSuffix), os.path.join(newAbsolutePath, uuid+self.jsonSuffix))
    os.rename(os.path.join(rpath,uuid+self.dumpSuffix), os.path.join(newAbsolutePath, uuid+self.dumpSuffix))

    self.remove(uuid)
      

  #-----------------------------------------------------------------------------------------------------------------
  def removeOlderThan (self, timestamp):
    """
    Walks the date branch removing all entries strictly older than the timestamp.
    Removes the corresponding entries in the radix branch.  Whenever it removes the last item in a date branch
    directory, it recursively removes the directory and its parents, as long as each is empty.
    """
    for dir,dirs,files in os.walk(self.dateBranch,topdown = True):
      thisStamp = self.__pathToDate(dir)
      if thisStamp and (thisStamp > timestamp):
        # The links are all to (relative) directories, so no need to handle files
        for i in dirs:
          if os.path.islink(os.path.join(dir,i)):
            self.remove(i)
      else:
        continue

  #=================================================================================================================
  # private methods
  def __radixAbsPath(self,uuid):
    """Get a radix path in absolute, i.e. %(root)s based format"""
    return self.__radixPath(uuid,self.radixBranch)
  
  def __radixRelativePath(self,uuid):
    """ get a radix path relative to a date-based location"""
    return self.__radixPath(uuid,self.toRadixFromDate)

  def __dateRelativePath(self,dt,head):
    """Get a date path relative to a radix storage location"""
    return self.__datePath(dt,head,self.toDateFromRadix)

  def __dateAbsPath(self,dt,head, checkSize = False):
    """Get a date path in absolute, i.e. %(root)s based format"""
    return self.__datePath(dt,head,self.dateBranch, checkSize)
                     
  def __makeRadixDir(self, uuid):
    """
    Parse the uuid into a directory path create directory as needed, return path to directory.
    Raises OSError on failure
    """
    path = self.__radixAbsPath(uuid)
    try:
      os.makedirs(path)
    except OSError, e:
      if not os.path.isdir(path):
        raise e
    return path

  def __radixPath(self,uuid,startswith):
    """Because the radix structure is simple, so is the method that creates one"""
    #       bb//ra//di//xx//xx
    return "%s%s%s%s%s%s%s%s%s" %(startswith,os.sep,uuid[0:2],os.sep,uuid[2:4],os.sep,uuid[4:6],os.sep,uuid[6:8])

  def __currentSlot(self):
    minute = DT.datetime.now().minute
    for slot in self.slotRange:
      if slot > minute:
        break
    slot -= self.minutesPerSlot

  def __datePath(self,dt,head,startswith,checkSize=False):
    """A workhorse that makes a path from a date and some other things. Param checkSize is true if we are seeing
    whether to create a new subdirectory (from newEntry())
    """
    m = dt.minute
    for slot in self.slotRange:
      if slot > m:
        break
    slot -= self.minutesPerSlot
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

  def __cleanDirectory(self,datepath):
    """Look higher and higher up the storage branch until you hit the top or a non-empty sub-directory"""
    opath = datepath
    while True:
      path,tail = os.path.split(opath)
      if self.dateName == tail:
        break
      try:
        os.rmdir(opath)
      except OSError,e:
        if errno.ENOTEMPTY == e.errno: # Directory not empty
          break
        else:
          raise e
      opath = path
  
