#! /usr/bin/env python

import psycopg2

import time
import datetime
import os
import os.path
import shutil
import signal

import logging

logger = logging.getLogger("monitor")

import socorro.lib.util

def directoryJudgedDeletable (config, pathname, subDirectoryList, fileList):
  if not (subDirectoryList or fileList) and pathname != config.storageRoot: #if both directoryList and fileList are empty
    #select an ageLimit from two options based on the if target directory name has a prefix of "dumpDirPrefix"
    ageLimit = (config.dateDirDelta, config.dumpDirDelta)[os.path.basename(pathname).startswith(config.dumpDirPrefix)]
    return (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(os.path.getmtime(pathname))) > ageLimit
  return False

def ignoreDuplicateDatabaseInsert (exceptionType, exception, tracebackInfo):
  return exceptionType is psycopg2.IntegrityError

def archiveCompletedJobFiles (config, jsonPathname, uuid, newFileExtension):
  logger.debug("archiving %s", jsonPathname)
  newJsonPathname = ("%s/%s%s.%s" % (config.saveMinidumpsTo, uuid, config.jsonFileSuffix, newFileExtension)).replace('//','/')
  try:
    shutil.move(jsonPathname, newJsonPathname)
  except:
    socorro.lib.util.reportExceptionAndContinue(logger)
  if config.debug:
    try:
      f = open(jsonPathname)
      f.close()
      logger.error("removed failed - %s", jsonPathname)
    except:
      logger.debug("remove succeeded - %s", jsonPathname)
    try:
      f = open(newJsonPathname)
      f.close()
      logger.debug("arrival succeeded - %s", newJsonPathname)
    except:
      logger.error("arrival failed - %s", newJsonPathname)      
      
  try:
    dumpPathname = "%s%s" % (jsonPathname[:-len(config.jsonFileSuffix)], config.dumpFileSuffix)
    newDumpPathname = ("%s/%s%s.%s" % (config.saveMinidumpsTo, uuid, config.dumpFileSuffix, newFileExtension)).replace('//','/')
    logger.debug("archiving %s", dumpPathname)
    shutil.move(dumpPathname, newDumpPathname)
  except:
    socorro.lib.util.reportExceptionAndContinue(logger)
  if config.debug:
    try:
      f = open(dumpPathname)
      f.close()
      logger.error("removed failed - %s", dumpPathname)
    except:
      logger.debug("remove succeeded - %s", dumpPathname)
    try:
      f = open(newDumpPathname)
      f.close()
      logger.debug("arrival succeeded - %s", newDumpPathname)
    except:
      logger.error("arrival failed - %s", newDumpPathname)    
      
def deleteCompletedJobFiles (config, jsonPathname, unused1, unused2):
  logger.debug("deleting %s", jsonPathname)
  try:
    os.remove(jsonPathname)
  except:
    socorro.lib.util.reportExceptionAndContinue(logger) 
  try:
    dumpPathname = "%s%s" % (jsonPathname[:-len(config.jsonFileSuffix)], config.dumpFileSuffix)
    os.remove(dumpPathname)
  except:
    socorro.lib.util.reportExceptionAndContinue(logger)

def respondToSIGTERM(signalNumber, frame):
  """ these classes are instrumented to respond to a KeyboardInterrupt by cleanly shutting down.
      This function, when given as a handler to for a SIGTERM event, will make the program respond
      to a SIGTERM as neatly as it responds to ^C.
  """
  logger.info("SIGTERM detected")
  raise KeyboardInterrupt
  
def startMonitor(config):
  """
  """
  signal.signal(signal.SIGTERM, respondToSIGTERM)

  logger.info("connecting to the database")
  try:
    databaseConnection = psycopg2.connect(config.databaseDSN)
    aCursor = databaseConnection.cursor()
  except:
    socorro.lib.util.reportExceptionAndAbort(logger) # can't continue without a database connection
  
  try:
    loopControl = True
    while (loopControl):
      logger.debug("dealing with completed and failed jobs")
      # check the jobs table to and deal with the completed and failed jobs
      try:
        aCursor.execute("select id, pathname, uuid from jobs where success is False")
        fileDisposalFunction = (deleteCompletedJobFiles, archiveCompletedJobFiles)[config.saveFailedMinidumps]
        for jobId, jsonPathname, uuid in aCursor.fetchall():
          fileDisposalFunction(config, jsonPathname, uuid, "failed")
          aCursor.execute("delete from jobs where id = %s", (jobId,))
        fileDisposalFunction = (deleteCompletedJobFiles, archiveCompletedJobFiles)[config.saveProcessedMinidumps]
        aCursor.execute("select id, pathname, uuid from jobs where success is True")
        for jobId, jsonPathname, uuid in aCursor.fetchall():
          fileDisposalFunction(config, jsonPathname, uuid, "processed")
          aCursor.execute("delete from jobs where id = %s", (jobId,))
        databaseConnection.commit()
      except:
        databaseConnection.rollback()
        socorro.lib.util.reportExceptionAndContinue(logger)  
        
      # look for dead processors
      #  delete the processor from the processors table and, via cascade, delete its associated jobs
      #  the abandoned jobs will be picked up again by walking the dump tree and assigned to other processors
      logger.debug("looking for dead processors")
      try:
        aCursor.execute("delete from processors where lastSeenDateTime < (now() - interval '%s')" % config.processorCheckInTime)
        databaseConnection.commit()
      except:
        socorro.lib.util.reportExceptionAndContinue(logger)
    
      # create a list of active processors along with the number of jobs asigned to each
      # then create a generator that will return the id of the processor with the fewest assigned jobs
      # this ensures that all processors have roughly an equal number of pending jobs
      logger.debug("compiling list of active processors")
      try:
        aCursor.execute("""select p.id, count(j.*) from processors p left join jobs j on p.id = j.owner group by p.id""")
        listOfProcessorIds = [[aRow[0], aRow[1]] for aRow in aCursor.fetchall()]  #processorId, numberOfAssignedJobs
        if not listOfProcessorIds:
          raise Exception("There are no processors registered")
        def processorIdCycle():
          while True:
            # sort the list of (processorId, numberOfAssignedJobs) pairs
            # this works because the list is numberOfAssignedJobs is incremented each
            # time a job is assigned to a processor further down in this code
            listOfProcessorIds.sort(lambda x, y: cmp(x[1], y[1]))
            # yield the processorId with the fewest jobs
            yield listOfProcessorIds[0][0]
      except:
        socorro.lib.util.reportExceptionAndAbort(logger) # can't continue
      
      # walk the dump tree and assign jobs
      logger.debug("beginning directory tree walk")
      try:
        processorIdSequenceGenerator = processorIdCycle()
        for currentDirectory, directoryList, fileList in os.walk(config.storageRoot, topdown=False):
          logger.debug("   %s", currentDirectory)
          try:
            if directoryJudgedDeletable(config, currentDirectory, directoryList, fileList):
              logger.debug("     removing - %s",  currentDirectory)
              os.rmdir(currentDirectory)
            else:
              logger.debug("     not eligible for deletion - %s",  currentDirectory)
          except Exception:
            socorro.lib.util.reportExceptionAndContinue(logger)
          for aFileName in fileList:
            logger.debug("   %s", aFileName)
            if aFileName.endswith(config.jsonFileSuffix):
              try:
                jsonFilePathName = os.path.join(currentDirectory, aFileName)
                uuid = aFileName[:-5]
                logger.debug("    trying to insert %s", uuid)
                processorIdAssignedToThisJob = processorIdSequenceGenerator.next()
                aCursor.execute("insert into jobs (pathname, uuid, owner, queuedDateTime) values (%s, %s, %s, %s)", 
                                           (jsonFilePathName, uuid, processorIdAssignedToThisJob, datetime.datetime.now()))
                listOfProcessorIds[0][1] += 1  #increment the job count for this processor so that the generator can track which processors need jobs 
                databaseConnection.commit()
                logger.debug("    assigned to processor %d", processorIdAssignedToThisJob)
              except:
                databaseConnection.rollback()
                socorro.lib.util.reportExceptionAndContinue(logger, logging.ERROR, ignoreDuplicateDatabaseInsert)
      except:
        socorro.lib.util.reportExceptionAndContinue(logger)
      loopControl = config.loop
  finally:
    databaseConnection.close()
    

