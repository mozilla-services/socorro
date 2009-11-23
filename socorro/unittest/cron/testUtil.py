import datetime
import errno
import logging
import os
import psycopg2
import time
import unittest
from nose.tools import *

import socorro.lib.ConfigurationManager as configurationManager

import socorro.unittest.testlib.dbtestutil as dbtestutil
import socorro.unittest.testlib.util as tutil

import socorro.cron.util as cron_util
import cronTestconfig as testConfig


class Me(): # not quite "self"
  """
  I need stuff to be initialized once per module. Rather than having a bazillion globals, lets just have 'me'
  """
  pass
me = None

def setup_module():
  global me
  if me:
    return
  tutil.nosePrintModule(__file__)
  me = Me()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Cron Util')
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass
  me.logFilePathname = me.config.logFilePathname
  if not me.logFilePathname:
    me.logFilePathname = 'logs/util_test.log'
  logFileDir = os.path.split(me.logFilePathname)[0]
  try:
    os.makedirs(logFileDir)
  except OSError,x:
    if errno.EEXIST == x.errno: pass
    else: raise
  f = open(me.logFilePathname,'w')
  f.close()
  fileLog = logging.FileHandler(me.logFilePathname, 'a')
  fileLog.setLevel(logging.DEBUG)
  fileLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
  fileLog.setFormatter(fileLogFormatter)
  me.fileLogger = logging.getLogger("testUtil")
  me.fileLogger.addHandler(fileLog)
  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)

def teardown_module():
  try:
    os.unlink(me.logFilePathname)
  except:
    pass

class TestUtil(unittest.TestCase):
  def setUp(self):
    global me
    self.connection = psycopg2.connect(me.dsn)
    self.tableName = 'bunny_test'

  def tearDown(self):
    self.dropBunny()

  def createBunny(self):
    cursor = self.connection.cursor()
    cursor.execute("CREATE TABLE %s (id serial not null,window_end TIMESTAMP WITHOUT TIME ZONE NOT NULL,window_size INTERVAL NOT NULL)"%self.tableName)
    self.connection.commit()

  def dropBunny(self):
    self.connection.cursor().execute("DROP TABLE IF EXISTS %s CASCADE"%(self.tableName))
    self.connection.commit()

  def testGetProcessingDates(self):
    config = {}
    config['processingDelay'] = datetime.timedelta(0)
    cursor = self.connection.cursor()
    self.connection.rollback()
    self.createBunny()
    now = datetime.datetime.now()
    midnight = now.replace(hour=0,minute=0,second=0,microsecond=0)
    defStart = midnight - cron_util.globalInitialDeltaDate
    defEnd = midnight
    while defEnd + cron_util.globalDefaultDeltaWindow < now:
      defEnd += cron_util.globalDefaultDeltaWindow

    mm = cron_util.getProcessingDates(config,self.tableName,None,cursor,me.fileLogger)
    assert (defStart,defEnd-defStart,defEnd) == mm, 'But got %s'%(str(mm))
    start = datetime.datetime(2000,1,2,12,12)
    delta = datetime.timedelta(days=3)
    end = start+delta

    # check that just one kwarg raises SystemExit
    assert_raises(SystemExit,cron_util.getProcessingDates,config,self.tableName,None,cursor,me.fileLogger,startDate=start)
    assert_raises(SystemExit,cron_util.getProcessingDates,config,self.tableName,None,cursor,me.fileLogger,endDate=end)
    assert_raises(SystemExit,cron_util.getProcessingDates,config,self.tableName,None,cursor,me.fileLogger,deltaDate=delta)

    # check that just one config raises SystemExit
    assert_raises(SystemExit,cron_util.getProcessingDates,{'startDate':start},self.tableName,None,cursor,me.fileLogger)
    assert_raises(SystemExit,cron_util.getProcessingDates,{'endDate':end},self.tableName,None,cursor,me.fileLogger)
    assert_raises(SystemExit,cron_util.getProcessingDates,{'deltaDate':delta},self.tableName,None,cursor,me.fileLogger)

    # check that two are sufficient
    mm = cron_util.getProcessingDates({'startDate':start},self.tableName,None,cursor,me.fileLogger,endDate=end)
    assert (start,delta,end) == mm, "But got %s"%(str(mm))
    mm = cron_util.getProcessingDates({'startDate':start},self.tableName,None,cursor,me.fileLogger,deltaDate=delta)
    assert (start,delta,end) == mm, "But got %s"%(str(mm))
    mm = cron_util.getProcessingDates({'endDate':end},self.tableName,None,cursor,me.fileLogger,startDate=start)
    assert (start,delta,end) == mm, "But got %s"%(str(mm))
    mm = cron_util.getProcessingDates({'endDate':end},self.tableName,None,cursor,me.fileLogger,deltaDate=delta)
    assert (start,delta,end) == mm, "But got %s"%(str(mm))
    mm = cron_util.getProcessingDates({'deltaDate':delta},self.tableName,None,cursor,me.fileLogger,endDate=end)
    assert (start,delta,end) == mm, "But got %s"%(str(mm))
    mm = cron_util.getProcessingDates({'deltaDate':delta},self.tableName,None,cursor,me.fileLogger,startDate=start)
    assert (start,delta,end) == mm, "But got %s"%(str(mm))

    # check various inconsistencies
    assert_raises(SystemExit,cron_util.getProcessingDates,{'startDate':start},self.tableName,None,cursor,me.fileLogger,endDate=start)
    assert_raises(SystemExit,cron_util.getProcessingDates,{'startDate':start},self.tableName,None,cursor,me.fileLogger,endDate=start-delta)
    assert_raises(SystemExit,cron_util.getProcessingDates,{'startDate':start},self.tableName,None,cursor,me.fileLogger,deltaDate=datetime.timedelta(0))
    assert_raises(SystemExit,cron_util.getProcessingDates,{'startDate':start},self.tableName,None,cursor,me.fileLogger,deltaDate=datetime.timedelta(days=-1))

    # Check that table with earlier row is ignored
    early = start-datetime.timedelta(days=1)
    cursor.execute("INSERT INTO %s (window_end,window_size) VALUES(%%s,%%s)"%self.tableName,(early,delta))
    self.connection.commit()
    mm = cron_util.getProcessingDates(config,self.tableName,None,cursor,me.fileLogger,startDate=start,endDate=end)
    assert (start,delta,end) == mm, "But got %s"%(str(mm))

    # Check that table with later row is used
    later = start+datetime.timedelta(days=1)
    cursor.execute("INSERT INTO %s (window_end,window_size) VALUES(%%s,%%s)"%self.tableName,(later,delta))
    self.connection.commit()
    mm = cron_util.getProcessingDates(config,self.tableName,None,cursor,me.fileLogger,startDate=start,endDate=end)
    assert (later,end-later,end) == mm, 'Expected %s, got %s'%(str((later,end-later,end)),str(mm))

    # Check that table with 'too late' time causes assertion
    later = later+datetime.timedelta(days=4)
    cursor.execute("INSERT INTO %s (window_end,window_size) VALUES(%%s,%%s)"%self.tableName,(later,delta))
    self.connection.commit()
    assert_raises(SystemExit,cron_util.getProcessingDates,config,self.tableName,None,cursor,me.fileLogger,startDate=start,endDate=end)

  def testGetProcessingWindow(self):
    cursor = self.connection.cursor()
    config = {}
    # check that a really empty system fails
    assert_raises(SystemExit,cron_util.getProcessingWindow,config,self.tableName,None,cursor,me.fileLogger)

    self.createBunny()
    # check that nothing useful yields nothing
    mm = cron_util.getProcessingWindow(config,self.tableName,None,cursor,me.fileLogger)
    assert (None,None,None) == mm, 'Expected None*3, got %s'%(str(mm))

    start = datetime.datetime(2000,1,2,12,12)
    delta = datetime.timedelta(seconds=300)
    end = start+delta

    procDay = datetime.date(2001,9,8)
    procStart = datetime.datetime(2001,9,8)
    procDelta = datetime.timedelta(days=1)
    procEnd = procStart+procDelta

    # check that just one kwarg raises SystemExit
    assert_raises(SystemExit,cron_util.getProcessingWindow,config,self.tableName,None,cursor,me.fileLogger,startWindow=start)
    assert_raises(SystemExit,cron_util.getProcessingWindow,config,self.tableName,None,cursor,me.fileLogger,endWindow=start)
    assert_raises(SystemExit,cron_util.getProcessingWindow,config,self.tableName,None,cursor,me.fileLogger,deltaWindow=delta)

    # check that just one config raises SystemExit
    assert_raises(SystemExit,cron_util.getProcessingWindow,{'startWindow':start},self.tableName,None,cursor,me.fileLogger)
    assert_raises(SystemExit,cron_util.getProcessingWindow,{'endWindow':end},self.tableName,None,cursor,me.fileLogger)
    assert_raises(SystemExit,cron_util.getProcessingWindow,{'deltaWindow':delta},self.tableName,None,cursor,me.fileLogger)

    # check that processingDay doesn't help
    assert_raises(SystemExit,cron_util.getProcessingWindow,config,self.tableName,None,cursor,me.fileLogger,deltaWindow=delta,processingDay=procDay)
    assert_raises(SystemExit,cron_util.getProcessingWindow,config,self.tableName,None,cursor,me.fileLogger,startWindow=start,processingDay=procDay)
    assert_raises(SystemExit,cron_util.getProcessingWindow,config,self.tableName,None,cursor,me.fileLogger,endWindow=start,processingDay=procDay)
    # ... with config either
    assert_raises(SystemExit,cron_util.getProcessingWindow,{'startWindow':start},self.tableName,None,cursor,me.fileLogger,processingDay=procDay)
    assert_raises(SystemExit,cron_util.getProcessingWindow,{'endWindow':end},self.tableName,None,cursor,me.fileLogger,processingDay=procDay)
    assert_raises(SystemExit,cron_util.getProcessingWindow,{'deltaWindow':delta,'processingDay':procDay},self.tableName,None,cursor,me.fileLogger)

    # check that any two kwargs work correctly
    mm = cron_util.getProcessingWindow(config,self.tableName,None,cursor,me.fileLogger,endWindow=end,startWindow=start)
    assert (start,delta,end) == mm, 'But got %s'%(str(mm))
    mm = cron_util.getProcessingWindow(config,self.tableName,None,cursor,me.fileLogger,deltaWindow=delta,startWindow=start)
    assert (start,delta,end) == mm, 'But got %s'%(str(mm))
    mm = cron_util.getProcessingWindow(config,self.tableName,None,cursor,me.fileLogger,endWindow=end,deltaWindow=delta)
    assert (start,delta,end) == mm, 'But got %s'%(str(mm))

    # and that two configs work
    mm = cron_util.getProcessingWindow({'endWindow':end,'startWindow':start},self.tableName,None,cursor,me.fileLogger)
    assert (start,delta,end) == mm, 'But got %s'%(str(mm))

    # and that one of each works  (not full test because using transparent box testing)
    mm = cron_util.getProcessingWindow({'deltaWindow':delta},self.tableName,None,cursor,me.fileLogger,startWindow=start)

    # check that three good kwargs works
    mm = cron_util.getProcessingWindow(config,self.tableName,None,cursor,me.fileLogger,endWindow=end,deltaWindow=delta,startWindow=start)
    assert (start,delta,end) == mm, 'But got %s'%(str(mm))

    # check that three incompatible kwargs fails
    badDelta = delta + delta
    assert_raises(SystemExit,cron_util.getProcessingWindow,config,self.tableName,None,cursor,me.fileLogger,endWindow=end,deltaWindow=badDelta,startWindow=start)

    # check that good processingDay works as expected
    mm = cron_util.getProcessingWindow(config,self.tableName,None,cursor,me.fileLogger,processingDay=procDay)
    assert (procStart,procDelta,procEnd) == mm, 'But got %s'%(str(mm))

    #check that invalid date (because it is a datetime) fails
    extraProcDay = datetime.datetime(2001,9,8,7,6,5)
    assert_raises(SystemExit,cron_util.getProcessingWindow,config,self.tableName,None,cursor,me.fileLogger,processingDay=extraProcDay)

    # check that kwargs beats config (not full test because using transparent box testing)
    otherProcDay = datetime.datetime(2003,9,8,7,6,5)
    mm = cron_util.getProcessingWindow({'processingDay':otherProcDay},self.tableName,None,cursor,me.fileLogger,processingDay=procDay)
    assert (procStart,procDelta,procEnd) == mm, 'But got %s'%(str(mm))


  def testGetLastWindowAndSizeFromTable(self):
    cursor = self.connection.cursor()
    # test the no-such-table case
    assert_raises(SystemExit,cron_util.getLastWindowAndSizeFromTable,cursor,self.tableName,None,me.fileLogger)
    self.connection.rollback()

    # test the missing-column case
    self.createBunny()
    cursor.execute("ALTER TABLE %s drop column window_end"%self.tableName)
    self.connection.commit()
    assert_raises(SystemExit,cron_util.getLastWindowAndSizeFromTable,cursor,self.tableName,None,me.fileLogger)
    self.connection.rollback()
    self.dropBunny()

    # test the correct but empty case
    self.createBunny()
    mm = cron_util.getLastWindowAndSizeFromTable(cursor,self.tableName,None,me.fileLogger)
    assert (None,None) == mm, 'Expect no time data, got %s'%(str(mm))

    end = datetime.datetime(2001,2,3,12)

    # test the case with negative size
    delta = datetime.timedelta(seconds=-600)
    cursor.execute("INSERT INTO %s (window_end,window_size) VALUES(%%s,%%s)"%self.tableName,(end,delta))
    self.connection.commit()
    assert_raises(SystemExit,cron_util.getLastWindowAndSizeFromTable,cursor,self.tableName,None,me.fileLogger)
    self.connection.rollback()
    self.dropBunny()

    # test the case with zero size
    self.createBunny()
    delta = datetime.timedelta(days=0)
    cursor.execute("INSERT INTO %s (window_end,window_size) VALUES(%%s,%%s)"%self.tableName,(end,delta))
    self.connection.commit()
    assert_raises(SystemExit,cron_util.getLastWindowAndSizeFromTable,cursor,self.tableName,None,me.fileLogger)
    self.connection.rollback()
    self.dropBunny()

    # test the case with negative day size
    self.createBunny()
    delta = datetime.timedelta(days=-2)
    cursor.execute("INSERT INTO %s (window_end,window_size) VALUES(%%s,%%s)"%self.tableName,(end,delta))
    self.connection.commit()
    assert_raises(SystemExit,cron_util.getLastWindowAndSizeFromTable,cursor,self.tableName,None,me.fileLogger)
    self.connection.rollback()
    self.dropBunny()

    # test the case with non-minute size
    self.createBunny()
    delta = datetime.timedelta(seconds=1234)
    cursor.execute("INSERT INTO %s (window_end,window_size) VALUES(%%s,%%s)"%self.tableName,(end,delta))
    self.connection.commit()
    assert_raises(SystemExit,cron_util.getLastWindowAndSizeFromTable,cursor,self.tableName,None,me.fileLogger)
    self.connection.rollback()
    self.dropBunny()

    # test the case with more than a day
    self.createBunny()
    delta = datetime.timedelta(days=1,seconds=4)
    cursor.execute("INSERT INTO %s (window_end,window_size) VALUES(%%s,%%s)"%self.tableName,(end,delta))
    self.connection.commit()
    assert_raises(SystemExit,cron_util.getLastWindowAndSizeFromTable,cursor,self.tableName,None,me.fileLogger)
    self.connection.rollback()
    self.dropBunny()

    # test a good case
    self.createBunny()
    delta = datetime.timedelta(seconds=720)
    cursor.execute("INSERT INTO %s (window_end,window_size) VALUES(%%s,%%s)"%self.tableName,(end,delta))
    self.connection.commit()
    mm = cron_util.getLastWindowAndSizeFromTable(cursor,self.tableName,None,me.fileLogger)
    assert (end,delta) == mm, 'Expected %s, got %s'%(str((end,delta)),str(mm))

    # be sure we get the correct row
    delta0 = datetime.timedelta(seconds=60)
    delta1 = datetime.timedelta(seconds=120)
    end0 = end+delta0
    end1 = end-delta0
    cursor.execute("INSERT INTO %s (window_end,window_size) VALUES(%%s,%%s),(%%s,%%s)"%self.tableName,(end0,delta0,end1,delta1))
    self.connection.commit()
    mm = cron_util.getLastWindowAndSizeFromTable(cursor,self.tableName,None,me.fileLogger)
    assert (end0,delta0) == mm, 'Expected %s, got %s'%(str((end0,delta0)),str(mm))

  def testGetDefaultDateInterval(self):
    cursor = self.connection.cursor()
    initialDeltaDate = datetime.timedelta(days=1)
    defaultDeltaWindow = datetime.timedelta(minutes=24)

    # check expected exception with no table
    assert_raises(SystemExit,cron_util.getDefaultDateInterval,cursor,self.tableName,datetime.timedelta(0),initialDeltaDate,defaultDeltaWindow,None,me.fileLogger)

    # check with empty table
    self.createBunny()
    now = datetime.datetime.now()
    midNight = now.replace(hour=0,minute=0,second=0,microsecond=0)
    defStart = midNight - initialDeltaDate
    defEnd = midNight
    while defEnd+defaultDeltaWindow < now:
      defEnd += defaultDeltaWindow
    ddi = cron_util.getDefaultDateInterval(cursor,self.tableName,datetime.timedelta(0),initialDeltaDate,defaultDeltaWindow,None,me.fileLogger)
    assert (defStart,defEnd,None) == ddi, "But got %s"%(str(ddi))

    # check with one row in table
    end0 = datetime.datetime(2008,12,11,10)
    delta0 = datetime.timedelta(minutes=15)
    cursor.execute("INSERT INTO %s (window_end,window_size) VALUES(%%s,%%s)"%self.tableName,(end0,delta0))
    self.connection.commit()
    ddi = cron_util.getDefaultDateInterval(cursor,self.tableName,datetime.timedelta(0),initialDeltaDate,defaultDeltaWindow,None,me.fileLogger)
    now = datetime.datetime.now()
    midNight = now.replace(hour=0,minute=0,second=0,microsecond=0)
    defEnd = midNight
    while defEnd+delta0 < now:
      defEnd += delta0
    assert (end0,defEnd,end0) == ddi, 'But %s != %s'%(str((end0,defEnd,end0,)),str(ddi))

