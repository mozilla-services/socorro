# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import os
import socorro.unittest.testlib.dbtestutil as dbtu

import socorro.lib.psycopghelper as psycopghelper
import socorro.lib.ConfigurationManager as configurationManager
import socorro.database.postgresql as db_postgresql
import socorro.database.schema as db_schema
import socorro.database.database as sdatabase

from socorro.lib.datetimeutil import UTC, utc_now

from nose.tools import *
from socorro.unittest.testlib.testDB import TestDB
import libTestconfig as testConfig
import socorro.unittest.testlib.createJsonDumpStore as createJDS

import psycopg2

import datetime as dt
import errno
import logging
import os
import re
import time

logger = logging.getLogger()

class Me:  pass
me = None

def setup_module():
  global me
  if me:
    return
  me = Me()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='Testing dbtestutil')
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass

  logger.setLevel(logging.DEBUG)
  logFilePathname = me.config.logFilePathname
  logfileDir = os.path.split(me.config.logFilePathname)[0]
  try:
    os.makedirs(logfileDir)
  except OSError,x:
    if errno.EEXIST != x.errno: raise
  f = open(me.config.logFilePathname,'w')
  f.close()

  fileLog = logging.FileHandler(logFilePathname, 'a')
  fileLog.setLevel(logging.DEBUG)
  fileLogFormatter = logging.Formatter(me.config.logFileLineFormatString)
  fileLog.setFormatter(fileLogFormatter)
  logger.addHandler(fileLog)
  me.database = sdatabase.Database(me.config)
  me.connection = me.database.connection()
  #me.dsn = "host=%(databaseHost)s dbname=%(databaseName)s user=%(databaseUserName)s password=%(databasePassword)s" % (me.config)
  #me.connection = psycopg2.connect(me.dsn)
  me.testDB = TestDB()
  # Remove/Create is being tested elsewhere via models.py & setupdb_app.py now
  me.testDB.removeDB(me.config,logger)
  me.testDB.createDB(me.config,logger)

def teardown_module():
  # Remove/Create is being tested elsewhere via models.py & setupdb_app.py now
  me.testDB.removeDB(me.config,logger)
  me.connection.close()
  if os.path.isfile(me.config.logFilePathname):
    os.remove(me.config.logFilePathname)

# this was a bad test in that it relies on the datetime in the database to be
# in sync with the datetime on the test machine
#def testDatetimeNow():
  #global me
  #cursor = me.connection.cursor()
  #before = dt.datetime.now()
  #time.sleep(.01)
  #got = dbtu.datetimeNow(cursor)
  #time.sleep(.01)
  #after = dt.datetime.now()
  #assert before < got and got < after, "but\nbefore:%s\ngot:   %s\nafter: %s"%(before,got,after)

def testMoreUuid():
  m = {'hexD':'[0-9a-fA-F]'}
  p = '^%(hexD)s{8}-%(hexD)s{4}-%(hexD)s{4}-%(hexD)s{4}-%(hexD)s{12}$'%m
  rep = re.compile(p)
  gen = dbtu.moreUuid()
  seen = set()
  # surely no test set has more than 150K uuids... and we want to run in < 1 second
  for i in range(150000):
    d = gen.next()
    assert 36 == len(d)
    assert d not in seen
    assert rep.match(d)
    seen.add(d)

def _makeJobDetails(aMap):
  "This is a test, but it is also a setup for the next test, so it will run there, not alone"
  jdCount = {1:0,2:0,3:0,4:0}
  data = dbtu.makeJobDetails(aMap)
  for d in data:
    jdCount[d[2]] += 1
    assert '/' in d[0]
    assert d[1] in d[0]
  assert jdCount == aMap
  return data

def testMoreUrl():
  global me
  noneGen = dbtu.moreUrl(False)
  for i in range(100):
    assert None == noneGen.next()

  allGen = dbtu.moreUrl(True,0)
  setAll = set()
  for i in range(40000):
    setAll.add(allGen.next())
  assert 2001 > len(setAll)
  assert 1998 < len(setAll)

  someGen5 = dbtu.moreUrl(True,5)
  set5 = set()
  for i in range(100):
    set5.add(someGen5.next())
  assert 5 >= len(set5)

  someGen100 = dbtu.moreUrl(True,100)
  set100 = set()
  for i in range(500):
    set100.add(someGen100.next())
  assert 100 >= len(set100)

  tooGen = dbtu.moreUrl(True,40000)
  setToo = set()
  for i in range(40000):
    setToo.add(tooGen.next())
  assert setToo == setAll
