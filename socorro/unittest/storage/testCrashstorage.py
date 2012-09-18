# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock
import os
import sys
import re
try:
  import json
except ImportError:
  import simplejson as json

## WARNING: in next line, if you get
## ERROR: Failure: ImportError (No module named thrift)
## You can fix it by checking out https://socorro.googlecode.com/svn/trunk/thirdparty
## and adding .../thirdparty to your PYTHONPATH (or equivalent)
try:
  import socorro.storage.crashstorage as cstore
except ImportError,x:
  print>> sys.stderr,"""
## If you see "Failure: ImportError (No module named thrift) ... ERROR"
## * check out https://socorro.googlecode.com/svn/trunk/thirdparty
## * read .../thirdparty/README.txt
## * add .../thirdparty to your PYTHONPATH (or equivalent)
  """
  raise
import socorro.unittest.testlib.expectations as exp
import socorro.lib.util as util

import socorro.unittest.testlib.loggerForTest as loggerForTest

#def testRepeatableStreamReader():
  #expectedReadResult = '1234567890/n'
  #fakeStream = exp.DummyObjectWithExpectations('fakeStream')
  #fakeStream.expect('read', (), {}, expectedReadResult, None)
  #rsr = cstore.RepeatableStreamReader(fakeStream)
  #result = rsr.read()
  #assert result == expectedReadResult, '1st expected %s but got %s' % (expectedReadResult, result)
  #result = rsr.read()
  #assert result == expectedReadResult, '2nd expected %s but got %s' % (expectedReadResult, result)
  #result = rsr.read()
  #assert result == expectedReadResult, '3rd expected %s but got %s' % (expectedReadResult, result)

def testLegacyThrottler():
  config = util.DotDict()
  config.throttleConditions = [ ('alpha', re.compile('ALPHA'), 100),
                                ('beta',  'BETA', 100),
                                ('gamma', lambda x: x == 'GAMMA', 100),
                                ('delta', True, 100),
                                (None, True, 0)
                              ]
  config.minimalVersionForUnderstandingRefusal = { 'product1': '3.5', 'product2': '4.0' }
  config.neverDiscard = False
  thr = cstore.LegacyThrottler(config)
  expected = 5
  actual = len(thr.processedThrottleConditions)
  assert expected == actual, "expected thr.preprocessThrottleConditions to have length %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.0',
                         'alpha':'ALPHA',
                       })
  expected = False
  actual = thr.understandsRefusal(json1)
  assert expected == actual, "understand refusal expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'alpha':'ALPHA',
                       })
  expected = True
  actual = thr.understandsRefusal(json1)
  assert expected == actual, "understand refusal expected %d, but got %d instead" % (expected, actual)

  expected = cstore.LegacyThrottler.ACCEPT
  actual = thr.throttle(json1)
  assert expected == actual, "regexp throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.4',
                         'alpha':'not correct',
                       })
  expected = cstore.LegacyThrottler.DEFER
  actual = thr.throttle(json1)
  assert expected == actual, "regexp throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'alpha':'not correct',
                       })
  expected = cstore.LegacyThrottler.DISCARD
  actual = thr.throttle(json1)
  assert expected == actual, "regexp throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'beta':'BETA',
                       })
  expected = cstore.LegacyThrottler.ACCEPT
  actual = thr.throttle(json1)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'beta':'not BETA',
                       })
  expected = cstore.LegacyThrottler.DISCARD
  actual = thr.throttle(json1)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'gamma':'GAMMA',
                       })
  expected = cstore.LegacyThrottler.ACCEPT
  actual = thr.throttle(json1)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'gamma':'not GAMMA',
                       })
  expected = cstore.LegacyThrottler.DISCARD
  actual = thr.throttle(json1)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)

  json1 = util.DotDict({ 'ProductName':'product1',
                         'Version':'3.6',
                         'delta':"value doesn't matter",
                       })
  expected = cstore.LegacyThrottler.ACCEPT
  actual = thr.throttle(json1)
  assert expected == actual, "string equality throttle expected %d, but got %d instead" % (expected, actual)
    # phase 2 tests

  config = util.DotDict()
  config.throttleConditions = [
    ('*', lambda x: 'alpha' in x, None),
    ('*', lambda x: x['beta'] == 'BETA', 100),
  ]
  config.minimalVersionForUnderstandingRefusal = {
    'product1': '3.5',
    'product2': '4.0'
  }
  config.neverDiscard = True
  config.logger = mock.Mock()
  thr = cstore.LegacyThrottler(config)
  expected = 2
  actual = len(thr.processedThrottleConditions)
  assert expected == actual, \
    "expected thr.preprocessThrottleConditions to have length %d, but got " \
    "%d instead" % (expected, actual)

  raw_crash = util.DotDict({ 'ProductName':'product1',
                             'Version':'3.6',
                             'beta': 'ugh',
                             'alpha':"value doesn't matter",
                          })
  expected = cstore.LegacyThrottler.IGNORE
  actual = thr.throttle(raw_crash)
  assert expected == actual, \
    "IGNORE expected %d, but got %d instead" % \
    (expected, actual)

  raw_crash = util.DotDict({ 'ProductName':'product1',
                             'Version':'3.6',
                             'beta': 'ugh',
                             'delta':"value doesn't matter",
                          })
  expected = cstore.LegacyThrottler.DEFER
  actual = thr.throttle(raw_crash)
  assert expected == actual, \
    "DEFER expected %d, but got %d instead" % \
    (expected, actual)

  raw_crash = util.DotDict({ 'ProductName':'product1',
                             'Version':'3.6',
                             'beta': 'BETA',
                             'alpha':"value doesn't matter",
                          })
  expected = cstore.LegacyThrottler.IGNORE
  actual = thr.throttle(raw_crash)
  assert expected == actual, \
    "IGNORE expected %d, but got %d instead" % \
    (expected, actual)
  raw_crash = util.DotDict({ 'ProductName':'product1',
                             'Version':'3.6',
                             'beta': 'BETA',
                             'delta':"value doesn't matter",
                          })
  expected = cstore.LegacyThrottler.ACCEPT
  actual = thr.throttle(raw_crash)
  assert expected == actual, \
    "ACCEPT expected %d, but got %d instead" % \
    (expected, actual)


def testCrashStorageSystem__init__():
  d = util.DotDict()
  d.benchmark = False
  css = cstore.CrashStorageSystem(d)
  assert css.config == d, 'config not saved'

def testCrashStorageSystem_makeJsonDictFromForm():
  d = util.DotDict()
  d.dumpField = 'd'
  fakeValue = util.DotDict()
  fakeValue.value = 2
  f = util.DotDict()
  f.a = '1'
  f.b = fakeValue
  f.c = '3'
  f.d = '4'
  f.e = '5'
  expectedTime = '12:00:01'
  fakeTimeModule = exp.DummyObjectWithExpectations('fakeTimeModule')
  fakeTimeModule.expect('time', (), {}, expectedTime, None)
  css = cstore.CrashStorageSystem(d)
  resultJson = css.makeJsonDictFromForm(f, fakeTimeModule)
  assert resultJson.a == '1'
  assert resultJson.b == 2
  assert resultJson.c == '3'
  assert resultJson.e == '5'

def testCrashStorageSystem_save():
  css = cstore.CrashStorageSystem(util.DotDict({'logger': util.SilentFakeLogger()}))
  result = css.save_raw('fred', 'ethel', 'lucy')
  assert result == cstore.CrashStorageSystem.NO_ACTION

def testCrashStorageSystemForHBase___init__():
  d = util.DotDict()
  j = util.DotDict()
  d.hbaseHost = 'fred'
  d.hbasePort = 'ethel'
  d.hbaseTimeout = 9000
  j.root = d.hbaseFallbackFS = '.'
  d.throttleConditions = []
  j.maxDirectoryEntries = d.hbaseFallbackDumpDirCount = 1000000
  j.jsonSuffix = d.jsonFileSuffix = '.json'
  j.dumpSuffix = d.dumpFileSuffix = '.dump'
  j.dumpGID = d.hbaseFallbackdumpGID = 666
  j.dumpPermissions = d.hbaseFallbackDumpPermissions = 660
  j.dirPermissions = d.hbaseFallbackDirPermissions = 770
  j.logger = d.logger = util.SilentFakeLogger()
  fakeHbaseConnection = exp.DummyObjectWithExpectations('fakeHbaseConnection')
  fakeHbaseModule = exp.DummyObjectWithExpectations('fakeHbaseModule')
  fakeHbaseModule.expect('HBaseConnectionForCrashReports', (d.hbaseHost, d.hbasePort, d.hbaseTimeout), {"logger":d.logger}, fakeHbaseConnection, None)
  fakeHbaseConnection.expect('hbaseThriftExceptions', None, None, (), None)
  fakeHbaseModule.expect('NoConnectionException', None, None, hbc.NoConnectionException, None)
  fakeJsonDumpStore = exp.DummyObjectWithExpectations('fakeJsonDumpStore')
  fakeJsonDumpModule = exp.DummyObjectWithExpectations('fakeJsonDumpModule')
  fakeJsonDumpModule.expect('JsonDumpStorage', (), j, fakeJsonDumpStore, None)
  css = cstore.CrashStorageSystemForHBase(d, configPrefix='',
                                          hbaseClient=fakeHbaseModule,
                                          jsonDumpStorage=fakeJsonDumpModule)
  assert css.hbaseConnection == fakeHbaseConnection

def testCrashStorageSystemForHBase_save_1():
  """straight save into hbase with no trouble"""
  currentTimestamp = 'now'
  expectedDumpResult = '1234567890/n'

  jdict = util.DotDict({'ProductName':'FireFloozy', 'Version':'3.6', 'legacy_processing':1})

  d = util.DotDict()
  j = util.DotDict()
  d.hbaseHost = 'fred'
  d.hbasePort = 'ethel'
  d.hbaseTimeout = 9000
  j.root = d.hbaseFallbackFS = '.'
  d.throttleConditions = []
  j.maxDirectoryEntries = d.hbaseFallbackDumpDirCount = 1000000
  j.jsonSuffix = d.jsonFileSuffix = '.json'
  j.dumpSuffix = d.dumpFileSuffix = '.dump'
  j.dumpGID = d.hbaseFallbackdumpGID = 666
  j.dumpPermissions = d.hbaseFallbackDumpPermissions = 660
  j.dirPermissions = d.hbaseFallbackDirPermissions = 770
  d.logger = util.SilentFakeLogger()

  fakeHbaseConnection = exp.DummyObjectWithExpectations('fakeHbaseConnection')
  fakeHbaseConnection.expect('hbaseThriftExceptions', None, None, (), None)
  fakeHbaseConnection.expect('put_json_dump', ('uuid', jdict, expectedDumpResult), {"number_of_retries":2}, None, None)

  fakeHbaseModule = exp.DummyObjectWithExpectations('fakeHbaseModule')
  fakeHbaseModule.expect('HBaseConnectionForCrashReports', (d.hbaseHost, d.hbasePort, d.hbaseTimeout), {"logger":d.logger}, fakeHbaseConnection, None)
  fakeHbaseModule.expect('NoConnectionException', None, None, hbc.NoConnectionException, None)

  fakeJsonDumpStore = exp.DummyObjectWithExpectations('fakeJsonDumpStore')
  fakeJsonDumpModule = exp.DummyObjectWithExpectations('fakeJsonDumpModule')
  fakeJsonDumpModule.expect('JsonDumpStorage', (), j, fakeJsonDumpStore, None)

  css = cstore.CrashStorageSystemForHBase(d, configPrefix='',
                                          hbaseClient=fakeHbaseModule,
                                          jsonDumpStorage=fakeJsonDumpModule)
  expectedResult = cstore.CrashStorageSystem.OK
  result = css.save_raw('uuid', jdict, expectedDumpResult, currentTimestamp)
  assert result == expectedResult, 'expected %s but got %s' % (expectedResult, result)

def testCrashStorageSystemForHBase_save_2():
  """hbase fails, must save to fallback"""
  currentTimestamp = 'now'
  expectedDumpResult = '1234567890/n'
  jdict = util.DotDict({'ProductName':'FireFloozy', 'Version':'3.6', 'legacy_processing':1})

  d = util.DotDict()
  j = util.DotDict()
  d.hbaseHost = 'fred'
  d.hbasePort = 'ethel'
  d.hbaseTimeout = 9000
  j.root = d.hbaseFallbackFS = '.'
  d.throttleConditions = []
  j.maxDirectoryEntries = d.hbaseFallbackDumpDirCount = 1000000
  j.jsonSuffix = d.jsonFileSuffix = '.json'
  j.dumpSuffix = d.dumpFileSuffix = '.dump'
  j.dumpGID = d.hbaseFallbackDumpGID = 666
  j.dumpPermissions = d.hbaseFallbackDumpPermissions = 660
  j.dirPermissions = d.hbaseFallbackDirPermissions = 770
  j.logger = d.logger = util.SilentFakeLogger()

  fakeHbaseConnection = exp.DummyObjectWithExpectations('fakeHbaseConnection')
  fakeHbaseConnection.expect('hbaseThriftExceptions', None, None, (), None)
  fakeHbaseConnection.expect('put_json_dump', ('uuid', jdict, expectedDumpResult), {"number_of_retries":2}, None, Exception())

  fakeHbaseModule = exp.DummyObjectWithExpectations('fakeHbaseModule')
  fakeHbaseModule.expect('HBaseConnectionForCrashReports', (d.hbaseHost, d.hbasePort, d.hbaseTimeout), {"logger":d.logger}, fakeHbaseConnection, None)
  fakeHbaseModule.expect('NoConnectionException', None, None, hbc.NoConnectionException, None)


  class FakeFile(object):
    def write(self, x): pass
    def close(self): pass

  fakeJsonFile = FakeFile()
  fakeDumpFile = exp.DummyObjectWithExpectations('fakeDumpFile')
  fakeDumpFile.expect('write', (expectedDumpResult,), {})
  fakeDumpFile.expect('close', (), {})

  fakeJsonDumpStore = exp.DummyObjectWithExpectations('fakeJsonDumpStore')
  fakeJsonDumpStore.expect('newEntry', ('uuid', os.uname()[1], currentTimestamp), {}, (fakeJsonFile, fakeDumpFile))
  fakeJsonDumpModule = exp.DummyObjectWithExpectations('fakeJsonDumpModule')
  fakeJsonDumpModule.expect('JsonDumpStorage', (), j, fakeJsonDumpStore, None)

  cstore.logger = loggerForTest.TestingLogger()
  css = cstore.CollectorCrashStorageSystemForHBase(d, fakeHbaseModule, fakeJsonDumpModule)
  expectedResult = cstore.CrashStorageSystem.OK
  result = css.save_raw('uuid', jdict, expectedDumpResult, currentTimestamp)

  assert result == expectedResult, 'expected %s but got %s' % (expectedResult, result)

def testCrashStorageSystemForHBase_save_3():
  """hbase fails with an unknown exception but there is no filesystem fallback - expecting error return"""
  currentTimestamp = 'now'
  expectedDumpResult = '1234567890/n'
  jdict = {'a':2, 'b':'hello'}

  d = util.DotDict()
  d.hbaseHost = 'fred'
  d.hbasePort = 'ethel'
  d.hbaseTimeout = 9000
  d.hbaseFallbackFS = ''
  d.throttleConditions = []
  d.hbaseFallbackDumpDirCount = 1000000
  d.jsonFileSuffix = '.json'
  d.dumpFileSuffix = '.dump'
  d.hbaseFallbackDumpGID = 666
  d.hbaseFallbackDumpPermissions = 660
  d.hbaseFallbackDirPermissions = 770
  d.logger = util.SilentFakeLogger()

  fakeHbaseConnection = exp.DummyObjectWithExpectations('fakeHbaseConnection')
  fakeHbaseConnection.expect('hbaseThriftExceptions', None, None, (), None)
  fakeHbaseConnection.expect('put_json_dump', ('uuid', jdict, expectedDumpResult), {"number_of_retries":2}, None, Exception())

  fakeHbaseModule = exp.DummyObjectWithExpectations('fakeHbaseModule')
  fakeHbaseModule.expect('HBaseConnectionForCrashReports', (d.hbaseHost, d.hbasePort, d.hbaseTimeout), {"logger":d.logger}, fakeHbaseConnection, None)
  fakeHbaseModule.expect('NoConnectionException', None, None, hbc.NoConnectionException, None)

  fakeJsonDumpModule = exp.DummyObjectWithExpectations('fakeJsonDumpModule')

  cstore.logger = loggerForTest.TestingLogger()
  css = cstore.CollectorCrashStorageSystemForHBase(d, fakeHbaseModule, fakeJsonDumpModule)
  expectedResult = cstore.CrashStorageSystem.ERROR
  print css.exceptionsEligibleForRetry
  result = css.save_raw('uuid', jdict, expectedDumpResult, currentTimestamp)

  assert result == expectedResult, 'expected %s but got %s' % (expectedResult, result)


import socorro.storage.hbaseClient as hbc
def testCrashStorageSystemForHBase_save_4():
  """hbase fails with a NoConnectionException but there is no filesystem fallback - expecting retry return"""
  currentTimestamp = 'now'
  expectedDumpResult = '1234567890/n'
  jdict = {'a':2, 'b':'hello'}

  d = util.DotDict()
  d.hbaseHost = 'fred'
  d.hbasePort = 'ethel'
  d.hbaseTimeout = 9000
  d.hbaseFallbackFS = ''
  d.throttleConditions = []
  d.hbaseFallbackDumpDirCount = 1000000
  d.jsonFileSuffix = '.json'
  d.dumpFileSuffix = '.dump'
  d.hbaseFallbackDumpGID = 666
  d.hbaseFallbackDumpPermissions = 660
  d.hbaseFallbackDirPermissions = 770
  d.logger = util.SilentFakeLogger()

  fakeHbaseConnection = exp.DummyObjectWithExpectations('fakeHbaseConnection')
  fakeHbaseConnection.expect('hbaseThriftExceptions', None, None, (), None)
  fakeHbaseConnection.expect('put_json_dump', ('uuid', jdict, expectedDumpResult), {"number_of_retries":2}, None, hbc.NoConnectionException(Exception()))

  fakeHbaseModule = exp.DummyObjectWithExpectations('fakeHbaseModule')
  fakeHbaseModule.expect('HBaseConnectionForCrashReports', (d.hbaseHost, d.hbasePort, d.hbaseTimeout), {"logger":d.logger}, fakeHbaseConnection, None)
  fakeHbaseModule.expect('NoConnectionException', None, None, hbc.NoConnectionException, None)

  fakeJsonDumpModule = exp.DummyObjectWithExpectations('fakeJsonDumpModule')

  cstore.logger = loggerForTest.TestingLogger()
  css = cstore.CrashStorageSystemForHBase(d, '', fakeHbaseModule, fakeJsonDumpModule)
  expectedResult = cstore.CrashStorageSystem.RETRY
  print css.exceptionsEligibleForRetry
  result = css.save_raw('uuid', jdict, expectedDumpResult, currentTimestamp)

  assert result == expectedResult, 'expected %s but got %s' % (expectedResult, result)

def testCrashStorageSystemForNFS__init__():
  d = util.DotDict()
  d.storageRoot = '/tmp/std'
  d.dumpDirCount = 42
  d.jsonFileSuffix = '.json'
  d.dumpFileSuffix = '.dump'
  d.dumpGID = 23
  d.dumpPermissions = 777
  d.dirPermissions = 777
  d.deferredStorageRoot = '/tmp/def'
  d.throttleConditions = [
    ("Version", lambda x: x[-3:] == "pre" or x[3] in 'ab', 100.0), # queue 100% of crashes with version ending in "pre" or having 'a' or 'b'
    #("Add-ons", re.compile('inspector\@mozilla\.org\:1\..*'), 75.0), # queue 75% of crashes where the inspector addon is at 1.x
    #("UserID", "d6d2b6b0-c9e0-4646-8627-0b1bdd4a92bb", 100.0), # queue all of this user's crashes
    #("SecondsSinceLastCrash", lambda x: 300 >= int(x) >= 0, 100.0), # queue all crashes that happened within 5 minutes of another crash
    (None, True, 10.0) # queue 10% of what's left
  ]

  css = cstore.CrashStorageSystemForNFS(d)
  assert css.standardFileSystemStorage.root == d.storageRoot
  assert css.deferredFileSystemStorage.root == d.deferredStorageRoot
  assert css.hostname == os.uname()[1]

def testCrashStorageForDualHbaseCrashStorageSystem01():
  d = util.DotDict()
  j = util.DotDict()
  d.hbaseHost = 'fred'
  d.secondaryHbaseHost = 'barney'
  d.hbasePort = 'ethel'
  d.secondaryHbasePort = 'betty'
  d.hbaseTimeout = 3000
  d.secondaryHbaseTimeout = 10000
  j.root = d.hbaseFallbackFS = '.'
  d.throttleConditions = []
  j.maxDirectoryEntries = d.hbaseFallbackDumpDirCount = 1000000
  j.jsonSuffix = d.jsonFileSuffix = '.json'
  j.dumpSuffix = d.dumpFileSuffix = '.dump'
  j.dumpGID = d.hbaseFallbackdumpGID = 666
  j.dumpPermissions = d.hbaseFallbackDumpPermissions = 660
  j.dirPermissions = d.hbaseFallbackDirPermissions = 770
  j.logger = d.logger = util.SilentFakeLogger()
  fakeHbaseConnection1 = exp.DummyObjectWithExpectations('fakeHbaseConnection1')
  fakeHbaseConnection2 = exp.DummyObjectWithExpectations('fakeHbaseConnection2')
  fakeHbaseConnection1.expect('hbaseThriftExceptions', None, None, (), None)
  fakeHbaseConnection1.expect('get_json', ('fakeOoid1',), {'number_of_retries':2}, 'fake_json1')
  import socorro.storage.hbaseClient as hbc
  fakeHbaseConnection1.expect('get_json', ('fakeOoid2',), {'number_of_retries':2}, None, hbc.OoidNotFoundException())
  fakeHbaseConnection2.expect('hbaseThriftExceptions', None, None, (), None)
  fakeHbaseConnection2.expect('get_json', ('fakeOoid2',), {'number_of_retries':2}, 'fake_json2')
  fakeHbaseModule = exp.DummyObjectWithExpectations('fakeHbaseModule')
  fakeHbaseModule.expect('HBaseConnectionForCrashReports', (d.hbaseHost, d.hbasePort, d.hbaseTimeout), {"logger":d.logger}, fakeHbaseConnection1, None)
  fakeHbaseModule.expect('NoConnectionException', None, None, hbc.NoConnectionException, None)
  fakeHbaseModule.expect('HBaseConnectionForCrashReports', (d.secondaryHbaseHost, d.secondaryHbasePort, d.secondaryHbaseTimeout), {"logger":d.logger}, fakeHbaseConnection2, None)
  fakeHbaseModule.expect('NoConnectionException', None, None, hbc.NoConnectionException, None)
  fakeJsonDumpStore = exp.DummyObjectWithExpectations('fakeJsonDumpStore')
  fakeJsonDumpModule = exp.DummyObjectWithExpectations('fakeJsonDumpModule')
  fakeJsonDumpModule.expect('JsonDumpStorage', (), j, fakeJsonDumpStore, None)
  fakeJsonDumpModule.expect('JsonDumpStorage', (), j, fakeJsonDumpStore, None)
  css = cstore.DualHbaseCrashStorageSystem(d,
                                           hbaseClient=fakeHbaseModule,
                                           jsonDumpStorage=fakeJsonDumpModule)
  assert css.hbaseConnection == fakeHbaseConnection1
  assert css.fallbackHBase.hbaseConnection == fakeHbaseConnection2
  result = css.get_meta('fakeOoid1')
  assert result == 'fake_json1'
  result = css.get_meta('fakeOoid2')
  assert result == 'fake_json2'

