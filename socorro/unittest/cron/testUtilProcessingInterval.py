import datetime
import os
import psycopg2
import unittest
import socorro.cron.util as cron_util
import socorro.lib.ConfigurationManager as configurationManager
import cronTestconfig as testConfig
import socorro.database.database as sdatabase

import socorro.unittest.testlib.util as tutil
from socorro.unittest.testlib.loggerForTest import TestingLogger

logger = TestingLogger()

class Me: pass
me = None

def setup_module():
  global me
  if me:
    return
  tutil.nosePrintModule(__file__)
  me = Me()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing Cron Util for Processing Intervals')
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass
  #me.dsn = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % (me.config)
  me.database = sdatabase.Database(me.config)

class TestUtilProcessingInterval(unittest.TestCase):
  def setUp(self):
    global me
    self.connection = me.database.connection()
    #self.connection = psycopg2.connect(me.dsn)
    self.tableName = 'bunny_test'
    self.dropBunny()
    self.createBunny()
  def tearDown(self):
    self.dropBunny()

  def createBunny(self):
    cursor = self.connection.cursor()
    cursor.execute("CREATE TABLE %s (id serial not null,window_end TIMESTAMP WITHOUT TIME ZONE NOT NULL,window_size INTERVAL NOT NULL)"%self.tableName)
    self.connection.commit()

  def dropBunny(self):
    self.connection.cursor().execute("DROP TABLE IF EXISTS %s CASCADE"%(self.tableName))
    self.connection.commit()

  def testGetDateAndWindow_noBunny(self):
    """
    testUtilProcessingInterval:TestUtilProcessingInterval.testGetDateAndWindow_noBunny
    """
    config = {}
    kwargs = {}
    now = datetime.datetime.now()
    if 59 == now.minute and now.second > 58: # avoid rolling over the edge of an hour
      time.sleep(3)
      now = datetime.datetime.now()
    nowMid = now.replace(hour=0,minute=0,second=0,microsecond=0)
    nowRound = now.replace(minute=0,second=0,microsecond=0)
    expectedStartDate = nowMid - cron_util.globalInitialDeltaDate
    deltaWinMinutes = cron_util.globalDefaultDeltaWindow.seconds/60
    more = datetime.timedelta(minutes=deltaWinMinutes*(now.minute/deltaWinMinutes))
    expectedEndDate = nowRound + more - cron_util.globalDefaultProcessingDelay
    expectedDeltaDate = expectedEndDate - expectedStartDate
    gotSdate,gotDdate,gotEdate,gotSwin,gotDwin,gotEwin = cron_util.getDateAndWindow(config,self.tableName,None,self.connection.cursor(),logger,**kwargs)
    assert expectedStartDate == gotSdate, "But: SD E:%s, G:%s, DIFF: %s"%(expectedStartDate, gotSdate, gotSdate-expectedStartDate)
    assert expectedDeltaDate == gotDdate, "but: DD E:%s, G:%s, DIFF: %s"%(expectedDeltaDate, gotDdate, gotDdate-expectedDeltaDate)
    assert expectedEndDate   == gotEdate, "but: ED E:%s, G:%s, DIFF: %s"%(expectedEndDate,   gotEdate, gotEdate-expectedEndDate)
    assert expectedStartDate == gotSwin,  "but: SW E:%s, G:%s"%(expectedStartDate,gotSwin)
    assert cron_util.globalDefaultDeltaWindow == gotDwin, "but: DW E:%s, G:%s"%(cron_util.globalDefaultDeltaWindow,gotDwin)
    assert gotSwin+gotDwin   == gotEwin,  "but: EW E:%s, G:%s" %(gotSwin+gotDwin,gotEwin)

    config = {}
    kwargs = {
      'startWindow':'2009-09-09T00:00:00',
      'deltaWindow':'1:0:0',
      'startDate':'2009-09-09T00:00:00',
      }
    now = datetime.datetime.now()
    if 59 == now.minute and now.second > 58: # avoid rolling over the edge of an hour
      time.sleep(3)
      now = datetime.datetime.now()
    nowMid = now.replace(hour=0,minute=0,second=0,microsecond=0)
    nowRound = now.replace(minute=0,second=0,microsecond=0)
    expectedDeltaWindow = configurationManager.timeDeltaConverter(kwargs['deltaWindow'])
    deltaWinMinutes = expectedDeltaWindow.seconds/60
    more = datetime.timedelta(minutes=deltaWinMinutes*(now.minute/deltaWinMinutes))
    expectedStartDate = datetime.datetime(2009,9,9)
    expectedEndDate = nowRound + more - cron_util.globalDefaultProcessingDelay
    expectedDeltaDate = expectedEndDate - expectedStartDate
    expected = {
      'startDate': expectedStartDate,
      'deltaDate': expectedDeltaDate,
      'endDate':  expectedEndDate,
      'startWindow': expectedStartDate,
      'deltaWindow': expectedDeltaWindow,
      'endWindow': expectedStartDate+expectedDeltaWindow
      }

    ignore = cron_util.getDateAndWindow(config,self.tableName,None,self.connection.cursor(),logger,**kwargs)
    for k,v in expected.items():
      assert v == config.get(k), "but %s: Expected %s, got %s"%(k,v,config.get(k))

    config = {}
    kwargs = {
      'startWindow':'2009-09-09T00:00:00',
      'deltaWindow':'1:0:0',
      'startDate':'2009-09-01T00:00:00',
      }
    now = datetime.datetime.now()
    if 59 == now.minute and now.second > 58: # avoid rolling over the edge of an hour
      time.sleep(3)
      now = datetime.datetime.now()
    nowMid = now.replace(hour=0,minute=0,second=0,microsecond=0)
    nowRound = now.replace(minute=0,second=0,microsecond=0)
    expectedDeltaWindow = configurationManager.timeDeltaConverter(kwargs['deltaWindow'])
    deltaWinMinutes = expectedDeltaWindow.seconds/60
    more = datetime.timedelta(minutes=deltaWinMinutes*(now.minute/deltaWinMinutes))
    expectedStartWindow = datetime.datetime(2009,9,9)
    expectedStartDate = datetime.datetime(2009,9,1)
    expectedEndDate = nowRound + more - cron_util.globalDefaultProcessingDelay
    expectedDeltaDate = expectedEndDate - expectedStartDate
    expected = {
      'startDate': expectedStartDate,
      'deltaDate': expectedDeltaDate,
      'endDate':  expectedEndDate,
      'startWindow': expectedStartWindow,
      'deltaWindow': expectedDeltaWindow,
      'endWindow': expectedStartWindow+expectedDeltaWindow
      }

    ignore = cron_util.getDateAndWindow(config,self.tableName,None,self.connection.cursor(),logger,**kwargs)
    for k,v in expected.items():
      assert v == config.get(k), "but %s: Expected %s, got %s"%(k,v,config.get(k))

    config = {}
    kwargs = {
      'startWindow':'2009-09-01T00:00:00',
      'deltaWindow':'1:0:0',
      'startDate':'2009-09-09T00:00:00',
      }
    now = datetime.datetime.now()
    if 59 == now.minute and now.second > 58: # avoid rolling over the edge of an hour
      time.sleep(3)
      now = datetime.datetime.now()
    nowMid = now.replace(hour=0,minute=0,second=0,microsecond=0)
    nowRound = now.replace(minute=0,second=0,microsecond=0)
    expectedDeltaWindow = configurationManager.timeDeltaConverter(kwargs['deltaWindow'])
    deltaWinMinutes = expectedDeltaWindow.seconds/60
    more = datetime.timedelta(minutes=deltaWinMinutes*(now.minute/deltaWinMinutes))
    expectedStartWindow = datetime.datetime(2009,9,9)
    expectedStartDate = datetime.datetime(2009,9,9)
    expectedEndDate = nowRound + more - cron_util.globalDefaultProcessingDelay
    expectedDeltaDate = expectedEndDate - expectedStartDate
    expected = {
      'startDate': expectedStartDate,
      'deltaDate': expectedDeltaDate,
      'endDate':  expectedEndDate,
      'startWindow': expectedStartWindow,
      'deltaWindow': expectedDeltaWindow,
      'endWindow': expectedStartWindow+expectedDeltaWindow
      }

    ignore = cron_util.getDateAndWindow(config,self.tableName,None,self.connection.cursor(),logger,**kwargs)
    for k,v in expected.items():
      assert v == config.get(k), "but %s: Expected %s, got %s"%(k,v,config.get(k))

  def testGetDateAndWindow_withBunny(self):
    """
    testUtilProcessingInterval:TestUtilProcessingInterval.testGetDateAndWindow_withBunny
    """
    windowEndTable = datetime.datetime(2009,10,10,0,0)
    windowSizeTable = datetime.timedelta(minutes=6) #(minutes=60)
    cursor = self.connection.cursor()
    sql = "INSERT INTO %s (window_end, window_size) VALUES (%%s,%%s)"%self.tableName
    cursor.execute(sql,(windowEndTable,windowSizeTable))
    self.connection.commit()

    config = {}
    kwargs = {}
    expectedStartDate = windowEndTable
    now = datetime.datetime.now()
    if 59 == now.minute and now.second > 58: # avoid rolling over the edge of an hour
      time.sleep(3)
      now = datetime.datetime.now()
    nowMid = now.replace(hour=0,minute=0,second=0,microsecond=0)
    nowRound = now.replace(minute=0,second=0,microsecond=0)
    deltaWinMinutes = windowSizeTable.seconds/60
    more = datetime.timedelta(minutes=deltaWinMinutes*(now.minute/deltaWinMinutes))
    expectedEndDate = nowRound + more - cron_util.globalDefaultProcessingDelay
    expectedDeltaDate = expectedEndDate - expectedStartDate
    gotSdate,gotDdate,gotEdate,gotSwin,gotDwin,gotEwin = cron_util.getDateAndWindow(config,self.tableName,None,self.connection.cursor(),logger,**kwargs)
    assert expectedStartDate == gotSdate, "But: SD E:%s, G:%s, DIFF: %s"%(expectedStartDate, gotSdate, gotSdate-expectedStartDate)
    assert expectedDeltaDate == gotDdate, "but: DD E:%s, G:%s, DIFF: %s"%(expectedDeltaDate, gotDdate, gotDdate-expectedDeltaDate)
    assert expectedEndDate   == gotEdate, "but: ED E:%s, G:%s, DIFF: %s"%(expectedEndDate,   gotEdate, gotEdate-expectedEndDate)
    assert expectedStartDate == gotSwin,  "but: SW E:%s, G:%s"%(expectedStartDate,gotSwin)
    assert windowSizeTable == gotDwin, "but: DW E:%s, G:%s"%(windowSizeTable,gotDwin)
    assert gotSwin+gotDwin   == gotEwin,  "but: EW E:%s, G:%s" %(gotSwin+gotDwin,gotEwin)

    config = {}
    kwargs = {
      'startWindow':'2009-09-09T00:00:00',
      'deltaWindow':'1:0:0',
      'startDate':'2009-09-09T00:00:00',
      }
    now = datetime.datetime.now()
    if 59 == now.minute and now.second > 58: # avoid rolling over the edge of an hour
      time.sleep(3)
      now = datetime.datetime.now()
    nowMid = now.replace(hour=0,minute=0,second=0,microsecond=0)
    nowRound = now.replace(minute=0,second=0,microsecond=0)
    expectedDeltaWindow = datetime.timedelta(hours=1)
    deltaWinMinutes = expectedDeltaWindow.seconds/60
    more = datetime.timedelta(minutes=deltaWinMinutes*(now.minute/deltaWinMinutes))
    expectedStartDate = windowEndTable
    expectedEndDate = nowRound + more - cron_util.globalDefaultProcessingDelay
    expectedDeltaDate = expectedEndDate - expectedStartDate
    expected = {
      'startDate': expectedStartDate,
      'deltaDate': expectedDeltaDate,
      'endDate':  expectedEndDate,
      'startWindow': windowEndTable,
      'deltaWindow': expectedDeltaWindow,
      'endWindow': windowEndTable+expectedDeltaWindow,
      }

    ignore = cron_util.getDateAndWindow(config,self.tableName,None,self.connection.cursor(),logger,**kwargs)
    for k,v in expected.items():
      assert v == config.get(k), "but %s: Expected %s, got %s"%(k,v,config.get(k))

    config = {}
    kwargs = {
      'startWindow':'2009-09-09T00:00:00',
      'deltaWindow':'1:0:0',
      'startDate':'2009-09-01T00:00:00',
      }
    now = datetime.datetime.now()
    if 59 == now.minute and now.second > 58: # avoid rolling over the edge of an hour
      time.sleep(3)
      now = datetime.datetime.now()
    nowMid = now.replace(hour=0,minute=0,second=0,microsecond=0)
    nowRound = now.replace(minute=0,second=0,microsecond=0)
    expectedDeltaWindow = datetime.timedelta(hours=1)
    deltaWinMinutes = expectedDeltaWindow.seconds/60
    more = datetime.timedelta(minutes=deltaWinMinutes*(now.minute/deltaWinMinutes))
    expectedStartWindow = windowEndTable
    expectedStartDate = windowEndTable
    expectedEndDate = nowRound + more - cron_util.globalDefaultProcessingDelay
    expectedDeltaDate = expectedEndDate - expectedStartDate
    expected = {
      'startDate': expectedStartDate,
      'deltaDate': expectedDeltaDate,
      'endDate':  expectedEndDate,
      'startWindow': expectedStartWindow,
      'deltaWindow': expectedDeltaWindow,
      'endWindow': expectedStartWindow+expectedDeltaWindow
      }

    ignore = cron_util.getDateAndWindow(config,self.tableName,None,self.connection.cursor(),logger,**kwargs)
    for k,v in expected.items():
      assert v == config.get(k), "but %s: Expected %s, got %s"%(k,v,config.get(k))

    config = {}
    kwargs = {
      'startWindow':'2009-09-01T00:00:00',
      'deltaWindow':'1:0:0',
      'startDate':'2009-09-09T00:00:00',
      }
    now = datetime.datetime.now()
    if 59 == now.minute and now.second > 58: # avoid rolling over the edge of an hour
      time.sleep(3)
      now = datetime.datetime.now()
    nowMid = now.replace(hour=0,minute=0,second=0,microsecond=0)
    nowRound = now.replace(minute=0,second=0,microsecond=0)
    expectedDeltaWindow = configurationManager.timeDeltaConverter(kwargs['deltaWindow'])
    deltaWinMinutes = expectedDeltaWindow.seconds/60
    more = datetime.timedelta(minutes=deltaWinMinutes*(now.minute/deltaWinMinutes))
    expectedStartWindow = windowEndTable
    expectedStartDate = windowEndTable
    expectedEndDate = nowRound + more - cron_util.globalDefaultProcessingDelay
    expectedDeltaDate = expectedEndDate - expectedStartDate
    expected = {
      'startDate': expectedStartDate,
      'deltaDate': expectedDeltaDate,
      'endDate':  expectedEndDate,
      'startWindow': expectedStartWindow,
      'deltaWindow': expectedDeltaWindow,
      'endWindow': expectedStartWindow+expectedDeltaWindow
      }

    ignore = cron_util.getDateAndWindow(config,self.tableName,None,self.connection.cursor(),logger,**kwargs)
    for k,v in expected.items():
      assert v == config.get(k), "but %s: Expected %s, got %s"%(k,v,config.get(k))




