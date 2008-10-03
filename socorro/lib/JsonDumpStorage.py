import datetime as dt
import os

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
        and (see below) references %(root)s/date/2008/09/30/12/05/webhead01_0
  The date branch consists of paths based on the year, month, day, hour, minute-segment, webhead host name and
  a small sequence number
  For each uuid, it holds a relative symbolic link referring to the actual storage (radix) directory holding
  data for that uuid.
    For the uuid above, submitted at 2008-09-30T12:05 from webhead01
      the symbolic link is stored as %(root)s/date/2008/09/30/12/05/webhead01_0/22adfb61-f75b-11dc-b6be-001321b0783d
        and references %(root)s/radix/22/ad/fb/61

  Note: The symbolic links are relative, so they begin with several rounds of '../'. This is to avoid issues that
  might arise from variously mounted nfs volumes.

  Note: If the number of links in a particular webhead subdirectory would exceed maxDirectoryEntries, then a new
  webhead directory is created by appending a larger '_N' : .../webhead01_0 first, then .../webhead01_1 etc.
  For the moment, maxDirectoryEntries is ignored for the radix branch. If this becomes a problem, another radix
  level might be added, not necessarily the next two characters (one of which will always be '-'). Brief examination
  seems to prefer the _last_ two characters for the next radix level, if needed.
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, root=".", maxDirectoryEntries=1024, **kwargs):
    """
    Take note of our root directory, maximum allowed date->radix links per directory, some relative relations, and
    whatever else we may need. Much of this could be read from a config file.
    """
    super(JsonDumpStorage, self).__init__()
    self.root = root
    self.maxDirectoryEntries = maxDirectoryEntries
    self.dateBranch = os.path.join(self.root,'date')
    self.radixBranch = os.path.join(self.root,'radix')
    self.toRadixFromDate = os.sep.join(('..','..','..','..','..','..','..','radix'))
    self.toDateFromRadix = os.sep.join(('..','..','..','..','..','date'))
    self.minutesPerSlot = 5
  #-----------------------------------------------------------------------------------------------------------------
  def newEntry (self, uuid, webheadHostName='webhead01', timestamp=dt.datetime.now()):
    """ this function will setup the radix and date storage directory branches for the given uuid.
    It will create any or all directories that it needs along the path to the appropriate storage location.
    It will create the two relative symbolic links: the date branch link pointing to the json file;
    the radix branch link pointing to the date branch link.  It returns a 2-tuple containing two file handles
    open for writing.  The first file handle will be set for ".../uuid.json", while the second will be for
    ".../uuid.dump"
    """
    radixDir = self._makeRadixDir(uuid) # deliberately leave this dir behind if next line throws
    dateDir = self._makeDateDir(timestamp,webheadHostName)
    df,jf = None,None
    try:
      os.symlink(radixDir,os.path.join(dateDir,uuid))
      os.symlink(dateDir,os.path.join(radixDir,uuid))
      jf = open(os.path.join(radixDir,uuid+'.json'),'w')
      df = open(os.path.join(radixDir,uuid+'.dump'),'w')
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
    """this function will return an absolute pathname for the json file for given uuid.
    If there is no such file or it is unreadable, it will raise an OSError
    """
    path = "%s%s%s.%s" % (self._radixDirPath(uuid),os.sep,uuid,'json')
    # os.stat is moderately faster than trying to open for reading
    self._readableOrThrow(path)
    return path
    
  #-----------------------------------------------------------------------------------------------------------------
  def getDump (self, uuid):
    """this function will return an absolute pathname for the dump file for given uuid.
    If there is no such file, it will raise an IOError exception.
    """
    path = "%s%s%s.%s" % (self._radixDirPath(uuid),os.sep,uuid,'dump')
    # os.stat is moderately faster than trying to open for reading
    self._readableOrThrow(path)
    return path
  
  #-----------------------------------------------------------------------------------------------------------------
  def openAndMarkAsSeen (self,uuid):
    """
    Returns two streams: The first is open for reading uuid.json the second open for reading uuid.dump. Also
    removes the links associated with these two files. Raises IOError if either file is missing. NOTE: You should
    call remove(uuid) after reading the data from the files.
    """
    rpath = self._radixDirPath(uuid)
    try:
      dpath = os.readlink(os.path.join(self._radixDirPath(uuid),uuid))
    except OSError, e:
      raise IOError(e)
    jf,df = None,None
    try:
      jf = open(os.path.join(rpath,uuid+'.json'))
      df = open(os.path.join(rpath,uuid+'.dump'))
    finally:
      if not jf or not df:
        if jf: jf.close()
        if df: df.close()
      else:
        os.unlink(os.path.join(self._radixDirPath(uuid),uuid))
        os.unlink(os.path.join(dpath,uuid))
        self._cleanDirectory(dpath)
    return (jf,df)
  
  #-----------------------------------------------------------------------------------------------------------------
  def destructiveDateWalk (self):
    """ this function is a generator.  It yields a series of uuids for json files found by walking the date
    branch of the file system.  However, just before yielding a value, it deletes both the date branch link
    pointing to the json file and the radix branch link pointing to the date branch link.  If the deletion of
    the date branch link results in an empty directory, then it should back down the date branch path deleting
    these empty directories.
    """
    raise StopIteration
  #-----------------------------------------------------------------------------------------------------------------
  def remove (self,uuid):
    """ this function removes all instances of the uuid from the file system including the json file, the dump
    file, and the two links if they still exist.  In addition, after a deletion, it backs down the date branch,
    deleting any empty subdirectories left behind. Raises IOError if either the json or dump file for the uuid
    is not found.
    """
    pass
  #-----------------------------------------------------------------------------------------------------------------
  def move (self, uuid, newAbsolutePath):
    """ this function moves the json and dump files to newAbsolutePath.  In addition, after a move, it removes
     the symbolic links if they still exist.  Then it backs down the date branch, deleting any empty subdirectories
     left behind. Raises IOError if either the json or dump file for the uuid is not found. 
    """
    pass
  #-----------------------------------------------------------------------------------------------------------------
  def removeOlderThan (self, timestamp):
    """ this function walks the date branch removing all entries older than the timestamp.  It also reaches across
    and removes the corresponding entries in the radix branch.  Whenever it removes the last item in a date branch
    directory, it removes the directory, too.
    """
    pass

  #=================================================================================================================
  # private data, methods
  currentSuffix = {} #maps datepath including webhead to an integer suffix
  def _radixDirPath(self,uuid):
    return "%s%s%s%s%s%s%s%s%s" %(self.radixBranch,os.sep,uuid[0:2],os.sep,uuid[2:4],os.sep,uuid[4:6],os.sep,uuid[6:8])
  
  def _makeRadixDir(self, uuid):
    """ parse the uuid into a directory path create directory as needed, return path to directory.
    Raises OSError on failure
    """
    path = self._radixDirPath(uuid)
    try:
      os.makedirs(path)
    except OSError, e:
      if not os.path.isdir(path):
        raise e
    return path

  def _dateDirPath(self,dt,head):
    m = dt.minute
    for slot in range(self.minutesPerSlot,60,self.minutesPerSlot):
      if slot > m:
        break
    slot -= self.minutesPerSlot
    #           bb//yyyy//mmmm//dddd//hhhh//5min//hd
    dpathKey = "%s%s%04d%s%02d%s%02d%s%02d%s%02d%s%s" %  (self.dateBranch,os.sep,dt.year,os.sep,dt.month,os.sep,dt.day,os.sep,dt.hour,os.sep,slot,os.sep,head)
    dpath = "%s_%d" %(dpathKey, JsonDumpStorage.currentSuffix.setdefault(dpathKey,0))
    try:
      if len(os.listdir(dpath)) >= self.maxDirectoryEntries:
        JsonDumpStorage.currentSuffix[dpathKey] += 1
        dpath = "%s_%d" %(dpathKey, JsonDumpStorage.currentSuffix[dpathKey])
    except OSError:
      pass
    return dpath
      
  def _makeDateDir(self, dt, head):
    """ parse the datetime.datetime dt and webhead name head into a directory path, check for overflow,
    create directory as needed, return path to directory. Raises OSError on failure.
    """
    dpath = self._dateDirPath(dt,head)
    try:
      os.makedirs(dpath)
    except OSError,e:
      if not os.path.isdir(dpath):
        raise e
    return dpath

  def _readableOrThrow(self, path):
    """ throws OSError if not """
    import stat
    if not os.stat(path).st_mode & (stat.S_IRUSR|stat.S_IRGRP|stat.S_IROTH):
      raise OSError('Cannot read')

  def _cleanDirectory(self,datepath):
    #FRANK: WORK ON THIS
    opath = datepath
    cur = os.listdir(opath)
    while [] == cur:
      path,tail = os.path.split(opath)
      if 'date' == tail:
        break
      os.rmdir(opath)
      opath = path
      cur = os.listdir(opath)
  
