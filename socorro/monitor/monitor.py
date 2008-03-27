#! /usr/bin/env python

import psycopg2

import time
import datetime
import os
import os.path

import socorro.lib.config as config
import socorro.lib.util

def directoryJudgedDeletable (pathname, subDirectoryList, fileList):
  if not (subDirectoryList or fileList) and pathname != config.storageRoot: #if both directoryList and fileList are empty
    #select an ageLimit from two options based on the if target directory name has a prefix of "dumpDirPrefix"
    ageLimit = (config.dateDirDelta, config.dumpDirDelta)[os.path.basename(pathname).startswith(config.dumpDirPrefix)]
    return (datetime.datetime.utcnow() - datetime.datetime.utcfromtimestamp(os.path.getmtime(pathname))) > ageLimit
  return False

def ignoreDuplicateDatabaseInsert (exceptionType, exception, tracebackInfo):
  return exceptionType is psycopg2.IntegrityError

def archiveCompletedJobFiles (jsonPathname, uuid, newFileExtension):
  print "archiving %s" % jsonPathname
  newJsonPathname = ("%s/%s%s.%s" % (config.saveMinidumpsTo, uuid, config.jsonFileSuffix, newFileExtension)).replace('//','/')
  print "to %s" % newJsonPathname
  try:
    os.rename(jsonPathname, newJsonPathname)
  except:
    socorro.lib.util.reportExceptionAndContinue()
    
  if config.debug:
    try:
      f = open(jsonPathname)
      f.close()
      print >>config.errorReportStream, "WARNING - %s was not properly moved" % jsonPathname
    except:
      print >>config.statusReportStream, "INFO - %s properly moved" % jsonPathname
      
  try:
    dumpPathname = "%s%s" % (jsonPathname[:-len(config.jsonFileSuffix)], config.dumpFileSuffix)
    os.rename(dumpPathname, ("%s/%s%s.%s" % (config.saveMinidumpsTo, uuid, config.dumpFileSuffix, newFileExtension)).replace('//','/'))
  except:
    socorro.lib.util.reportExceptionAndContinue()

def deleteCompletedJobFiles (jsonPathname, unused1, unused2):
  print "deleting %s" % jsonPathname
  try:
    os.remove(jsonPathname)
  except:
    socorro.lib.util.reportExceptionAndContinue() 
  try:
    dumpPathname = "%s%s" % (jsonPathname[:-len(config.jsonFileSuffix)], config.dumpFileSuffix)
    os.remove(dumpPathname)
  except:
    socorro.lib.util.reportExceptionAndContinue()

def startMonitor():
  print >>config.statusReportStream, "INFO -- connecting to the database"
  try:
    databaseConnection = psycopg2.connect(config.processorDatabaseDSN)
    aCursor = databaseConnection.cursor()
  except:
    socorro.lib.util.reportExceptionAndAbort() # can't continue without a database connection
    
  print >>config.statusReportStream, "INFO -- dealing with completed and failed jobs"
  # check the jobs table to and deal with the completed and failed jobs
  try:
    aCursor.execute("select pathname, uuid from jobs where success is False")
    fileDisposalFunction = (deleteCompletedJobFiles, archiveCompletedJobFiles)[config.saveFailedMinidumps]
    for jsonPathname, uuid in aCursor.fetchall():
      fileDisposalFunction(jsonPathname, uuid, "failed")
    fileDisposalFunction = (deleteCompletedJobFiles, archiveCompletedJobFiles)[config.saveProcessedMinidumps]
    aCursor.execute("select pathname, uuid from jobs where success is True")
    for jsonPathname, uuid in aCursor.fetchall():
      fileDisposalFunction(jsonPathname, uuid, "processed")
    aCursor.execute("delete from jobs where success is not null")
    databaseConnection.commit()
  except:
    databaseConnection.rollback()
    socorro.lib.util.reportExceptionAndContinue()  
    
  # look for dead processors
  #  delete the processor from the processors table and, via cascade, delete its associated jobs
  #  the abandoned jobs will be picked up again by walking the dump tree and assigned to other processors
  print >>config.statusReportStream, "INFO -- looking for dead processors"
  try:
    aCursor.execute("delete from processors where lastSeenDateTime < (now() - interval '%s')" % config.processorCheckInTime)
    databaseConnection.commit()
  except:
    socorro.lib.util.reportExceptionAndContinue()

  # create a list of active processors along with the number of jobs asigned to each
  # then create a generator that will return the id of the processor with the fewest assigned jobs
  # this ensures that all processors have roughly an equal number of pending jobs
  print >>config.statusReportStream, "INFO -- compiling list of active processors"
  try:
    aCursor.execute("""select p.id, count(j.*) from processors p left join jobs j on p.id = j.owner group by p.id""")
    listOfProcessorIds = [[aRow[0], aRow[1]] for aRow in aCursor.fetchall()]
    if not listOfProcessorIds:
      raise Exception("There are no processors registered")
    def processorIdCycle():
      while True:
        listOfProcessorIds.sort(lambda x, y: cmp(x[1], y[1]))
        yield listOfProcessorIds[0][0]
  except:
    socorro.lib.util.reportExceptionAndAbort() # can't continue
  
  # walk the dump tree and assign jobs
  print >>config.statusReportStream, "INFO -- beginning directory tree walk"
  try:
    processorIdSequenceGenerator = processorIdCycle()
    for currentDirectory, directoryList, fileList in os.walk(config.storageRoot, topdown=False):
      print >>config.statusReportStream, "INFO --   %s" % currentDirectory
      try:
        if directoryJudgedDeletable(currentDirectory, directoryList, fileList):
          print >>config.statusReportStream, "%s: Removing - %s" % (datetime.datetime.now(),  currentDirectory)
          os.rmdir(currentDirectory)
        #else:
          #print >>config.statusReportStream, "%s: not deletable - %s" % (datetime.datetime.now(),  currentDirectory)
      except Exception:
        socorro.lib.util.reportExceptionAndContinue()
      for aFileName in fileList:
        print >>config.statusReportStream, "INFO --     %s" % aFileName
        if aFileName.endswith(config.jsonFileSuffix):
          try:
            jsonFilePathName = os.path.join(currentDirectory, aFileName)
            uuid = aFileName[:-5]
            processorIdAssignedToThisJob = processorIdSequenceGenerator.next()
            aCursor.execute("insert into jobs (pathname, uuid, owner, queuedDateTime) values (%s, %s, %s, %s)", 
                                       (jsonFilePathName, uuid, processorIdAssignedToThisJob, datetime.datetime.now()))
            listOfProcessorIds[0][1] += 1  #increment the job count for this processor so that the generator can track which processors need jobs 
            databaseConnection.commit()
          except:
            databaseConnection.rollback()
            socorro.lib.util.reportExceptionAndContinue(ignoreDuplicateDatabaseInsert)
  except:
    socorro.lib.util.reportExceptionAndContinue()
  
if __name__ == '__main__':       
  startMonitor()
  print >>config.statusReportStream, "INFO -- Done."  

