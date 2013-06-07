# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# XXX Set to be deprecated in favor of socorro/external/postgresql/models.py

import socorro.database.cachedIdAccess as cia

import errno
import logging
import os
import time

from nose.tools import *
from nose.plugins.skip import SkipTest

import psycopg2

import dbTestconfig as testConfig
from   socorro.unittest.testlib.testDB import TestDB
import socorro.lib.ConfigurationManager as configurationManager

class Me: # Class 'Me' is just a way to say 'global' once per method
  pass
me = None
# Note: without setup_module and teardown_module we get weird double, treble and more multiple (logging of) calls
# to testDB.removeDB() and testDB.createDB using nosetests as the driver. I have no idea, but this is a pragmatic
# work around: do setup and teardown at the (spelled) module level.

def setup_module():
  global me
  if me:
    return
  me = Me()
  me.testDB = TestDB()
  me.config = configurationManager.newConfiguration(configurationModule = testConfig, applicationName='TestingCachedIdAccess')
  myDir = os.path.split(__file__)[0]
  if not myDir: myDir = '.'
  replDict = {'testDir':'%s'%myDir}
  for i in me.config:
    try:
      me.config[i] = me.config.get(i)%(replDict)
    except:
      pass
  cia.logger.setLevel(logging.DEBUG)
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
  fileLogFormatter = logging.Formatter('%(asctime)s %(levelname)s - %(message)s')
  fileLog.setFormatter(fileLogFormatter)
  cia.logger.addHandler(fileLog)
  me.logger = cia.logger
  me.dsn = "host=%s dbname=%s user=%s password=%s" % (me.config.databaseHost,me.config.databaseName,
                                                      me.config.databaseUserName,me.config.databasePassword)

def teardown_module():
  me.testDB = None

class TestCachedIdAccess:
  def setUp(self):
    global me
    assert me, 'DAMN! what happened?!'
    # Remove/Create is being tested elsewhere via models.py & setupdb_app.py now
    me.testDB.removeDB(me.config,me.logger)
    me.testDB.createDB(me.config,me.logger)
    self.connection = psycopg2.connect(me.dsn)

  def tearDown(self):
    global me
    sql = 'DELETE from %s'
    cursor = self.connection.cursor()
    me.testDB.removeDB(me.config,me.logger)

  def testCreateProductRelease(self):
    """
    TestCachedIdAccess:testCreateProductRelease(self):
     for a bunch of possible version strings, check that the calculated release name is appropriate
    """
    data = [
      # test for major and fails major
      ('a.b.c',None),
      ('presumptive.behavior',None),
      ('0.0','major'),
      ('3.4','major'),
      ('1.2.3','major'),
      ('0.123456','major'),
      ('123456.0','major'),
      ('1.2.3.4.5.6.7.8.9.10','major'),
      ('a.2.3.4.5.6.7.8.9.10',None),
      ('1.2.3.4.5.b.7.8.9.10',None),
      ('1.2.3.4.5.6.7.8.9.a',None),
      ('1.2.3.4.5.6.7.8.9.b',None),
      ('1.',None),
      ('1.2.',None),
      ('1.2.3.',None),
      ('1,2',None),
      ('1..2.3',None),
      ('0',None),
      ('5',None),
      ('12345',None),
      ('.1',None),
      ('.1.2',None),
      ('.1.2.3',None),
      ('.1.2.3.',None),

      # development and fails release
      ('1.2a','development'),
      ('1.2a1','development'),
      ('1.2.3.4.5.6.7.8.9a','development'),
      ('1.2.3.4.5.6.7.8.9a9','development'),
      ('1.1234567a','development'),
      ('1.1234567a999','development'),
      ('1.2b','development'),
      ('1.2b2','development'),
      ('1.1234567b','development'),
      ('1.1234567b2233','development'),
      ('1.2.3.4.5.6.7.8.9b','development'),
      ('1.2.3.4.5.6.7.8.9b9','development'),
      ('1.a',None),
      ('1.a3',None),
      ('1.b',None),
      ('1.b4',None),
      ('1.2.3c',None),
      ('1.2.3c5',None),
      ('a1.2.3',None),
      ('b1.2.3',None),
      #('1.2.3.4.5.6.7.8.9.a',None), # done above

      # milestone and fails milestone
      ('3.1pre','milestone'),
      ('3.1apre','milestone'),
      ('3.1bpre','milestone'),
      ('3.1a1pre','milestone'),
      ('3.1b99pre','milestone'),
      ('pre3.1',None),
      ('pre3.1a',None),
      ('3.1prea',None),
      ('3.1preb',None),
      ('3.1apre1',None),
      ('3.1prea1',None),
      ('3.1.pre',None),
      ]
    for trial,expect in data:
      got = cia.createProductRelease(trial)
      assert expect == got, "For '%s': Expected '%s', got '%s'"%(trial,expect,got)

  #def testConstructor(self): # Fully tested in testClearAndInitializeCache()

  def testShrinkIdCache(self):
    idCache = dict((x,x) for x in range(7))
    idCount = dict((x,10-x) for x in range(7))
    # expect the first half of the map
    expectCache = dict((x,x) for x in range(4))
    expectCount = dict((x,1) for x in range(4))
    gotCache, gotCount = cia.shrinkIdCache(idCache,idCount)
    assert expectCache == gotCache, 'Expect %s, got %s'%(expectCache,gotCache)
    assert expectCount == gotCount, 'Expect %s, got %s'%(expectCount,gotCount)
    # expect the same if the key to save is already in the saved part
    gotCache, gotCount = cia.shrinkIdCache(idCache,idCount,oneKeyToSave=2)
    assert expectCache == gotCache, 'Expect %s, got %s'%(expectCache,gotCache)
    assert expectCount == gotCount, 'Expect %s, got %s'%(expectCount,gotCount)
    # expect the key and its count if key to save would have been discarded
    gotCache, gotCount = cia.shrinkIdCache(idCache,idCount,oneKeyToSave=5)
    expectCache[5] = 5
    expectCount[5] = 1
    assert expectCache == gotCache, 'Expect %s, got %s'%(expectCache,gotCache)
    assert expectCount == gotCount, 'Expect %s, got %s'%(expectCount,gotCount)
    # expect reverse, just to be sure
    idCount = dict((x,10+x) for x in range(7))
    expectCache = dict((x,x) for x in range(3,7))
    expectCount = dict((x,1) for x in range(3,7))
    gotCache, gotCount = cia.shrinkIdCache(idCache,idCount)
    assert expectCache == gotCache, 'Expect %s, got %s'%(expectCache,gotCache)
    assert expectCount == gotCount, 'Expect %s, got %s'%(expectCount,gotCount)
    assert_raises(KeyError,cia.shrinkIdCache,idCache,idCount,99)

  def testAssureAndGetId(self):
    createSql = """CREATE TABLE moolah (
    id serial not null primary key,
    n text NOT NULL,
    o text NOT NULL,
    p text
    );
    CREATE INDEX moolah_no ON moolah (n,o);
    """
    dropSql = "DROP TABLE IF EXISTS moolah CASCADE"
    delSql  = "DELETE FROM moolah"
    getSqlk = "SELECT id from moolah WHERE n=%s and o=%s"
    putSqlk = "INSERT INTO moolah (n,o) VALUES(%s,%s)"
    getSqld = "SELECT id from moolah WHERE n=%(n)s and o=%(o)s"
    putSqld = "INSERT INTO moolah (n,o,p) VALUES(%(n)s,%(o)s,%(p)s)"
    checkSql= "SELECT id,n,o,p from moolah"
    countSql= "SELECT count(id) from moolah"
    cursor = self.connection.cursor()
    try:
      # setup
      cursor.execute(createSql)
      self.connection.commit()
      #end of setup
      idc = cia.IdCache(cursor)
      ktests = [
        (('n','o',),1),
        (('nn','oo'),2),
        (('nn','o'),3),
        (('nn','oo'),2),
        (('nn','o'),3),
        ]

      dtests = [
        (('n','o',),{'n':'n','o':'o','p':'p'},1),
        (('nn','oo'),{'n':'nn','o':'oo','p':'pp'},2),
        (('nn','o'),{'n':'nn','o':'o','p':'p'},3),
        (('nn','oo'),{'n':'nn','o':'oo','p':'pp'},2),
        (('nn','o'),{'n':'nn','o':'o','p':'pp'},3),
        ]

      # test with key and no cache
      # - the database gets each (and only) new key
      # - the ids are as expected
      idCache = None
      idCount = None
      idSet = set()
      rowCount = 0
      for v in ktests:
        id = idc.assureAndGetId(v[0],'moolah',getSqlk,putSqlk,idCache,idCount)
        if not id in idSet:
          rowCount += 1
        idSet.add(id)
        assert v[1] == id, 'Expected %s, got %s'%(v[1],id)
        cursor.execute(checkSql)
        data = cursor.fetchall()
        self.connection.commit()
        assert (v[1],v[0][0],v[0][1], None) in data
        assert len(data) == rowCount
      assert idCache == idCount
      assert idCache == None

      cursor.execute(delSql)
      self.connection.commit()

      # test with key and full cache:
      # - know the id from the cache
      # - the database isn't updated
      idCache = {('n','o'):23, ('nn','oo'):24, ('nn','o'):25}
      idCount = {('n','o'):5, ('nn','oo'):10, ('nn','o'):10}
      testIdCount = {('n','o'):5, ('nn','oo'):10, ('nn','o'):10}
      for v in ktests:
        id = idc.assureAndGetId(v[0],'moolah',getSqlk,putSqlk,idCache,idCount)
        assert idCache.get(v[0]) == id
        testIdCount[v[0]] += 1
        cursor.execute(countSql)
        self.connection.commit()
        count = cursor.fetchone()
        assert 0 == count[0]
      assert testIdCount == idCount

      cursor.execute(dropSql)
      cursor.execute(createSql)
      self.connection.commit()
      # test with key and initially empty cache:
      idSet = set()
      rowCount = 0
      idCache = {}
      idCount = {('n','o'):5, ('nn','oo'):10, ('nn','o'):10}
      testIdCount = {('n','o'):0, ('nn','oo'):0, ('nn','o'):0}
      for v in ktests:
        id = idc.assureAndGetId(v[0],'moolah',getSqlk,putSqlk,idCache,idCount)
        if not id in idSet:
          rowCount += 1
        idSet.add(id)
        assert idCache.get(v[0]) == id
        assert v[1] == id
        testIdCount[v[0]] += 1
        cursor.execute(countSql)
        self.connection.commit()
        count = cursor.fetchone()
        assert rowCount == count[0]
      assert testIdCount == idCount

      cursor.execute(dropSql)
      cursor.execute(createSql)
      self.connection.commit()
      # test with dictKey and full cache:
      # - know the id from the cache
      # - the database isn't updated
      idCache = {('n','o'):23, ('nn','oo'):24, ('nn','o'):25}
      idCount = {('n','o'):5, ('nn','oo'):10, ('nn','o'):10}
      testIdCount = {('n','o'):5, ('nn','oo'):10, ('nn','o'):10}
      for v in dtests:
        id = idc.assureAndGetId(v[0],'moolah',getSqld,putSqld,idCache,idCount,dkey=v[1])
        assert idCache.get(v[0]) == id
        testIdCount[v[0]] += 1
        cursor.execute(countSql)
        self.connection.commit()
        count = cursor.fetchone()
        assert 0 == count[0]
      assert testIdCount == idCount

      cursor.execute(dropSql)
      cursor.execute(createSql)
      self.connection.commit()
      # test with dictKey and initially empty cache:
      idSet = set()
      rowCount = 0
      idCache = {}
      idCount = {('n','o'):5, ('nn','oo'):10, ('nn','o'):10}
      testIdCount = {('n','o'):0, ('nn','oo'):0, ('nn','o'):0}
      for v in dtests:
        id = idc.assureAndGetId(v[0],'moolah',getSqld,putSqld,idCache,idCount,dkey=v[1])
        if not id in idSet:
          rowCount += 1
        idSet.add(id)
        assert idCache.get(v[0]) == id
        assert v[2] == id
        testIdCount[v[0]] += 1
        cursor.execute(countSql)
        self.connection.commit()
        count = cursor.fetchone()
        assert rowCount == count[0]
      assert testIdCount == idCount

    finally:
      # teardown
      cursor.execute(dropSql)
      self.connection.commit()

  def testGetAppropriateOsVersion(self):
    cursor = self.connection.cursor()
    idc = cia.IdCache(cursor)
    testList = [
      (('','5.1.2600 SP2'),'5.1.2600 SP2'),
      (('Windows NT',''),''),
      (('Windows NT','5.1.2600 SP2'),'5.1.2600 SP2'),
      (('Windows NT','5.1.2600 SP3'),'5.1.2600 SP3'),
      (('Windows','5.1.2600 SP2'),'5.1.2600 SP2'),
      (('Windows NT','5.1.2600 SP3'),'5.1.2600 SP3'),
      (('Linux', '0.0.0 Linux 1.2.3 i586 Linux'),'1.2.3 i586'),
      (('Linux', '0.0.0 Linux 2.4.6_flitteration x86_64 Linux'),'2.4.6 x86_64'),
      (('Linux', '0.0.0 Linux 2.4.6.flapitation x86_64 Linux'),'2.4.6 x86_64'),
      (('Linux', '0.0.0 Linux 2.4.6.flapitation-very-long'),'2.4.6 ?arch?'),
      (('Linux', '0.0.0 Linux 2.4.6.flapitation-very-long x86_6'),'2.4.6 ?arch?'),
      (('Linux', '0.0.0 Linux 2.4.6.flapitation-very-very-very-long-really'),'2.4.6 ?arch?'),
      (('Linux', '0.0.0 Linux 1.2.3 i586 Linux'),'1.2.3 i586'),
      (('Linux', '1.2.3 i686'),''),
      (('Namby', 'wiggle room'),'wiggle room'),
      (('Linux', 'Linux 1.2.3 i586 Linux'),''),
      (('Linux', '0.0.0 Linux non-numeric-version-string i586 Linux'),''),
      ]
    for testCase in testList:
      got = idc.getAppropriateOsVersion(*testCase[0])
      assert testCase[1] == got,'From "%s": Expected "%s", got "%s"'%(testCase[0][1],testCase[1],got)

