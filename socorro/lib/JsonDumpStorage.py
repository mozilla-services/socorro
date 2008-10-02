import datetime as dt
import os


#-----------------------------------------------------------------------------------------------------------------
class JsonDumpStorage(object):
  """ This class implements a file system storage scheme for the JSON and dump files of the Socorro project.
  It create a tree with two branches: the radix branch and the date branch.
  The radix branch consists of paths based on the first 8 characters of the uuid file name.
    22adfb61-f75b-11dc-b6be-001321b0783d.json is stored as %(root)s/radix/22/ad/fb/61/22adfb61-f75b-11dc-b6be-001321b0783d.json
    the dump file follows the same template
    a relative symbolic link is also saved with the JSON and dump files pointing to the date branch symbolic link
      defined below.
  The date branch stores symbolic links to the JSON files in the radix branch.  The path made up of date parts
    followed by the hostname (from os.uname()[1]) from which the files originated:
      "YYYY/MM/DD/HH/5min/WebHeadHostName"
      %(root)s/date/2008/09/30/12/05/webhead01/22adfb61-f75b-11dc-b6be-001321b0783d.symlink
      the symbolic link would be: "../../../../../../../../radix/22/ad/fb/61/22adfb61-f75b-11dc-b6be-001321b0783d.json"
  """
  #-----------------------------------------------------------------------------------------------------------------
  def __init__(self, root=".", maxDirectoryEntries=1024, **kwargs):
    """
    """
    super(FileSystemStorage, self).__init__()
    self.root = root
    self.maxDirectoryEntries = maxDirectoryEntries
  #-----------------------------------------------------------------------------------------------------------------
  def newEntry (self, uuid, webheadHostName='webhead01', timestamp=dt.datetime.now()):
    """ this function will setup the radix and date storage directory branches for the given uuid.
    It will create any or all directories that it needs along the path to the appropriate storage location.
    It will create the two relative symbolic links: the date branch link pointing to the json file;
    the radix branch link pointing to the date branch link.  It returns a 2-tuple containing two file handles
    open for writing.  The first file handle will be set for ".../uuid.json", while the second will be for
    ".../uuid.dump"
    """
    return (None, None)
  #-----------------------------------------------------------------------------------------------------------------
  def getJson (uuid):
    """this function will return an absolute pathname for the json file for given uuid.
    If there is no such file, it will raise an IOError exception.
    """
    pass
  #-----------------------------------------------------------------------------------------------------------------
  def getDump (self, uuid):
    """this function will return an absolute pathname for the dump file for given uuid.
    If there is no such file, it will raise an IOError exception.
    """
    pass
  #-----------------------------------------------------------------------------------------------------------------
  def openAndMarkAsSeen (self,uuid):
    """
    Returns two streams: The first is open for reading uuid.json the second open for reading uuid.dump. Also
    removes the links associated with these two files. Raises IOError if either file is missing. NOTE: You should
    call remove(uuid) after reading the data from the files.
    """
    raise IOError("stub")
  
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
    deleting any empty subdirectories left behind.
    """
    pass
  #-----------------------------------------------------------------------------------------------------------------
  def move (self, uuid, newAbsolutePath):
    """ this function moves the json and dump files to newAbsolutePath.  In addition, after a move, it removes
     the symbolic links if they still exist.  Then it backs down the date branch, deleting any empty subdirectories
     left behind. 
    """
    pass
  #-----------------------------------------------------------------------------------------------------------------
  def removeOlderThan (self, timestamp):
    """ this function walks the date branch removing all entries older than the timestamp.  It also reaches across
    and removes the corresponding entries in the radix branch.  Whenever it removes the last item in a date branch
    directory, it removes the directory, too.
    """
    pass
