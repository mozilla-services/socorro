# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
This is a named cursor proof of concept, flanged together quickly to use nose (see rename below) because all the
bits and pieces were lying around ready when I wrote it. I checked it in because someday, maybe, we'll want to do
another proof, if psycopg library gets smarter about fetchmany(). See one of the below (mirrors) for details:
http://www.velocityreviews.com/forums/t509431-psycopg2-amp-large-result-set.html
http://bytes.com/groups/python/652577-psycopg2-large-result-set
In essence: you can use fetchmany, but only with a named cursor, and only useful if you specify the size.
"""
import copy
import datetime as dt
import errno
import logging
import os
import psycopg2
import time
import unittest
from nose.tools import *

import socorro.lib.ConfigurationManager as configurationManager
import socorro.database.database as sdatabase

from socorro.lib.datetimeutil import UTC

from   socorro.unittest.testlib.testDB import TestDB
import socorro.unittest.testlib.dbtestutil as dbtestutil
import socorro.unittest.testlib.util as tutil
import cronTestconfig as testConfig

def setup_module():
  tutil.nosePrintModule(__file__)

class Me:
  pass
me = None

def addReportData(cursor, dataToAdd):
  # dataToAdd is [{},...] for dictionaries of values as shown in sql below
  sql = """INSERT INTO reports
     (uuid,     client_crash_date,    date_processed,    product,    version,    build,    url,    install_age,    last_crash,   uptime,
      email,    os_name,    os_version,
      user_id,                                            -- ignored (no longer collected)
      user_comments,
      app_notes, distributor, distributor_version) VALUES -- These are ignored for testing purposes
    (%(uuid)s,%(client_crash_date)s,%(date_processed)s,%(product)s,%(version)s,%(build)s,%(url)s,%(install_age)s,%(last_crash)s,%(uptime)s,
    %(email)s,%(os_name)s,%(os_version)s,
      0,
    %(user_comments)s,
    %(app_notes)s,        %(distributor)s,          %(distributor_version)s)"""

  cursor.executemany(sql,dataToAdd)
  cursor.connection.commit()

def createMe():
  global me
  if not me:
    me = Me()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName = "Testing TopCrashers")
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass
  me.logFilePathname = me.config.logFilePathname
  logfileDir = os.path.split(me.config.logFilePathname)[0]
  try:
    os.makedirs(logfileDir)
  except OSError,x:
    if errno.EEXIST != x.errno: raise
  f = open(me.config.logFilePathname,'w')
  f.close()

  fileLog = logging.FileHandler(me.logFilePathname, 'a')
  fileLog.setLevel(logging.DEBUG)
  fileLogFormatter = logging.Formatter(me.config.get('logFileLineFormatString','%(asctime)s %(levelname)s - %(message)s'))
  fileLog.setFormatter(fileLogFormatter)
  me.logger = logging.getLogger('cron_test')
  me.logger.setLevel(logging.DEBUG)
  me.logger.addHandler(fileLog)
  me.database = sdatabase.Database(me.config)
  #me.dsn = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % (me.config)

class TestNamedCursor(unittest.TestCase):
  def setUp(self):
    global me
    if not me:
      createMe()
    self.testDB = TestDB()
    self.testDB.removeDB(me.config, me.logger)
    self.testDB.createDB(me.config, me.logger)
    #self.connection = psycopg2.connect(me.dsn)
    self.connection = me.database.connection()

  def tearDown(self):
    global me
    self.testDB.removeDB(me.config,me.logger)
    self.connection.close()

  def reportDataGenerator(self,sizePerDay,numDays):
    idGen = dbtestutil.moreUuid()
    initialDate = dt.datetime(2008,1,1,1,1,1,1,tzinfo=UTC)
    currentDate = dt.datetime(2008,1,1,1,1,1,1,tzinfo=UTC)
    milli5 = dt.timedelta(milliseconds=5)
    milli10 = dt.timedelta(milliseconds=10)
    buildStrings = ['200712312355','200712302355','200712292355']
    buildDates =   [dt.datetime(2007,12,31,23,55,tzinfo=UTC),dt.datetime(2007,12,30,23,55,tzinfo=UTC),dt.datetime(2007,12,29,23,55,tzinfo=UTC)]
    osNameVersions = [('Windows NT','6.6.6'),('Windows NT','6.6.6'),('Windows','v.v.v'),('Windows','v.v.v'),('Windows','v.v.v'),('Windows','v.v.v'),
                      ('Mac OS X','10.5.5'),('Mac OS X','10.5.6'),('Mac OS X','10.5.6'),
                      ('Linux','10.10.10'),('Linux','10.10.11'),
                      ]
    insData = []
    for dummyDays in range(numDays):
      count = 0
      while count < sizePerDay:
        os_name,os_version = osNameVersions[count % len(osNameVersions)]
        data = {
          'uuid':idGen.next(),
          'client_crash_date':currentDate,
          'date_processed': currentDate+milli5,
          'product': 'foxy',
          'version': '3.6.9b2',
          'build': buildStrings[count%len(buildStrings)],
          'url':'http://www.woo.wow/weee',
          'install_age':89000,
          'last_crash':0,
          'uptime':88000,
          'email':None,
          'os_name': os_name,
          'os_version': os_version,
          #'build_date': buildDates[count%len(buildDates)],
          'user_comments': 'oh help',
          'app_notes':"",
          'distributor':"",
          'distributor_version':"",
          }
        insData.append(data)
        if not count%(3):
          currentDate += milli10
        count += 1
      currentDate = initialDate+dt.timedelta(days=1)
    cursor = self.connection.cursor()
    addReportData(cursor,insData)

  def build1000(self): #testBuild1000(self):
    self.reportDataGenerator(1000,10)
    ncursor = self.connection.cursor('myCursor')
    ncursor.execute('SELECT id,uuid,client_crash_date,date_processed from reports')
    try:
      while True:
        data = ncursor.fetchmany(512)
        if data and len(data):
          print data[0][0],len(data)
        else:
          print "Broke: %s"%(data)
          break
    finally:
      self.connection.commit()
