#! /usr/bin/env python
# encoding: utf-8

"""socorro.lib.monitor watches a dump directory managed by a collector,
prunes directories, and detects orphaned dumps and json files. Linux only.
Requires gamin and accompanying python bindings."""

import gamin
import os
import select, errno
from datetime import datetime
import config

#
# Adapted from the WAF project (BSD License)
# http://code.google.com/p/waf/
#
class GaminHelper:
  def __init__(self, eventHandler):
    """@param eventHandler: callback method for event handling"""
    self.__gamin = gamin.WatchMonitor()
    self.__eventHandler = eventHandler # callBack function
    self.__watchHandler = {} # {name : famId}

  def __del__(self):
    """clean remove"""
    if self.__gamin:
      for handle in self.__watchHandler.keys():
        self.stop_watch(handle)
      self.__gamin.disconnect()
      self.__gamin = None

  def __check_gamin(self):
    """is gamin connected"""
    if self.__gamin == None:
      raise "gamin not init"

  def __code2str(self, event):
    """convert event numbers to string"""
    gaminCodes = {
      1:"changed",
      2:"deleted",
      3:"StartExecuting",
      4:"StopExecuting",
      5:"created",
      6:"moved",
      7:"acknowledge",
      8:"exists",
      9:"endExist"
    }
    try:
      return gaminCodes[event]
    except:
      return "unknown"
    
  def __eventhandler_helper(self, pathName, event, userData):
    """local eventhandler helps to convert event numbers to string"""
    self.__eventHandler(pathName, self.__code2str(event), userData)

  def watching(self, name):
    print self.__watchHandler.keys()
    return self.__watchHandler.has_key(name)

  def watch_directory(self, name, userData):
    self.__check_gamin()
    if self.__watchHandler.has_key(name):
      raise "dir allready watched"
    # set gaminId
    self.__watchHandler[name] = self.__gamin.watch_directory(name, self.__eventhandler_helper, userData)
    return(self.__watchHandler[name])

  def watch_file(self, name, userData):
    self.__check_gamin()
    if self.__watchHandler.has_key( name ):
      raise "file allready watched"
    # set famId
    self.__watchHandler[name] = self.__gamin.watch_directory( name, self.__eventhandler_helper, userData)
    return(self.__watchHandler[name])

  def stop_watch(self, name):
    self.__check_gamin()
    if self.__watchHandler.has_key(name):
      self.__gamin.stop_watch(name)
      del self.__watchHandler[name]
    return None

  def wait_for_event(self):
    self.__check_gamin()
    try:
      select.select([self.__gamin.get_fd()], [], [])
    except select.error, er:
      errnumber, strerr = er
      if errnumber != errno.EINTR:
        raise strerr

  def event_pending( self ):
    self.__check_gamin()
    return self.__gamin.event_pending()

  def handle_events( self ):
    self.__check_gamin()
    self.__gamin.handle_events()

  def request_end_loop(self):
    self.__isLooping = False

  def loop(self):
    try:
      self.__isLooping = True
      while (self.__isLooping) and (self.__gamin):
        self.wait_for_event()
        while self.event_pending():
          self.handle_events()
          if not self.__isLooping:
            break
    except KeyboardInterrupt:
      self.request_end_loop()

def shouldDeleteDir(path):
  # check to see if it's empty
  if not len(os.listdir(path)) == 0:
    return False

  # don't delete the storage root
  if os.path.samefile(path, config.storageRoot):
    return False

  if not os.path.isdir(path):
    raise "shouldDeleteDir called on a file"

  if not path.startswith(config.storageRoot):
    raise "shouldDeleteDir called on file outside storage root"

  basename = os.path.basename(path)
  isDumpDir = basename.startswith(config.dumpDirPrefix)
  mtime = datetime.utcfromtimestamp(os.path.getmtime(path))
  now = datetime.utcnow()
  delta = now - mtime
  
  # a dump directory that's empty and more than 2 hours old
  if isDumpDir and delta > config.dumpDirDelta:
    return True
  
  # a date directory that's empty and more than a day old
  if not isDumpDir and delta > config.dateDirDelta:
    return True
    
  return False

def stopWatchingAndDelete(path):
  if gGamin.watching(path):
    gGamin.stop_watch(path)
  # we race with other machines, so delete can fail
  try:
    os.rmdir(path)
  except OSError, e:
    if e.errno != 2:
      raise e
    
def pruneStorageRoot(toppath):
  """Check for empty directories"""
  for root, dirs, files in os.walk(toppath, topdown=False):
    for name in dirs:
      fullpath = os.path.join(root, name)
      if shouldDeleteDir(fullpath):
        stopWatchingAndDelete(fullpath)
    #XXX check for orphaned dump files
    return
  
rootPathLength = len(config.storageRoot.split(os.sep))
def gaminCallback(filename, eventName, userData):
  fullpath = filename
  if filename != userData:
    fullpath = os.path.join(userData, filename)
  depth = len(fullpath.split(os.sep)) - rootPathLength

  # make sure we don't monitor too deep or monitor the root again
  if depth > 6 or depth < 0:
    return

  # we can stop watching and delete old, empty stuff
  isDir = os.path.isdir(fullpath)
  if isDir and shouldDeleteDir(fullpath):
    stopWatchingAndDelete(fullpath)
    
  # if it's a directory we aren't watching, add it to our dict
  if eventName in ["exists","created"]:
    if isDir and not gGamin.watching(fullpath):
      gGamin.watch_directory(fullpath, fullpath)
      # try pruning the parent
      pruneStorageRoot(userData)
    elif not isDir:
      # The collector should create the json file containing form
      # fields after creating the dump file. So we ignore files ending
      # with config.dumpSuffix until their companion JSON file is
      # present. pruneStorageRoot will manage orphaned files.
      #
      pass
  elif eventName is "deleted" and gGamin.watching(fullpath):
    gGamin.stop_watch(fullpath)

  print "fam event: %s name: %s" % (userData,eventName)

gGamin = GaminHelper(gaminCallback)

def main():
  gGamin.watch_directory(config.storageRoot, config.storageRoot)
  gGamin.loop()
  print "hi"

if __name__ == "__main__":
  main()
