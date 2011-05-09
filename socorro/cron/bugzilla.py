#!/usr/bin/python

import urllib2
import logging
import datetime as dt
import cPickle
import csv
import time

logger = logging.getLogger("bugzilla")

import socorro.lib.psycopghelper as psy
import socorro.lib.util as util

#-----------------------------------------------------------------------------------------------------------------
def find_signatures(bugReportDict):
  try:
    candidateString = bugReportDict['short_desc']
    bracketNestingCounter = 0 #limit 1
    firstLevelBracketPositions = []
    for i, ch in enumerate(candidateString):
      if ch == '[':
        if bracketNestingCounter == 0:
          firstLevelBracketPositions.append(i+2) #choose position 2 beyond
        bracketNestingCounter += 1
      elif ch == ']':
        if bracketNestingCounter == 1:
          firstLevelBracketPositions.append(i)
        if bracketNestingCounter: bracketNestingCounter -= 1
    listOfSignatures = []
    try:
      for beginSignaturePosition, endSignaturePosition in ((firstLevelBracketPositions[x],firstLevelBracketPositions[x+1]) for x in range(0,len(firstLevelBracketPositions),2)):
        if candidateString[beginSignaturePosition-1] == '@':
          listOfSignatures.append(candidateString[beginSignaturePosition:endSignaturePosition].strip())
    except IndexError:
      pass
    setOfSignatures = set(listOfSignatures)
    return (int(bugReportDict["bug_id"]), bugReportDict["bug_status"], bugReportDict["resolution"], bugReportDict["short_desc"], setOfSignatures)
  except (KeyError, TypeError, ValueError):
    return None

#-----------------------------------------------------------------------------------------------------------------
def bug_id_to_signature_association_iterator(query, querySourceFunction=urllib2.urlopen):
  logger.debug("query: %s", query)
  for x in csv.DictReader(querySourceFunction(query)):
    logger.debug("reading csv: %s", str(x))
    yield find_signatures(x)

#-----------------------------------------------------------------------------------------------------------------
def signature_is_found(signature, databaseCursor):
  try:
    psy.singleValueSql(databaseCursor, "select id from reports where signature = %s limit 1", (signature,))
    return True
  except psy.SQLDidNotReturnSingleValue:
    return False

#-----------------------------------------------------------------------------------------------------------------
def insert_or_update_bug_in_database(bugId, statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla, signatureSetFromBugzilla,
                                     databaseCursor, signatureFoundInReportsFunction=signature_is_found):
  try:
    if len(signatureSetFromBugzilla) == 0:
      databaseCursor.execute("delete from bugs where id = %s", (bugId,))
      databaseCursor.connection.commit()
      logger.info("rejecting bug (no signatures): %s - %s, %s", bugId, statusFromBugzilla, resolutionFromBugzilla)
    else:
      useful = False
      insertMade = False
      try:
        statusFromDatabase, resolutionFromDatabase, shortDescFromDatabase = psy.singleRowSql(databaseCursor, "select status, resolution, short_desc from bugs where id = %s", (bugId,))
        if statusFromDatabase != statusFromBugzilla or resolutionFromDatabase != resolutionFromBugzilla or shortDescFromDatabase != shortDescFromBugzilla:
          databaseCursor.execute("update bugs set status = %s, resolution = %s, short_desc = %s where id = %s", (statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla, bugId))
          logger.info("bug status updated: %s - %s, %s", bugId, statusFromBugzilla, resolutionFromBugzilla)
          useful = True
        listOfSignaturesFromDatabase = [x[0] for x in psy.execute(databaseCursor, "select signature from bug_associations where bug_id = %s", (bugId,))]
        for aSignature in listOfSignaturesFromDatabase:
          if aSignature not in signatureSetFromBugzilla:
            databaseCursor.execute("delete from bug_associations where signature = %s and bug_id = %s", (aSignature, bugId))
            logger.info ('association removed: %s - "%s"', bugId, aSignature)
            useful = True
      except psy.SQLDidNotReturnSingleRow:
        databaseCursor.execute("insert into bugs (id, status, resolution, short_desc) values (%s, %s, %s, %s)", (bugId, statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla))
        insertMade = True
        listOfSignaturesFromDatabase = []
      for aSignature in signatureSetFromBugzilla:
        if aSignature not in listOfSignaturesFromDatabase:
          if signatureFoundInReportsFunction(aSignature, databaseCursor):
            databaseCursor.execute("insert into bug_associations (signature, bug_id) values (%s, %s)", (aSignature, bugId))
            logger.info ('new association: %s - "%s"', bugId, aSignature)
            useful = True
          else:
            logger.info ('rejecting association (no reports with this signature): %s - "%s"', bugId, aSignature)
      if useful:
        databaseCursor.connection.commit()
        if insertMade:
          logger.info('new bug: %s - %s, %s, "%s"', bugId, statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla)
      else:
        databaseCursor.connection.rollback()
        if insertMade:
          logger.info('rejecting bug (no useful information): %s - %s, %s, "%s"', bugId, statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla)
        else:
          logger.info('skipping bug (no new information): %s - %s, %s, "%s"', bugId, statusFromBugzilla, resolutionFromBugzilla, shortDescFromBugzilla)
  except Exception, x:
    databaseCursor.connection.rollback()
    raise

#-----------------------------------------------------------------------------------------------------------------
def get_last_run_date(config, now_function=dt.datetime.now):
  if config.daysIntoPast == 0:
    try:
      f = open(config.persistentDataPathname)
      try:
        return cPickle.load(f)
      finally:
        f.close()
    except IOError:
      return now_function() - dt.timedelta(days=30)
  else:
    return now_function() - dt.timedelta(days=config.daysIntoPast)

#-----------------------------------------------------------------------------------------------------------------
def save_last_run_date(config, now_function=dt.datetime.now):
  try:
    f = open(config.persistentDataPathname, "w")
    try:
      return cPickle.dump(now_function(), f)
    finally:
      f.close()
  except IOError:
    reportExceptionAndContinue(logger)

#-----------------------------------------------------------------------------------------------------------------
def record_associations(config):
  databaseConnectionPool = psy.DatabaseConnectionPool(config.databaseHost, config.databaseName, config.databaseUserName, config.databasePassword, logger)
  try:
    databaseConnection, databaseCursor = databaseConnectionPool.connectionCursorPair()
    lastRunDate = get_last_run_date(config)
    lastRunDateAsString = lastRunDate.strftime('%Y-%m-%d')
    logger.info("beginning search from this date (YYYY-MM-DD): %s", lastRunDateAsString)
    query = config.bugzillaQuery % lastRunDateAsString
    logger.info("searching using: %s", query)
    for bug, status, resolution, short_desc, signatureSet in bug_id_to_signature_association_iterator(query):
      logger.debug("bug %s (%s, %s) %s: %s", bug, status, resolution, short_desc, str(signatureSet))
      insert_or_update_bug_in_database (bug, status, resolution, short_desc, signatureSet, databaseCursor)
    save_last_run_date(config)
  finally:
    databaseConnectionPool.cleanup()

