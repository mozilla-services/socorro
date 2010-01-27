import unittest

import os
import simplejson

import socorro.lib.filesystem as soc_filesys

import socorro.unittest.testlib.util as tutil

import socorro.cron.dailyUrl as dailyUrl

jsonData = [
  # [testMount_index,uuid,json dict]
  [0,'abcd289c-a4e0-496a-a124-beb6d2100125', {
  "ProductName": "Firefox",
  "Version": "3.6",
  "EMCheckCompatibility": "true",
  "Add-ons": "oma@me.com:1.1.2,opa@me.com:6.0.13",
  "Throttleable": "1",
  "Theme": "classic\/1.0",
  "StartupTime": "1264455098",
  "timestamp": 1264455122.84,
  "ReleaseChannel": "release"
  }],
  [1,'deadbea7-3141-4ec4-96bc-5a8212100125', {
  "ProductName": "Firefox",
  "Version": "3.6",
  "EMCheckCompatibility": "false",
  "Add-ons": "oma@me.com:1.1.2,opa@me.com:6.0.13",
  "Throttleable": "0",
  "Theme": "classic\/1.0",
  "StartupTime": "1264455098",
  "timestamp": 1264455122.84,
  "ReleaseChannel": "release"
  }],
  [2,'deaf36ac-2615-42a1-8ede-e98e12100125', {
  "ProductName": "Firefox",
  "Version": "3.6",
  "Add-ons": "oma@me.com:1.1.2,opa@me.com:6.0.13",
  "Theme": "classic\/1.0",
  "StartupTime": "1264455098",
  "timestamp": 1264455122.84,
  "ReleaseChannel": "release"
  }],
]

def setup_module():
  tutil.nosePrintModule(__file__)


class testFormatter:
  def __init__(self,initialData = []):
    self.data = initialData

  def writerow(self,aList):
    self.data.append(aList)

class TestDailyUrl(unittest.TestCase):
  def setUp(self):
    try:
      shutil.rmtree(self.testDir)
    except:
      pass
    self.testDir = os.path.join(os.path.dirname(__file__),'TEST_DIR')
    soc_filesys.makedirs(self.testDir)
    self.testMounts =['mount0','foo%(S)sbar%(S)sbaz%(S)s..%(S)sboo'%{'S':os.path.sep},'moo%(S)syou'%{'S':os.path.sep}]
    for d in jsonData:
      dir = os.path.join(self.testDir,self.testMounts[d[0]])
      jsonFile = dailyUrl.pathFromUuidAndMount(dir,d[1],'json')
      jsonDir = os.path.dirname(jsonFile)
      soc_filesys.makedirs(jsonDir)
      fh = open(jsonFile,'w')
      simplejson.dump(d[2],fh)
      
  def tearDown(self):
    try:
      shutil.rmtree(self.testDir)
    except:
      pass

  def testPathFromUuidAndMount(self):
    uuids = ['0bba61c5-dfc3-43e7-dead-8afd20071025', '0bba929f-8721-460c-dead-a43c20071025', '0b9ff107-8672-4aac-dead-b2bd20081225']
    suffix = 'suff'
    expected = [os.path.sep.join([self.testMounts[0],'0b','ba',uuids[0]+'.'+suffix]),
                os.path.sep.join([self.testMounts[1],'0b','ba',uuids[1]+'.'+suffix]),
                os.path.sep.join([self.testMounts[2],'0b','9f',uuids[2]+'.'+suffix]),
                ]
    for i in range(len(uuids)):
      got = dailyUrl.pathFromUuidAndMount(self.testMounts[i],uuids[i],suffix)
      assert expected[i] == got, 'Expected %s but got %s'%(expected[i],got)

  def testGetJson(self):
    config = {'rawFileMountPoints': ' '.join([os.path.join(self.testDir,x) for x in self.testMounts])}
    for jd in jsonData:
      x = dailyUrl.getJson(config,jd[1])
      assert x, 'expected a real json file, but got %s'%(x)
    x = dailyUrl.getJson(config,'aaaaffff-aeae-6666-7777-babe02100125')
    assert not x, 'expected None, got %s'%(x)
    
  def testGetColumnHeader(self):
    assert ['addons_checked'] == dailyUrl.getColumnHeader([])
    
  def testAppendDetailsFromJson(self):
    config = {'rawFileMountPoints': ' '.join([os.path.join(self.testDir,x) for x in self.testMounts])}
    cList = []
    dailyUrl.appendDetailsFromJson(config,cList,'aaaaffff-aeae-6666-7777-babe02100125')
    assert [] == cList, 'expected empty list, got %s'%(str(cList))
    expected = [['checked'],['not'],['unknown']]
    for i in range(len(jsonData)):
      jd = jsonData[i]
      cList = []
      dailyUrl.appendDetailsFromJson(config,cList,jd[1])
      assert expected[i] == cList, 'Expected %s, got %s'%(str(expected[i]),str(cList))
    
  def testWriteRowToInternalAndExternalFiles(self):
    iF = testFormatter([])
    pF = testFormatter([])
    data = [
      ['0','http://url',2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'email@a.b',18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'', 18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'email@a.b',18],
      ]
    iExpected = [
      ['0','http://url',2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'email@a.b',18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'', 18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'email@a.b',18],
      ]
    pExpected = [
      ['0','URL removed',2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'',18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'', 18],
      ['0','', 2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,'',18],
      ]
    for d in data:
      dailyUrl.writeRowToInternalAndExternalFiles(iF,pF,d)

    for i in range(len(iF.data)):
      assert iExpected[i] == iF.data[i]
    for i in range(len(pF.data)):
      assert pExpected[i] == pF.data[i]
