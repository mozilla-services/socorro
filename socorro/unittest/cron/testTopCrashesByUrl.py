import copy
import datetime
import errno
import logging
import os
import psycopg2
import time

import socorro.unittest.testlib.util as tutil
import socorro.unittest.testlib.dbtestutil as dbtutil
from   socorro.unittest.testlib.testDB import TestDB

import socorro.lib.ConfigurationManager as configurationManager
import socorro.database.cachedIdAccess as socorro_cia

import cronTestconfig as testConfig

import socorro.cron.topCrashesByUrl as tcbu

class Me: pass
me = None

def setup_module():
  global me
  tutil.nosePrintModule(__file__)
  if me:
    return
  me = Me()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing TCByUrl')
  tcbu.logger.setLevel(logging.DEBUG)
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass
  me.logFilePathname = me.config.logFilePathname
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
  tcbu.logger.addHandler(fileLog)
  socorro_cia.logger.addHandler(fileLog)
  me.logger = tcbu.logger
  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)

class TestTopCrashesByUrl:
  def setUp(self):
    global me
    self.logger = me.logger
    self.connection = psycopg2.connect(me.dsn)
    self.testDB = TestDB()
    self.testDB.removeDB(me.config,self.logger)
    self.testDB.createDB(me.config,self.logger)

  def tearDown(self):
    self.testDB.removeDB(me.config,self.logger)
    socorro_cia.clearCache()

  def testConstructor(self):
    """testTopCrashesByUrl:TestTopCrashesByUrl.testConstructor(self)"""
    global me
    config = copy.copy(me.config)
    t = tcbu.TopCrashesByUrl(config)
    
    assert 1 == t.configContext['minimumHitsPerUrl']
    assert 500 == t.configContext['maximumUrls']
    assert tcbu.logger.name
    assert 'date_processed' == t.configContext.get('dateColumn')
    config = copy.copy(me.config)
    config['minimumHitsPerUrl'] = 2
    config['maximumUrls'] = 100
    config['logger'] = self.logger
    t = tcbu.TopCrashesByUrl(config)
    assert 2 == t.configContext.get('minimumHitsPerUrl')
    assert 100 == t.configContext.get('maximumUrls')
    assert self.logger == t.configContext.get('logger')
    halfDay = datetime.timedelta(hours=12)
    config = copy.copy(me.config)
    t = tcbu.TopCrashesByUrl(config, minimumHitsPerUrl=3, maximumUrls=50,deltaWindow =halfDay)
    assert 3 == t.configContext.get('minimumHitsPerUrl')
    assert 50 == t.configContext.get('maximumUrls')
    assert halfDay == t.configContext.get('deltaWindow')

  def testCountCrashesByUrlInWindow(self):
    """testTopCrashesByUrl:TestTopCrashesByUrl.testCountCrashesByUrlInWindow(self):"""
    global me
    cursor = self.connection.cursor()
    dbtutil.fillReportsTable(cursor,createUrls=True,multiplier=2,signatureCount=83) # just some data...
    self.connection.commit()
    config = copy.copy(me.config)

    # test /w/ 'normal' params
    t = tcbu.TopCrashesByUrl(config)
    startWindow = datetime.datetime(2008,1,1)
    deltaWindow = datetime.timedelta(days=1)
    endWindow = startWindow + deltaWindow
    data = t.countCrashesByUrlInWindow(startWindow = startWindow, deltaWindow = deltaWindow)
    # the following are JUST regression tests: The data has been only very lightly examined to be sure it makes sense.
    assert 24 ==  len(data), 'This is (just) a regression test. Did you change the data somehow? (%s)'%len(data)
    for d in data:
      assert 1 == d[0]
    # test /w/ small maximumUrls
    config = copy.copy(me.config)
    t = tcbu.TopCrashesByUrl(config, maximumUrls=50)
    data = t.countCrashesByUrlInWindow(startWindow = datetime.datetime(2008,1,1), endWindow = endWindow)
    assert 24 == len(data), 'This is (just) a regression test. Did you change the data somehow? (%s)'%len(data)
    for d in data:
      assert 1 == d[0]
    # test /w/ minimumHitsPerUrl larger
    config = copy.copy(me.config)
    t = tcbu.TopCrashesByUrl(config, minimumHitsPerUrl=2)
    data = t.countCrashesByUrlInWindow(startWindow = datetime.datetime(2008,1,1),endWindow = endWindow)
    assert 24 == len(data), len(data)
    for d in data:
      assert 1 == d[0]
    
    # test /w/ shorter window
    config = copy.copy(me.config)
    halfDay = datetime.timedelta(hours=12)
    t = tcbu.TopCrashesByUrl(config, deltaWindow = halfDay)
    data = t.countCrashesByUrlInWindow(startWindow = datetime.datetime(2008,1,1))
    assert 12 == len(data), 'This is (just) a regression test. Did you change the data somehow? (%s)'%len(data)
    for d in data:
      assert 1 == d[0]

    # test a different day, to be sure we get different data
    config = copy.copy(me.config)
    t = tcbu.TopCrashesByUrl(config)
    data = t.countCrashesByUrlInWindow(startWindow = datetime.datetime(2008,1,11),deltaWindow=deltaWindow)
    assert 57 == len(data), 'This is (just) a regression test. Did you change the data somehow? (%s)'%len(data)
    for d in data[:3]:
      assert 2 == d[0]
    for d in data[3:]:
      assert 1 == d[0]

  def testSaveData(self):
    """
    testTopCrashesByUrl:TestTopCrashesByUrl.testSaveData(slow=2)
    This is a reasonably realistic amount of time (about 1.5 seconds) to handle about 150 reports
    """
    global me
    cursor = self.connection.cursor()

    ## Set up 
    dbtutil.fillReportsTable(cursor,createUrls=True,multiplier=2,signatureCount=83) # just some data...
    self.connection.commit()
    # ... now assure some duplicates
    sqls = "SELECT uuid, client_crash_date, install_age, last_crash, uptime, date_processed, success, signature, url, product, version, os_name, os_version from reports where date_processed >= '2008-01-01' and date_processed < '2008-01-02' LIMIT 4"
    cursor.execute(sqls)
    self.connection.rollback() # db not altered
    rows3 = cursor.fetchall()
    add11 = datetime.timedelta(seconds=1,microseconds=1000)
    addData = []
    for i in range(3):
      r = list(rows3[i])
      r[0] = r[0].replace('-dead-','-f00f-')
      r[1] += add11
      r[2] += 1
      r[3] += 1
      r[7] = rows3[i+1][7]
      addData.append(r)
      r[0] = r[0].replace('-f00f-','-fead-')
      r[1] += add11
      r[2] += 1
      r[3] += 1
      r[7] = 'js_blatherskytes'
      addData.append(r)
    sqli = """INSERT INTO reports
                (uuid, client_crash_date, install_age, last_crash, uptime, date_processed, success, signature, url, product, version, os_name, os_version)
          VALUES(%s,   %s,                %s,          %s,         %s,     %s,             %s,      %s,        %s,  %s,      %s,      %s,      %s)"""
    addData.extend([
      ['b965de73-ae90-b936-deaf-03ae20081225','2007-12-31 23:59:50',9000,110,222,'2008-01-01 11:12:13',True,'UserCallWinProcCheckWow','http://www.mozilla.org/projects/minefield/a','Firefox','3.0.9','Windows NT','5.1.2600 Service Pack 2'],
      ['b965de73-ae90-b935-deaf-03ae20081225','2007-12-31 23:59:40',9009,220,333,'2008-01-01 11:12:14',True,'UserCallWinProcCheckWow','http://yachats/uncwiki/LarsLocalPortal/b',   'Firefox','3.0.9','Windows NT','5.1.2600 Service Pack 2'],
      ])
    cursor.executemany(sqli,addData)
    self.connection.commit()
    config = copy.copy(me.config)
    startWindow = datetime.datetime(2008,1,1)
    deltaWindow = datetime.timedelta(days=1)

    ## On your mark...
    t = tcbu.TopCrashesByUrl(config)
    data = t.countCrashesByUrlInWindow(startWindow = startWindow, deltaWindow = deltaWindow)

    ## assure we have an empty playing field
    cursor.execute("SELECT COUNT(*) from top_crashes_by_url")
    self.connection.rollback()
    assert 0 == cursor.fetchone()[0]

    ## Call the method
    t.saveData(startWindow,data)

    # expect 99 rows
    cursor.execute("SELECT COUNT(id) from top_crashes_by_url")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 35 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)
    # expect 80 distinct urls
    cursor.execute("SELECT COUNT(distinct urldims_id) from top_crashes_by_url")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 21 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("SELECT count from top_crashes_by_url where count > 1 order by count")
    self.connection.rollback()
    data = cursor.fetchall()
    assert [(2,),(2,),(2,)] == data, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(str(data))

    cursor.execute("SELECT COUNT(top_crashes_by_url_id) from top_crashes_by_url_signature")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 38 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("SELECT COUNT(distinct top_crashes_by_url_id) from top_crashes_by_url_signature")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 35 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    # Expect 3 rows with sums of 2 and three rows with counts of 2, none with both
    cursor.execute("SELECT count, COUNT(top_crashes_by_url_id) AS sum FROM top_crashes_by_url_signature GROUP BY top_crashes_by_url_id, count ORDER BY sum DESC, count DESC LIMIT 6")
    self.connection.rollback()
    data = cursor.fetchall()
    assert 6 == len(data)
    assert [(1, 2L), (1, 2L), (1, 2L), (1, 1L), (1, 1L), (1, 1L)] == data, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(str(data))

    cursor.execute("SELECT count(*) from topcrashurlfactsreports")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 38 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)
    
    cursor.execute("SELECT COUNT(topcrashurlfacts_id) AS sum FROM topcrashurlfactsreports GROUP BY topcrashurlfacts_id ORDER BY sum DESC LIMIT 7")
    self.connection.rollback()
    data = cursor.fetchall()
    assert [(2L,), (2L,), (2L,), (1L,), (1L,), (1L,), (1L,)] == data, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(str(data))

  def testSaveTruncatedData(self):
    """
    testTopCrashesByUrl:TestTopCrashesByUrl.testSaveTruncatedData(slow=2)
    This is a reasonably realistic amount of time (about 1.5 seconds) to handle about 150 reports
    """
    global me
    cursor = self.connection.cursor()

    ## Set up 
    dbtutil.fillReportsTable(cursor,createUrls=True,multiplier=2,signatureCount=83) # just some data...
    self.connection.commit()
    # ... now assure some duplicates
    sqls = "SELECT uuid, client_crash_date, install_age, last_crash, uptime, date_processed, success, signature, url, product, version, os_name, os_version from reports where date_processed >= '2008-01-01' and date_processed < '2008-01-02' LIMIT 4"
    cursor.execute(sqls)
    self.connection.rollback() # db not altered
    rows3 = cursor.fetchall()
    add11 = datetime.timedelta(seconds=1,microseconds=1000)
    addData = []
    for i in range(3):
      r = list(rows3[i])
      r[0] = r[0].replace('-dead-','-f00f-')
      r[1] += add11
      r[2] += 1
      r[3] += 1
      r[7] = rows3[i+1][7]
      addData.append(r)
      r[0] = r[0].replace('-f00f-','-fead-')
      r[1] += add11
      r[2] += 1
      r[3] += 1
      r[7] = 'js_blatherskytes'
      addData.append(r)
    sqli = """INSERT INTO reports
                (uuid, client_crash_date, install_age, last_crash, uptime, date_processed, success, signature, url, product, version, os_name, os_version)
          VALUES(%s,   %s,                %s,          %s,         %s,     %s,             %s,      %s,        %s,  %s,      %s,      %s,      %s)"""
    addData.extend([
      ['b965de73-ae90-b936-deaf-03ae20081225','2007-12-31 23:59:50',9000,110,222,'2008-01-01 11:12:13',True,'UserCallWinProcCheckWow','http://www.mozilla.org/projects/minefield/a','Firefox','3.0.9','Windows NT','5.1.2600 Service Pack 2'],
      ['b965de73-ae90-b935-deaf-03ae20081225','2007-12-31 23:59:40',9009,220,333,'2008-01-01 11:12:14',True,'UserCallWinProcCheckWow','http://yachats/uncwiki/LarsLocalPortal/b',   'Firefox','3.0.9','Windows NT','5.1.2600 Service Pack 2'],
      ])
    cursor.executemany(sqli,addData)
    self.connection.commit()
    config = copy.copy(me.config)
    startWindow = datetime.datetime(2008,1,1)
    deltaWindow = datetime.timedelta(days=1)

    ## On your mark...
    t = tcbu.TopCrashesByUrl(config,truncateUrlLength=25)
    data = t.countCrashesByUrlInWindow(startWindow = startWindow, deltaWindow = deltaWindow)

    ## assure we have an empty playing field
    cursor.execute("SELECT COUNT(*) from top_crashes_by_url")
    self.connection.rollback()
    assert 0 == cursor.fetchone()[0]

    ## Call the method
    t.saveData(startWindow,data)

    # expect 99 rows
    cursor.execute("SELECT COUNT(id) from top_crashes_by_url")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 30 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)
    # expect 80 distinct urls
    cursor.execute("SELECT COUNT(distinct urldims_id) from top_crashes_by_url")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 17 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("SELECT count from top_crashes_by_url where count > 1 order by count")
    self.connection.rollback()
    data = cursor.fetchall()
    assert [(2,), (2,), (2,), (2,), (2,), (4,)] == data, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(str(data))

    cursor.execute("SELECT COUNT(top_crashes_by_url_id) from top_crashes_by_url_signature")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 38 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("SELECT COUNT(distinct top_crashes_by_url_id) from top_crashes_by_url_signature")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 30 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    # Expect 3 rows with sums of 2 and three rows with counts of 2, none with both
    cursor.execute("SELECT count, COUNT(top_crashes_by_url_id) AS sum FROM top_crashes_by_url_signature GROUP BY top_crashes_by_url_id, count ORDER BY sum DESC, count DESC LIMIT 6")
    self.connection.rollback()
    data = cursor.fetchall()
    assert 6 == len(data)
    assert [(1, 4L), (1, 2L), (1, 2L), (1, 2L), (1, 2L), (1, 2L)] == data, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(str(data))

    cursor.execute("SELECT count(*) from topcrashurlfactsreports")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 38 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)
    
    cursor.execute("SELECT COUNT(topcrashurlfacts_id) AS sum FROM topcrashurlfactsreports GROUP BY topcrashurlfacts_id ORDER BY sum DESC LIMIT 7")
    self.connection.rollback()
    data = cursor.fetchall()
    assert [(4L,), (2L,), (2L,), (2L,), (2L,), (2L,), (1L,)] == data, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(str(data))

  def testProcessDateInterval(self):
    """
    testTopCrashesByUrl:TestTopCrashesByUrl.testProcessDateInterval(slow=7)
    Takes a long time, first to set up the data (about 1.5 seconds), then to process it several times
    """
    global me
    cursor = self.connection.cursor()
    config = copy.copy(me.config)

    ## Set up 
    dbtutil.fillReportsTable(cursor,createUrls=True,multiplier=2,signatureCount=83) # just some data...
    self.connection.commit()
    t = tcbu.TopCrashesByUrl(config)
    ## assure we have an empty playing field
    cursor.execute("SELECT COUNT(*) from top_crashes_by_url")
    self.connection.rollback()
    assert 0 == cursor.fetchone()[0]
    t.processDateInterval(startDate = datetime.datetime(2008,1,1), endDate=datetime.datetime(2008,1,6))

    cursor.execute("SELECT COUNT(id) from top_crashes_by_url")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 35 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("SELECT COUNT(*) from top_crashes_by_url_signature")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 38 ==  count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("SELECT COUNT(*) from topcrashurlfactsreports")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 38 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("delete from top_crashes_by_url; delete from top_crashes_by_url_signature; delete from topcrashurlfactsreports")
    self.connection.commit()
    t = tcbu.TopCrashesByUrl(copy.copy(me.config))
    t.processDateInterval(startDate = datetime.datetime(2008,1,4), endDate=datetime.datetime(2008,1,8))

    cursor.execute("SELECT COUNT(id) from top_crashes_by_url")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 31 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("SELECT COUNT(*) from top_crashes_by_url_signature")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 32 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("SELECT COUNT(*) from topcrashurlfactsreports")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 32 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("delete from top_crashes_by_url; delete from top_crashes_by_url_signature; delete from topcrashurlfactsreports")
    self.connection.commit()

    t = tcbu.TopCrashesByUrl(copy.copy(me.config))
    t.processDateInterval(startDate = datetime.datetime(2008,1,1), endDate=datetime.datetime(2008,3,3))
    
    cursor.execute("SELECT COUNT(id) from top_crashes_by_url")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 483 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("SELECT COUNT(*) from top_crashes_by_url_signature")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 514 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)

    cursor.execute("SELECT COUNT(*) from topcrashurlfactsreports")
    self.connection.rollback()
    count = cursor.fetchone()[0]
    assert 514 == count, 'This is (just) a regression test. Did you change the data somehow? (%s)'%(count)


    
