import socorro.unittest.testlib.createJsonDumpStore as createJDS

import os
import shutil

from nose.tools import *

import socorro.unittest.testlib.util as tutil

def setup_module():
  tutil.nosePrintModule(__file__)

def testGetSlot():
  testData = [
    (0,1,0),
    (0,30,0),
    (1,5,0),
    (1,12,0),
    (4,5,0),
    (5,5,5),
    (29,30,0),
    (30,30,30),
    (59,5,55),
    (59,12,48),
    ]
  for minutes, size, expected in testData:
    got = createJDS.getSlot(size,minutes)
    assert expected == got, 'expected %s from getSlot(%s,%s), got %s'%(expected,minute,size,got)
  assert_raises(ZeroDivisionError, createJDS.getSlot, 0, 12)
  
def testMinimalJsonFileContents():
  testMap = {'first':'a%d'}
  gen = createJDS.minimalJsonFileContents(testMap)
  for i in range(3):
    expected = '{"first": "a%d"}'%i
    got = gen.next()
    assert expected == got
  gen = createJDS.minimalJsonFileContents()
  for i in range(3):
    expected = '{"BuildID": "bogusBuildID-%02d", "Version": "bogusVersion-%02d", "ProductName": "bogusName-%02d"}'%(i,i,i)
    got = gen.next()
    assert expected == got

def testCreateTestSet():
  testDir = "./TEST_CREATE_DIR"
  try:
    shutil.rmtree(testDir)
  except:
    pass
  assert not os.path.exists(testDir)
  try:
    createJDS.createTestSet({},{},testDir)
    assert os.path.isdir(testDir)
  finally:
    try:
      shutil.rmtree(testDir)
    except:
      pass

  expected = {
    '%s/20071025/date/05'%testDir:(['04'], []),
    '%s/20071025/date'%testDir:(['05'], []),
    '%s/20071025/name/0b/ba/61/c5'%testDir:(['0bba61c5-dfc3-43e7-effe-8afd20071025'], ['0bba61c5-dfc3-43e7-effe-8afd20071025.dump', '0bba61c5-dfc3-43e7-effe-8afd20071025.json']),
    '%s/20071025/name/0b'%testDir:(['ba'], []),
    '%s/20071025/date/05/04'%testDir:(['webhead02_0'], []),
    '%s/20071025/name/0b/ba/61'%testDir:(['c5'], []),
    '%s/20071025'%testDir:(['date', 'name'], []),
    '%s/20071025/date/05/04/webhead02_0'%testDir:(['0bba61c5-dfc3-43e7-effe-8afd20071025'], []),
    '%s/20071025/name'%testDir:(['0b'], []),
    '%s'%testDir:(['20071025'], []),
    '%s/20071025/name/0b/ba'%testDir:(['61'], []),
    }
  minSet = {'0bba61c5-dfc3-43e7-effe-8afd20071025': ('2007-10-25-05-04','webhead02','0b/ba/61/c5','2007/10/25/05/00/webhead02_0')}
  try:
    createJDS.createTestSet(minSet,{},testDir)
    got = {}
    for dirpath, files, dirs in os.walk(testDir):
      got[dirpath] = (files,dirs)
    if expected != got:
      for k, v in expected.items():
        print 'X',k,v
      for k,v in got.items():
        print 'G',k,v
    assert expected == got, 'Expected "%s" but got "%s"'%(expected,got)
    f = open(os.path.join(testDir,'20071025/name/0b/ba/61/c5/0bba61c5-dfc3-43e7-effe-8afd20071025.dump'))
    data = f.readlines()
    assert 1 == len(data)
    assert 'dump test of 0bba61c5-dfc3-43e7-effe-8afd20071025' == data[0].strip()
    f.close()
    f = open(os.path.join(testDir,'20071025/name/0b/ba/61/c5/0bba61c5-dfc3-43e7-effe-8afd20071025.json'))
    data = f.readlines()
    assert 1 == len(data)
    assert 'json test of 0bba61c5-dfc3-43e7-effe-8afd20071025' == data[0].strip()
    f.close()
  finally:
    try:
      shutil.rmtree(testDir)
    except:
      pass

  try:
    createJDS.createTestSet(minSet,{'jsonIsEmpty':True},testDir)
    f = open(os.path.join(testDir,'20071025/name/0b/ba/61/c5/0bba61c5-dfc3-43e7-effe-8afd20071025.dump'))
    data = f.readlines()
    assert 1 == len(data)
    assert 'dump test of 0bba61c5-dfc3-43e7-effe-8afd20071025' == data[0].strip()
    f.close()
    f = open(os.path.join(testDir,'20071025/name/0b/ba/61/c5/0bba61c5-dfc3-43e7-effe-8afd20071025.json'))
    data = f.readlines()
    assert 0 == len(data)
    f.close()
  finally:
    try:
      shutil.rmtree(testDir)
    except:
      pass

  try:
    createJDS.createTestSet(minSet,{'jsonIsBogus':False, 'jsonFileGenerator':'default'},testDir)
    f = open(os.path.join(testDir,'20071025/name/0b/ba/61/c5/0bba61c5-dfc3-43e7-effe-8afd20071025.dump'))
    data = f.readlines()
    assert 1 == len(data)
    assert 'dump test of 0bba61c5-dfc3-43e7-effe-8afd20071025' == data[0].strip()
    f.close()
    f = open(os.path.join(testDir,'20071025/name/0b/ba/61/c5//0bba61c5-dfc3-43e7-effe-8afd20071025.json'))
    data = f.readlines()
    assert 1 == len(data)
    expect='{"BuildID": "bogusBuildID-00", "Version": "bogusVersion-00", "ProductName": "bogusName-00"}'
    assert expect == data[0].strip()
    f.close()
  finally:
    try:
      shutil.rmtree(testDir)
    except:
      pass

  try:
    createJDS.createTestSet(minSet,{'jsonIsBogus':False},testDir)
    f = open(os.path.join(testDir,'20071025/name/0b/ba/61/c5/0bba61c5-dfc3-43e7-effe-8afd20071025.dump'))
    data = f.readlines()
    assert 1 == len(data)
    assert 'dump test of 0bba61c5-dfc3-43e7-effe-8afd20071025' == data[0].strip()
    f.close()
    f = open(os.path.join(testDir,'20071025/name/0b/ba/61/c5/0bba61c5-dfc3-43e7-effe-8afd20071025.json'))
    data = f.readlines()
    assert 1 == len(data)
    expect='{"what": "legal json, bad contents", "uuid": "0bba61c5-dfc3-43e7-effe-8afd20071025"}'
    assert expect == data[0].strip()
    f.close()
  finally:
    try:
      shutil.rmtree(testDir)
    except:
      pass
