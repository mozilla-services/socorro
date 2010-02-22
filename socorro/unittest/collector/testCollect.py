import unittest
import os
import socorro.collector.collect as collect
import socorro.unittest.testlib.expectations as exp
import socorro.lib.util as util


def testRepeatableStreamReader():
  expectedReadResult = '1234567890/n'
  fakeStream = exp.DummyObjectWithExpectations('fakeStream')
  fakeStream.expect('read', (), {}, expectedReadResult, None)
  rsr = collect.RepeatableStreamReader(fakeStream)
  result = rsr.read()
  assert result == expectedReadResult, '1st expected %s but got %s' % (expectedReadResult, result)
  result = rsr.read()
  assert result == expectedReadResult, '2nd expected %s but got %s' % (expectedReadResult, result)
  result = rsr.read()
  assert result == expectedReadResult, '3rd expected %s but got %s' % (expectedReadResult, result)

def testCrashStorageSystem__init__():
  d = util.DotDict()
  d.benchmark = False
  css = collect.CrashStorageSystem(d)
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
  css = collect.CrashStorageSystem(d)
  resultJson = css.makeJsonDictFromForm(f, fakeTimeModule)
  assert resultJson.a == '1'
  assert resultJson.b == 2
  assert resultJson.c == '3'
  assert 'd' not in resultJson
  assert resultJson.e == '5'

def testCrashStorageSystem_save():
  css = collect.CrashStorageSystem({})
  result = css.save('fred', 'ethel', 'lucy')
  assert result == collect.CrashStorageSystem.NO_ACTION

def testCrashStorageSystemForHBase___init__():
  d = util.DotDict()
  d.hbaseHost = 'fred'
  d.hbasePort = 'ethel'
  fakeHbaseModule = exp.DummyObjectWithExpectations('fakeHbaseModule')
  fakeHbaseModule.expect('HBaseConnectionForCrashReports', ('fred', 'ethel'), {}, 'a fake connection', None)
  css = collect.CrashStorageSystemForHBase(d, fakeHbaseModule)
  assert css.hbaseConnection == 'a fake connection'

def testCrashStorageSystemForHBase_save_1():
  expectedReadResult = '1234567890/n'
  fakeStream = exp.DummyObjectWithExpectations('fakeStream')
  fakeStream.expect('read', (), {}, expectedReadResult, None)
  rsr = collect.RepeatableStreamReader(fakeStream)

  d = util.DotDict()
  d.hbaseHost = 'fred'
  d.hbasePort = 'ethel'

  fakeHbaseConnection = exp.DummyObjectWithExpectations('fakeHbaseConnection')
  fakeHbaseConnection.expect('create_ooid', ('uuid', '1111', expectedReadResult), {}, None, None)

  fakeHbaseModule = exp.DummyObjectWithExpectations('fakeHbaseModule')
  fakeHbaseModule.expect('HBaseConnectionForCrashReports', ('fred', 'ethel'), {}, fakeHbaseConnection, None)

  css = collect.CrashStorageSystemForHBase(d, fakeHbaseModule)
  expectedResult = collect.CrashStorageSystem.OK
  result = css.save('uuid', 1111, rsr)
  assert result == expectedResult, 'expected %s but got %s' % (expectedResult, result)

def testCrashStorageSystemForHBase_save_2():
  expectedReadResult = '1234567890/n'
  fakeStream = exp.DummyObjectWithExpectations('fakeStream')
  fakeStream.expect('read', (), {}, expectedReadResult, None)
  rsr = collect.RepeatableStreamReader(fakeStream)

  d = util.DotDict()
  d.hbaseHost = 'fred'
  d.hbasePort = 'ethel'

  fakeHbaseConnection = exp.DummyObjectWithExpectations('fakeHbaseConnection')
  fakeHbaseConnection.expect('create_ooid', ('uuid', '1111', expectedReadResult), {}, None, Exception())

  fakeHbaseModule = exp.DummyObjectWithExpectations('fakeHbaseModule')
  fakeHbaseModule.expect('HBaseConnectionForCrashReports', ('fred', 'ethel'), {}, fakeHbaseConnection, None)

  css = collect.CrashStorageSystemForHBase(d, fakeHbaseModule)
  expectedResult = collect.CrashStorageSystem.ERROR
  result = css.save('uuid', 1111, rsr)
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

  css = collect.CrashStorageSystemForNFS(d)
  assert css.normalizedVersionDict == {}
  assert css.normalizedVersionDictEntryCounter == 0
  assert css.standardFileSystemStorage.root == d.storageRoot
  assert css.deferredFileSystemStorage.root == d.deferredStorageRoot
  assert css.hostname == os.uname()[1]

