#! /usr/bin/env python
# encoding: utf-8

"""socorro.lib.monitor watches a dump directory managed by a collector,
prunes directories, and detects orphaned dumps and json files. Linux only.
Requires gamin and accompanying python bindings."""

import sys
import gamin
import os
import select, errno
import time
from datetime import datetime
from  sqlalchemy.exceptions import SQLError
import sqlalchemy
import Queue
# signal must be available for this to work right
import signal
import threading
import traceback

if __name__ == '__main__':
  thisdir = os.path.dirname(__file__)
  sys.path.append(os.path.join(thisdir, '..', '..'))

from socorro.lib.processor import Processor
import socorro.lib.config as config
import socorro.models as model

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
    except IndexError:
      return "unknown"
    
  def __eventhandler_helper(self, pathName, event, userData):
    """local eventhandler helps to convert event numbers to string"""
    self.__eventHandler(pathName, self.__code2str(event), userData)

  def watching(self, name):
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

  def is_looping(self):
    return self.__isLooping

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
  # Don't do anything if the event loop has been stopped
  # We'll process these when we start back up
  if not gGamin.is_looping():
    return
  try:
    lookForFiles(filename, eventName, userData)
  except (KeyboardInterrupt, SystemExit):
    gGamin.request_end_loop()
    
def lookForFiles(filename, eventName, userData):
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
  if eventName in ["exists","created"] and isDir:
     if not gGamin.watching(fullpath):
      gGamin.watch_directory(fullpath, fullpath)
      # try pruning the parent
      pruneStorageRoot(userData)
  elif eventName == "deleted" and gGamin.watching(fullpath):
    gGamin.stop_watch(fullpath)
  elif (eventName in ["exists","changed"] and
        filename.endswith(config.jsonFileSuffix)):
    print "%s | queueing %s" % (time.ctime(time.time()), filename)
    gDumpQueue.put_nowait((fullpath, userData, filename))
    print "%s | queue size %d" % (time.ctime(time.time()), gDumpQueue.qsize())

def processDump((fullpath, dir, basename)):
  # If there is more than one processor, they will race to process dumps
  # To prevent this from occuring, the processor will first attempt
  # to insert a record with only the ID.
  dumpID = basename[:basename.find(config.jsonFileSuffix)]
  report = None
  didProcess = False

  report = getReport(dumpID)
  if report is not None:
    try:
      try:
        session = sqlalchemy.object_session(report)
        session.clear()
        didProcess = runProcessor(dir, dumpID, report.id)
      except:
        print "encountered exception... " + dumpID
        # need to clear the db because we didn't process it
        print "Backout changes to uuid " + dumpID
        r = model.Report.get_by(uuid=dumpID)
        r.refresh()
        r.delete()
        r.flush()
        raise
    finally:
      dumppath = os.path.join(dir, dumpID + config.dumpFileSuffix)

      if didProcess:
        print "%s | Did process %s" % (time.ctime(time.time()), dumpID)
        save = config.saveProcessedMinidumps
        saveSuffix = ".processed"
      else:
        print "%s | Failed to process %s" % (time.ctime(time.time()), dumpID)
        save = config.saveFailedMinidumps
        saveSuffix = ".failed"
      
      if save:
        os.rename(fullpath,
                  os.path.join(config.saveMinidumpsTo,
                               dumpID + config.jsonFileSuffix + saveSuffix))
        os.rename(dumppath,
                  os.path.join(config.saveMinidumpsTo,
                               dumpID + config.dumpFileSuffix + saveSuffix))
      else:
        os.remove(fullpath)
        os.remove(dumppath)

def runProcessor(dir, dumpID, pk):
  sys.stdout.flush()
  print "runProcessor for " + dumpID
  report = model.Report.get_by(id=pk, uuid=dumpID)
  session = sqlalchemy.object_session(report) 
  trans = session.create_transaction()
  success = False
  try:
    processor = Processor(config.processorMinidump,
                          config.processorSymbols)
    processor.process(dir, dumpID, report)
    success = True
  except (KeyboardInterrupt, SystemExit):
    trans.rollback()
    raise
  except Exception, e:
    # XXX We should add the exception to the dump, but I can't figure out how
    print "Error in processor: %s" % e

  trans.commit()
  session.clear()
  return success

def getReport(dumpID):
  r = model.Report()
  try:
    r.uuid = dumpID
    r.flush()
  except SQLError, e:
    print "beat to the punch for uuid " + dumpID
    # This is ok, someone beat us to it
    return None
  return r

gDumpQueue = Queue.Queue(0)
def dumpWorker(): 
  while True:
    try:
      # block for 5 minutes if no dump
      item = gDumpQueue.get(True, 300)
      processDump(item)
    except Queue.Empty:
      print "Worker thread waited 5 minutes with no dump."
      sys.stdout.flush()
    except:
      print "Error in worker thread:", sys.exc_info()[0]
      print sys.exc_info()[1]
      traceback.print_tb(sys.exc_info()[2])
      sys.stdout.flush()
        
gGamin = GaminHelper(gaminCallback)
def start():
  print "starting Socorro dump file monitor."

  # ensure that we have a database
  c = model.localEngine.contextual_connect()
  print "Connected to database."
  c = None

  print "Starting background threads."
  for i in range(config.backgroundTaskCount):
    t = threading.Thread(target=dumpWorker)
    t.setDaemon(True)
    t.start()

  gGamin.watch_directory(config.storageRoot, config.storageRoot)
  gGamin.loop()
  
  print "Stopping Socorro dump file monitor."

if __name__ == '__main__':
  start()
