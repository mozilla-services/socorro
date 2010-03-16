""" Shared utilities for the cron scripts """

import socorro.lib.util as lib_util
import socorro.lib.ConfigurationManager as cm
import socorro.lib.psycopghelper as psy
import datetime
import logging
import time

# Used by unittest: You may freely edit these values to better defaults
globalDefaultDeltaWindow = datetime.timedelta(seconds=12*60)
globalInitialDeltaDate = datetime.timedelta(days=4)
globalDefaultProcessingDelay = datetime.timedelta(hours=2)

def getProcessingDates(configContext, tableName, productVersionRestriction, cursor, logger, **kwargs):
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
      startDate = window_end
      logger.info(...that change...)
  if startDate >= endDate, or deltaDate <= 0, or three provided are inconsistent:
    logs the inconsistency and aborts
  """
  config = {}
  config.update(configContext)
  config.update(kwargs)
  delta0 = datetime.timedelta(days=0)
  delay = config.get('processingDelay', datetime.timedelta(hours=2))
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
    try:
      logger.debug('trying getDefaultDateInterval')
      startDateFromTable,endDateFromTable,latestWindowEnd = getDefaultDateInterval(cursor,tableName,delay,initialDeltaDate,defaultDeltaWindow,productVersionRestriction,logger)
    except Exception, x:
      print x
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

def getProcessingWindow(configContext,tableName, productVersionRestriction,cursor,logger, **kwargs):
  """
  ProcessingWindow is a single time window over which to aggregate materialized view data.

  Returns (startWindow,deltaWindow,endWindow) using this heuristic:
  kwargs beats configContext which beats latest table row
  if only one is present, try to get the others from the table
  if two among startWindow, endWindow, deltaWindow in config or kwargs: they are used.
    if all three: assert startWindow + deltaWindow == endWindow
  Backward compatibility: if processingDay is present and windowXxx are not:
    startWindow = midnight of given day, deltaWindow = timedelta(days=1)
  else: try to read window_end and window_size from the given table
  On inconsistency or failure, logs the problem and aborts
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
    tStartWindow,tDeltaWindow = None,None
    if startWindow and endWindow and deltaWindow:
      assert startWindow + deltaWindow == endWindow,"inconsistent: %s + %s != %s"%(startWindow,deltaWindow,endWindow)
    elif startWindow and endWindow:
      deltaWindow = endWindow - startWindow
    elif startWindow and deltaWindow:
      endWindow = startWindow + deltaWindow
    elif deltaWindow and endWindow:
      startWindow = endWindow - deltaWindow
    elif processingDay:
      dayt = datetime.datetime.fromtimestamp(time.mktime(processingDay.timetuple()))
      startWindow = dayt.replace(hour=0,minute=0,second=0,microsecond=0)
      assert startWindow == dayt,'processingDay must be some midnight, but was %s'%dayt
      deltaWindow = datetime.timedelta(days=1)
      endWindow = startWindow + deltaWindow
    else: # not enough params: try table
      tStartWindow,tDeltaWindow = getLastWindowAndSizeFromTable(cursor,tableName, productVersionRestriction,logger)
      if startWindow and tDeltaWindow:
        deltaWindow = tDeltaWindow
        endWindow = startWindow+deltaWindow
      elif endWindow and tDeltaWindow:
        deltaWindow = tDeltaWindow
        startWindow = endWindow - deltaWindow
      elif deltaWindow and tStartWindow:
        startWindow = tStartWindow
        endWindow = startWindow + deltaWindow
      elif tStartWindow and tDeltaWindow:
        startWindow = tStartWindow
        deltaWindow = tDeltaWindow
        endWindow = startWindow + deltaWindow
    assert (startWindow and deltaWindow and endWindow) or not (startWindow or deltaWindow or endWindow)
    return (startWindow,deltaWindow,endWindow)
  except:
    lib_util.reportExceptionAndAbort(logger)

def getProcessingWindowFromArgs(config,tStartWindow,tDeltaWindow,logger):
  """
  ProcessingWindow is a single time window over which to aggregate materialized view data.

  parameters:
  config: A map that already has appropriate types (or None) for the needed keys
  tStarWindow, tDeltaWindow: used as if latest appropriate window_end, window_size from the materialized view table

  Returns (startWindow,deltaWindow,endWindow) using this heuristic:
  if no config values for Window:
    if startDate:
      startWindow = startDate
      deltaWindow = globalDefaultDeltaWindow
      endWindow = startWindow+deltaWindow
    else:
      fail
  if only one value in config:
    try to use what is needed from tStartWindow or tDeltaWindow
  if two among startWindow, endWindow, deltaWindow in config:
    assert start < end or delta > 0, then generate the other
  if all three:
    assert startWindow + deltaWindow == endWindow and delta > 0
  Backward compatibility: if processingDay is present in config and windowXxx are not:
    startWindow = midnight of given day, deltaWindow = timedelta(days=1)
  after all calculations, if startWindow < tStartWindow (i.e.: Table value is more recent):
    a warning is logged, startWindow is set to tStartWindow and endWindow is recalculated
  On inconsistency or failure, logs the problem and aborts
  """
  startWindow = config.get('startWindow')
  deltaWindow = config.get('deltaWindow')
  if deltaWindow:
    assert deltaWindow > datetime.timedelta(0), 'configured deltaWindow [%s] not > 0'%deltaWindow
  endWindow = config.get('endWindow')
  processingDay = config.get('processingDay')
  if type(processingDay) is str:
    processingDay = cm.dateTimeConverter(processingDay)
  try:
    if startWindow and endWindow and deltaWindow:
      assert startWindow + deltaWindow == endWindow,"inconsistent: %s + %s != %s"%(startWindow,deltaWindow,endWindow)
    elif startWindow and endWindow:
      assert startWindow < endWindow, "inconsistent: startWindow [%s] !< endWindow [%s]"%(startWindow, endWindow)
      deltaWindow = endWindow - startWindow
    elif startWindow and deltaWindow:
      endWindow = startWindow + deltaWindow
    elif deltaWindow and endWindow:
      startWindow = endWindow - deltaWindow
    else: # one or zero params: try the alternate parameter values
      if startWindow:
        if tDeltaWindow:
          deltaWindow = tDeltaWindow
        else:
          deltaWindow = globalDefaultDeltaWindow
          logger.warn("Using global default deltaWindow = %s",deltaWindow)
        endWindow = startWindow+deltaWindow
      elif endWindow:
        if tDeltaWindow:
          deltaWindow = tDeltaWindow
        else:
          deltaWindow = globalDefaultDeltaWindow
          logger.warn("Using global default deltaWindow = %s",deltaWindow)
        startWindow = endWindow - deltaWindow
      elif deltaWindow:
        if tStartWindow:
          startWindow = tStartWindow
          endWindow = startWindow + deltaWindow
      elif not processingDay and tStartWindow and tDeltaWindow:
        startWindow = tStartWindow
        deltaWindow = tDeltaWindow
        endWindow = startWindow + deltaWindow
      elif processingDay:
        logger.warn("Discarding start-,delta-,end-Window config values (%s,%s,%s) in favor of processingDay [%s]",startWindow,deltaWindow,endWindow,processingDay)
        dayt = datetime.datetime.fromtimestamp(time.mktime(processingDay.timetuple()))
        startWindow = dayt.replace(hour=0,minute=0,second=0,microsecond=0)
        deltaWindow = datetime.timedelta(days=1)
        endWindow = startWindow + deltaWindow
      else:
        if 'startDate' in config:
          startWindow = config['startDate']
          deltaWindow = config.get('deltaWindow')
          if not deltaWindow:
            deltaWindow = globalDefaultDeltaWindow
          endWindow = startWindow + deltaWindow
          logger.warn("insufficient window information in table or config. Using startWindow=startDate (%s) and deltaWindoww (%s)",startWindow,deltaWindow)
    if 'startDate' in config:
      startDate = config['startDate']
      if startDate and (not startWindow or startWindow < startDate):
        logger.warn("Adjusting startWindow (was %s) and endWindow to match more recent startDate: %s",startWindow,startDate)
        startWindow = startDate
        endWindow = startWindow+deltaWindow
    if tStartWindow and startWindow < tStartWindow:
      logger.warn("Discarded config.startWindow (%s), using table value (%s) (also adjusted endWindow)",startWindow,tStartWindow)
      startWindow = tStartWindow
      endWindow = startWindow + deltaWindow
    return (startWindow,deltaWindow,endWindow)
  except:
    lib_util.reportExceptionAndAbort(logger)

def getDefaultDateInterval(cursor,tableName,delay,initialDeltaDate,defaultDeltaWindow,productVersionRestriction,logger):
  """
  Calculates startDate, deltaWindow from latest entry in tableName (else initialDeltaDate, defaultDeltaWindow)
  if no such table, logs failure and exits
  Calculates endDate from now and deltaWindow
  if initialDeltaDate or defaultDeltaWindow is used, logs an info message
  returns (startDate, endDate, latestWindowEnd)
  """
  eWindow,dWindow = getLastWindowAndSizeFromTable(cursor, tableName, productVersionRestriction, logger)
  return getDefaultDateIntervalFromArgs(tableName,eWindow,dWindow,delay,initialDeltaDate,defaultDeltaWindow,logger)

def getDefaultDateIntervalFromArgs(tableName,latestWindowEnd,deltaWindow,delay,initialDeltaDate,defaultDeltaWindow,logger):
  """
  Calculates startDate, deltaWindow from latestWindowEnd, deltaWindow (else initialDeltaDate, defaultDeltaWindow)
  Calculates endDate from now and deltaWindow
  if initialDeltaDate or defaultDeltaWindow is used, logs an info message
  returns (startDate, endDate, latestWindowEnd)
  """
  #raise IndexError
  now = datetime.datetime.now() - delay
  myMidnight = now.replace(hour=0,minute=0,second=0,microsecond=0)
  if latestWindowEnd:
    startDate = latestWindowEnd
  else:
    startDate = myMidnight - initialDeltaDate
    logger.info("Table %s has no latest entry. Default startDate is  %s",tableName,startDate)
  if not deltaWindow:
    deltaWindow = defaultDeltaWindow
    logger.info("Table %s has no window_size entry. Using default = %s",tableName,deltaWindow)
  endDate = myMidnight
  while endDate + deltaWindow < now:
    endDate += deltaWindow
  return (startDate,endDate,latestWindowEnd)

def getLastWindowAndSizeFromTable(cursor, table, productVersionRestriction, logger):
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
    if productVersionRestriction:
      cursor.execute("SELECT window_end,window_size FROM %s where productdims_id = %s ORDER BY window_end DESC LIMIT 1" % (table, productVersionRestriction))
    else:
      cursor.execute("SELECT window_end,window_size FROM %s ORDER BY window_end DESC LIMIT 1" % table)
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

def getProductId(aProduct, aVersion, aCursor, logger):
  logger.debug("getProductId")
  if not aProduct or not aVersion:
    return None
  try:
    return psy.singleValueSql(aCursor, "select id from productdims where product = %s and version = %s", (aProduct, aVersion))
  except psy.SQLDidNotReturnSingleValue:
    lib_util.reportExceptionAndAbort(logger)

def getDateAndWindow(configContext,tableName,productVersionRestriction,cursor,logger,**kwargs):
  """
  Calculates outer processing interval (Date) and inner processing interval (Window) 
    arguments:
      configContext provides as many of these options as desired:
       window: interval for which reports are agregated into the materialized view table: start <= time < end
        startWindow: a datetime representing the beginning of an aggregation interval
        deltaWindow: a datetime interval representing the duration of an aggregation interval
        processingInterval: synonym for deltaWindow
        endWindow:   a datetime representing the limit of an aggregation window
        processingDelay: a heuristic to avoid processing a window before (most) all its crashes are submitted
      date: interval holding a one or more windows: Cron job will run less often than deltaWindow
        startDate:   a datetime representing the beginning of a date interval
        deltaDate:   a datetime interval representing the duration of a date interval
        endDate:     a datetime representing the limit of a date interval
        initialDeltaDate: used if no start/end/delta Date is supplied and there is no table data
      backward compatibility:
        initialIntervalDays: if no initialDeltaDate, initialDeltaDate is this count of days
        processingDay: specifies startDate, startWindow (midnight) and endDate (next midnight)
      tableName: a table which has
        columns window_end (timestamp) and window_size (interval)
        column productdims_id as a foreign key integer (needed when productVersionRestriction is used)
      productVersionRestriction: an integer from the id column of table productdims
      cursor: A cursor active in the appropriate database
      logger: Suitable for logging warnings, errors
      kwargs: optional overrides to configContext

    returns: a tuple: (startDate, deltaDate, endDate, startWindow, deltaWindow, endWindow)
    alters parameter: configContext will hold the returned values

    heuristic:
      kwargs beats configContext beats information in the table.
      if there is productVersionRestriction, select where productVersionRestriction == productdims_id when using table
      for each 'item' which is a Date or a Window:
        zero config/kwargs per item:  select startWindow, deltaWindow from table if possible:
          startWindow is the most recently collected window_end from table
          if needed, startDate is the same
          deltaWindow is the most recently collected window_size from table
          if needed endDate is based on now()
        one config/kwargs per item: The other is gathered from the table if possible, or now()
        two config/kwargs per item: use them (see below for adjustments, difficulties), ignore table
        three config/kwargs per item: assert they are consistent (start + delta == end), ignore table
      after gathering from table, if possible, making use of initalDeltaDate if necessary:
        if there is sufficient information, calculate and return
        if there is insufficient or contradictory information, raise an error
    If there is redundant information, kwargs beats config beats table data; and in the case of redundancy
    based on multiple sources, contradictory information is not a cause for error
    Any two of the three elements for Window or Date are sufficient, and any pair is allowed

    the table is always consulted:
      If startDate < the latest (productVersionRestricted) window_end:
        startDate = latest_window_end
      If startWindow < the latest (productVersionRestricted) window_end:
        startWindow = latest_window_end
    if, after adjusting, endDate < startDate, the inconsistency is logged and an error raised
    """
  myConfig = {}
  myConfig.update(configContext) # ~== copy.copy(configContext), but simple dict
  myConfig.update(kwargs) # kwargs beats (and adds to) config
  myConfig.setdefault('deltaWindow',myConfig.get('processingInterval'))
  #handle backward compatibility
  if 'initialIntervalDays' in myConfig and not 'initialDeltaDate' in myConfig:
    try:
      myConfig['initialDeltaDate'] = int(myConfig.get('initialIntervalDays',0)*datetime.timedelta(days=1))
    except ValueError, x:
      logger.warn("Non-integer value for 'initialIntervalDays': [%s]. Deprecated. Use 'initialDeltaDate'",myConfig.get('initialIntervalDays'))
  if 'processingDay' in myConfig:
    if not 'startDate' in myConfig and not 'endDate' in myConfig and not 'deltaDate' in myConfig:
      processingDay = cm.dateTimeConverter("%(procssingDay)s"%myConfig)
      myConfig['startDate'] = datetime.datetime(processingDay.year,processinDay.month,processingDay.day)
      myConfig['deltaDate'] = datetime.timedelta(days=1)
      myConfig['endDate'] = myConfig['startDate'] + myConfig['deltaDate']

  # handle defaults
  myConfig.setdefault('initialDeltaDate',globalInitialDeltaDate)
  myConfig.setdefault('processingDelay',globalDefaultProcessingDelay)

  # normalize types
  for item in ['startDate','endDate','startWindow','endWindow']:
    if item in myConfig:
      v = "%s"%(myConfig.get(item))
      myConfig[item] = cm.dateTimeConverter(v)
  for item in ['deltaDate','deltaWindow','initialDeltaDate']:
    if item in myConfig:
      v = myConfig.get(item)
      if type(v) is str:
        myConfig[item] = cm.timeDeltaConverter(v)

  # always try for last appropriate line in the table, in case startDate needs adjustment
  tableWindowEnd, tableWindowSize = getLastWindowAndSizeFromTable(cursor,tableName,productVersionRestriction,logger)
  if 'startDate' in myConfig and tableWindowEnd and myConfig['startDate'] < tableWindowEnd:
    myConfig['startDate'] = tableWindowEnd
    if 'deltaDate' in myConfig and 'endDate' in myConfig:
      myConfig['deltaDate'] = myConfig['endDate'] - myConfig['startDate']

  #### all the data ducks are aligned. Now do the work ####
  delay = myConfig['processingDelay'] # just an alias
  initialDeltaDate = myConfig['initialDeltaDate']
  defaultDeltaWindow = myConfig.get('defaultDeltaWindow',globalDefaultDeltaWindow)
  if not defaultDeltaWindow: # maybe a config value was specified as None or ''
    defaultDeltaWindow = globalDefaultDeltaWindow
  workingDeltaWindow = myConfig.get('deltaWindow')
  if not workingDeltaWindow:
    workingDeltaWindow = tableWindowSize # kwargs,config beat table for this
  if 'deltaDate' in myConfig:
    assert myConfig['deltaDate'] > datetime.timedelta(0)
    if 'startDate' in myConfig:
      if 'endDate' in myConfig:
        assert myConfig['startDate'] + myConfig['deltaDate'] == myConfig['endDate'],'Got startD: %s, deltaD: %s, endD: %s. Actual deltaD: %s'%(myConfig['startDate'],myConfig['deltaDate'],myConfig['endDate'],myConfig['endDate']-myConfig['startDate'])
      else:
        myConfig['endDate'] = myConfig['startDate'] + myConfig['deltaDate']
    elif 'endDate' in myConfig:
      myConfig['startDate'] = myConfig['endDate'] - myConfig['deltaDate']
      if myConfig['startDate'] > tableWindowEnd:
        logger.warn('config values for endDate [%s] and deltaDate [%s] are incompatible with column %s.window_end [%s]',myConfig['endDate'],myConfig['deltaDate'],tableWindowEnd)
        myConfig['startDate'],myConfig['deltaDate'], myConfig['endDate'] = tableWindowEnd,datetime.timedelta(0),tableWindowEnd
    else:
      # we have deltaDate but neither start nor end. That is a logic error, but maybe we can do something useful:
      defSdate,defEdate,ignore = getDefaultDateIntervalFromArgs(tableName,tableWindowEnd,workingDeltaWindow,delay,initialDeltaDate,globalDefaultDeltaWindow,logger)
      if defSdate and defEdate:
        myConfig['startDate'] = defSdate
        myConfig['endDate'] = defEdate
        logger.warn("Ignoring configured solo deltaDate [%s] using default/calculated startDate [%s], endDate[%s] deltaDate[%s]", myConfig['deltaDate'],defSdate,defEdate,(defEdate - defSdate))
        myConfig['deltaDate'] = defEdate - defSdate
      else:
        assert False, 'Cannot generate start and end dates'
        lib_util.reportExceptionAndAbort(logger)
  else: # no deltaDate:
    if 'startDate' in myConfig:
      if 'endDate' in myConfig:
        assert myConfig['startDate'] < myConfig['endDate']
        myConfig['deltaDate'] = myConfig['endDate'] - myConfig['startDate']
      else: # startDate only
        ignore,defEdate,ignore = getDefaultDateIntervalFromArgs(tableName,tableWindowEnd,workingDeltaWindow,delay, initialDeltaDate,defaultDeltaWindow,logger)
        assert not defEdate or (myConfig['startDate'] < defEdate)
        myConfig['deltaDate'] = defEdate - myConfig['startDate']
        myConfig['endDate'] = defEdate
        logger.warn("using solo startDate [%s], default/calculated deltaDate [%s], endDate [%s]",myConfig['startDate'],myConfig['deltaDate'],defEdate)
    elif 'endDate' in myConfig:
      defSdate,ignore,ignore = getDefaultDateIntervalFromArgs(tableName,tableWindowEnd,workingDeltaWindow,delay, initialDeltaDate,defaultDeltaWindow,logger)
      assert defSdate < myConfig['endDate']
      myConfig['startDate'] = defSdate
      myConfig['deltaDate'] = myConfig['endDate'] = defSdate
      logger.warn("using solo endDate [%s], default/calculated startDate [%s], deltaDate [%s]",myConfig['endDate'],myConfig['startDate'],myConfig['deltaDate'])
    else: # we got nothing
      defSdate,defEdate,ignore = getDefaultDateIntervalFromArgs(tableName,tableWindowEnd,workingDeltaWindow,delay, initialDeltaDate,defaultDeltaWindow,logger)
      myConfig['startDate'] = defSdate
      myConfig['deltaDate'] = defEdate - defSdate
      myConfig['endDate'] = defEdate
  assert myConfig.get('startDate') and myConfig.get('deltaDate') and myConfig.get('endDate')
  myConfig['startWindow'],myConfig['deltaWindow'],myConfig['endWindow'] = getProcessingWindowFromArgs(myConfig,tableWindowEnd,workingDeltaWindow,logger)

  configContext.update(myConfig)
  return myConfig['startDate'],myConfig['deltaDate'],myConfig['endDate'],myConfig['startWindow'],myConfig['deltaWindow'],myConfig['endWindow']
