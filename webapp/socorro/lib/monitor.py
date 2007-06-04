#! /usr/bin/env python
# encoding: utf-8

"""socorro.lib.monitor watches a dump directory managed by a collector,
prunes directories, and detects orphaned dumps and json files. Linux only.
Requires gamin and accompanying python bindings."""

import sys
import os
import time
from datetime import datetime
from  sqlalchemy.exceptions import SQLError
import sqlalchemy
import traceback
import errno

if __name__ == '__main__':
  thisdir = os.path.dirname(__file__)
  sys.path.append(os.path.join(thisdir, '..', '..'))

def print_exception():
  print "Caught Error (ignoring):", sys.exc_info()[0]
  print sys.exc_info()[1]
  traceback.print_tb(sys.exc_info()[2])
  sys.stdout.flush()

from socorro.lib.processor import Processor
import socorro.lib.config as config
import socorro.models as model

def deleteIfAppropriate(path):
  # don't delete the storage root
  if os.path.samefile(path, config.storageRoot):
    return

  basename = os.path.basename(path)
  isDumpDir = basename.startswith(config.dumpDirPrefix)
  mtime = datetime.utcfromtimestamp(os.path.getmtime(path))
  now = datetime.utcnow()
  delta = now - mtime
  
  try:
    # a dump directory that's empty and more than 2 hours old
    if isDumpDir and delta > config.dumpDirDelta:
      print "Cleaning up directory %s" % path
      os.rmdir(path)
      # a date directory that's empty and more than a day old
    elif not isDumpDir and delta > config.dateDirDelta:
      print "Cleaning up directory %s" % path
      os.rmdir(path)
  except OSError, e:
    if e.errno not in (errno.ENOENT,
                       errno.ENOTEMPTY):
      print_exception()
  except (KeyboardInterrupt, SystemExit):
    raise
  except:
    print_exception()

def processDump(fullpath, dir, basename):
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

def TimedForever():
  last_time = 0
  while True:
    t = time.time()
    sleep_time = last_time - t + config.processorLoopTime
    if sleep_time > 0:
      print "Sleeping for %f seconds." % sleep_time
      sys.stdout.flush()
      time.sleep(sleep_time)
    last_time = time.time()
    yield 1

rootPathLength = len(config.storageRoot.split(os.sep))

def start():
  print "starting Socorro dump file monitor."

  # ensure that we have a database
  c = model.localEngine.contextual_connect()
  print "Connected to database."
  c = None

  try:
    for i in TimedForever():
      try:
        for (root, dirs, files) in os.walk(config.storageRoot, topdown=False):
          if rootPathLength + 6 > root.split(os.sep):
            del dirs[0:]

          if len(files) == 0 and len(dirs) == 0:
            deleteIfAppropriate(root)

          for file in files:
            if file.endswith(config.jsonFileSuffix):
              path = os.path.join(root, file)
              processDump(path, root, file)
        
      except (KeyboardInterrupt, SystemExit):
        raise
      except:
        print_exception()
  except (KeyboardInterrupt, SystemExit):
    print "Stopping Socorro dump file monitor."
    sys.exit(0)
  
if __name__ == '__main__':
  start()
