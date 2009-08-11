""" Shared utilities for the cron scripts """

import socorro.lib.util as lib_util
import socorro.lib.ConfigurationManager as cm
import datetime
import logging
import time

# Used by unittest: You may freely edit these values to better defaults
globalDefaultDeltaWindow = datetime.timedelta(seconds=12*60)
globalInitialDeltaDate = datetime.timedelta(days=4)

def getProcessingDates(configContext, tableName, cursor, logger, **kwargs):
  """
  A processing interval is a time interval greater or equal to a processing window. Used to
  calculate a series of adjacent materialized view aggregates.
  
  Returns (startDate, deltaDate, endDate) using this heuristic:
  kwargs beats configContext
  if none are provided, calculates based on latest row of table, now()
  if only one is provided, logs the insufficiency and aborts
  if two among startDate, deltaDate, endDate: they are used
  Checks the table for most recent window_end
    if startDate < window_end:
      startDate = endWindow
      logger.info(...that change...)
  if startDate >= endDate, or deltaDate <= 0, or three provided are inconsistent:
    logs the inconsistency and aborts
  """
  config = {}
  config.update(configContext)
  config.update(kwargs)
  delta0 = datetime.timedelta(days=0)
  startDate = config.get('startDate')
  if startDate:
    startDate = "%s"%(startDate)
    startDate = cm.dateTimeConverter(startDate)
  deltaDate = config.get('deltaDate')
  if type(deltaDate) is str:
    deltaDate = cm.timeDeltaConverter(deltaDate)
  endDate = config.get('endDate')
  if endDate:
    endDate = "%s"%(endDate)
    endDate = cm.dateTimeConverter(endDate)
  initialDeltaDate = config.get('initialDeltaDate',config.get('deltaDate'))
  if not initialDeltaDate: initialDeltaDate = globalInitialDeltaDate
  defaultDeltaWindow = config.get('defaultDeltaWindow',config.get('deltaWindow'))
  if not defaultDeltaWindow: defaultDeltaWindow = globalDefaultDeltaWindow
  try:
    startDateFromTable,endDateFromTable,latestWindowEnd = getDefaultDateInterval(cursor,tableName,initialDeltaDate,defaultDeltaWindow,logger)
    if startDate and endDate and deltaDate:
      assert startDate + deltaDate == endDate,"inconsistent: %s + %s != %s"%(startDate,deltaDate,endDate)
    elif startDate and endDate:
      assert startDate < endDate, 'inconsistent: startDate %s >= endDate %s'%(startDate,endDate)
      deltaDate = endDate - startDate
    elif startDate and deltaDate:
      assert deltaDate > delta0, 'inconsistent: deltaDate %s <= 0'%(deltaDate)
      endDate = startDate + deltaDate
    elif deltaDate and endDate:
      assert deltaDate > delta0, 'inconsistent: deltaDate %s <= 0'%(deltaDate)
      startDate = endDate - deltaDate
    else:
      assert not (startDate or deltaDate or endDate), "insufficient: Need two xxxDate: start: %s, delta: %s, end:%s"%(startDate,deltaDate,endDate)
      startDate = startDateFromTable
      endDate = endDateFromTable
      deltaDate = endDate - startDate
    if latestWindowEnd and startDate < latestWindowEnd:
      logger.info("given/calculated startDate: %s < latest row in %s. Changing to %s",startDate,tableName,latestWindowEnd)
      startDate = latestWindowEnd
      deltaDate = endDate - startDate
      assert deltaDate > delta0, 'inconsistent (after check with db table %s): deltaDate %s <= 0'%(tableName,deltaDate)
    return (startDate,deltaDate,endDate)
  except:
    lib_util.reportExceptionAndAbort(logger)

def getProcessingWindow(configContext,tableName,cursor,logger, **kwargs):
  """
  ProcessingWindow is a single time window over which to aggregate materialized view data.
  
  Returns (startWindow,deltaWindow,endWindow) using this heuristic:
  kwargs beats configContext which beats latest table row
  if two among startWindow, endWindow, deltaWindow in config or kwargs: they are used.
    if all three: assert startWindow + deltaWindow == endWindow
  Backward compatibility: if processingDay is present and windowXxx are not:
    startWindow = midnight of given day, deltaWindow = timedelta(days=1)
  else: try to read window_end and window_size from the given table
  if one is available from config/kwargs it beats the same (or calculated) one from the table
  On inconsistency or failure, logs the problem and aborts
  BEWARE: You can get inconsitency by having one item in config and the other two in kwargs: BEWARE
  """
  config = {}
  config.update(configContext)
  config.update(kwargs)
  startWindow = config.get('startWindow')
  if type(startWindow) is str:
    startWindow = cm.dateTimeConverter(startWindow)
  deltaWindow = config.get('deltaWindow')
  if type(deltaWindow) is str:
    deltaWindow = cm.timeDeltaConverter(deltaWindow)
  endWindow = config.get('endWindow')
  if type(endWindow) is str:
    endWindow = cm.dateTimeConverter(endWindow)
  processingDay = config.get('processingDay')
  if type(processingDay) is str:
    processingDay = cm.dateTimeConverter(processingDay)
  try:
    if startWindow or deltaWindow or endWindow:
      if startWindow and endWindow and deltaWindow:
        assert startWindow + deltaWindow == endWindow,"inconsistent: %s + %s != %s"%(startWindow,deltaWindow,endWindow)
      elif startWindow and endWindow:
        deltaWindow = endWindow - startWindow
      elif startWindow and deltaWindow:
        endWindow = startWindow + deltaWindow
      elif deltaWindow and endWindow:
        startWindow = endWindow - deltaWindow
      else:
        assert not (startWindow or deltaWindow or endWindow), "insufficient: Need two of window ...Start: %s, ...Delta: %s, ...End:%s"%(startWindow,deltaWindow,endWindow)
    elif processingDay:
      dayt = datetime.datetime.fromtimestamp(time.mktime(processingDay.timetuple()))
      startWindow = dayt.replace(hour=0,minute=0,second=0,microsecond=0)
      assert startWindow == dayt,'processingDay must be some midnight, but was %s'%dayt
      deltaWindow = datetime.timedelta(days=1)
      endWindow = startWindow + deltaWindow
    else: # no params: try table
      startWindow,deltaWindow = getLastWindowAndSizeFromTable(cursor,tableName,logger)
      if startWindow:
        endWindow = startWindow+deltaWindow
    return (startWindow,deltaWindow,endWindow)
  except:
    lib_util.reportExceptionAndAbort(logger)

def getDefaultDateInterval(cursor,tableName,initialDeltaDate,defaultDeltaWindow,logger):
  """
  Calculates startDate, deltaWindow from latest entry in tableName (else initialDeltaDate, defaultDeltaWindow)
  if no such table, logs failure and exits 
  Calculates endDate from now and deltaWindow
  if initialDeltaDate or defaultDeltaWindow is used, logs an info message
  returns (startDate, endDate, latestWindowEnd)
  """
  now = datetime.datetime.now()
  myMidnight = now.replace(hour=0,minute=0,second=0,microsecond=0)
  latestWindowEnd,deltaWindow = getLastWindowAndSizeFromTable(cursor,tableName,logger)
  if latestWindowEnd:
    startDate = latestWindowEnd
  else:
    startDate = myMidnight - initialDeltaDate
    logger.info("Table %s has no latest entry. Using default = %s",tableName,startDate)
  if not deltaWindow:
    deltaWindow = defaultDeltaWindow
    logger.info("Table %s has no window_size entry. Using default = %s",tableName,deltaWindow)
  endDate = myMidnight
  while endDate + deltaWindow < now:
    endDate += deltaWindow
  return (startDate,endDate,latestWindowEnd)
  
def getLastWindowAndSizeFromTable(cursor, table, logger):
  """
  cursor: database cursor
  table: name of table to check
  logger: in case trouble needs to be reported,
  Extracts and returns the most recent (window_end, window_size)
    - If there is no such table (or it has no such columns), logs failure and exits
    - If there is no such row, return (None,None)
  Checks that:
    - window_size is a whole number of minutes and that an integral number of them make a full day
    - window_size is an integral number of days (probably exactly one)
  If window_size is incorrect, logs failure and exits: The database is corrupt.
  """
  lastEnd, lastSize = None,None
  try:
    cursor.execute("SELECT window_end,window_size FROM %s ORDER BY window_end DESC LIMIT 1"%table)
    cursor.connection.rollback()
  except:
    cursor.connection.rollback()
    lib_util.reportExceptionAndAbort(logger)
  try:
    lastEnd, lastSize = None,None
    (lastEnd,lastSize) = cursor.fetchone()
  except TypeError: # Don't log "NoneType object is not iterable"
    return lastEnd,lastSize
  except:
    lib_util.reportExceptionAndContinue(logger)
    return lastEnd,lastSize
  try:
    if 0 == lastSize.days:
      min = lastSize.seconds/60.0
      assert min > 0, 'Negative processing interval is not allowed, but got %s minutes'%min
      assert int(min) == min, 'processingInterval must be whole number of minutes, but got %s'%min
      assert 0 == (24*60)%min, 'Minutes in processing interval must divide evenly into a day, but got %d'%min
    else:
      day = lastSize.days
      assert day > 0, 'Negative processing interval is not allowed, but got %s days'%day
      assert 0 == lastSize.seconds, 'processing interval of days must have no left over seconds, but got %s'%lastSize.seconds
    usec = lastSize.microseconds
    assert 0 == usec, 'processing interval must have no fractional seconds, but got %s usecs'%usec
  except:
    lib_util.reportExceptionAndAbort(logger)
  return (lastEnd,lastSize)
