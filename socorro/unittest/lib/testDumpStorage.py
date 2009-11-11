import datetime
import logging
import os
import shutil
import sys
import time

from nose.tools import *

import socorro.lib.dumpStorage as dumpStorage
import socorro.lib.util as socorro_util

import socorro.unittest.testlib.util as test_util

def setup_module():
  print test_util.getModuleFromFile(__file__)

class TestDumpStorage():
  def setUp(self):
    self.expectedTestDir = os.path.join('.','TEST-DUMP')
    self.testDir = self.expectedTestDir+os.sep
    self.testData = {
      '0bba61c5-dfc3-43e7-dead-8afd20081225': ['0b/ba',datetime.datetime(2008,12,25,12,0, 0),'12/00'],
      '0bba929f-8721-460c-dead-a43c20081225': ['0b/ba',datetime.datetime(2008,12,25,12,0, 1),'12/00'],
      '0b9ff107-8672-4aac-dead-b2bd20081225': ['0b/9f',datetime.datetime(2008,12,25,12,0,59),'12/00'],
      '22adfb61-f75b-11dc-dead-001320081225': ['22/ad',datetime.datetime(2008,12,25,12,55,0),'12/55'],
      'b965de73-ae90-a935-dead-03ae20080101': ['b9/65',datetime.datetime(2008, 1, 1,1,20,31),'01/20'],
      '0b781b88-ecbe-4cc4-dead-6bbb20080203': ['0b/78',datetime.datetime(2008, 2, 3, 4,1,45),'04/00'],
      }
    self.ctorData = {
      0:{'dateName':'otherDate','logger':logging.getLogger('otherLogger')},
      1:{'indexName':'otherIndex','storageDepth':3},
      2:{'storageDepth':'4','minutesPerSlot':10},
      3:{'minutesPerSlot':'10','dirPermissions':0577},
      4:{'dumpGID':32111,'subSlotCount':3},
      5:{}
      }
    self.expectedCtor = {
      0:{'root':self.expectedTestDir,
         'dateName':'otherDate',
         'indexName':'name',
         'storageDepth':2,
         'minutesPerSlot':5,
         'dirPermissions':0770,
         'dumpGID':None,
         'logger.name':'otherLogger',
         'subSlotCount': 0,
         },
      1:{'root':self.expectedTestDir,
         'dateName':'date',
         'indexName':'otherIndex',
         'storageDepth':3,
         'minutesPerSlot':5,
         'dirPermissions':0770,
         'dumpGID':None,
         'logger.name':'dumpStorage',
         'subSlotCount': 0,
         },
      2:{'root':self.expectedTestDir,
         'dateName':'date',
         'indexName':'name',
         'storageDepth':4,
         'minutesPerSlot':10,
         'dirPermissions':0770,
         'dumpGID':None,
         'logger.name':'dumpStorage',
         'subSlotCount': 0,
         },
      3:{'root':self.expectedTestDir,
         'dateName':'date',
         'indexName':'name',
         'storageDepth':2,
         'minutesPerSlot':10,
         'dirPermissions':0577,
         'dumpGID':None,
         'logger.name':'dumpStorage',
         'subSlotCount': 0,
         },
      4:{'root':self.expectedTestDir,
         'dateName':'date',
         'indexName':'name',
         'storageDepth':2,
         'minutesPerSlot':5,
         'dirPermissions':0770,
         'dumpGID':32111,
         'logger.name':'dumpStorage',
         'subSlotCount': 3,
         },
      5:{'root':self.expectedTestDir,
         'dateName':'date',
         'indexName':'name',
         'storageDepth':2,
         'minutesPerSlot':5,
         'dirPermissions':0770,
         'dumpGID':None,
         'logger.name':'dumpStorage',
         'subSlotCount': 0,
         },
      }

  def tearDown(self):
    try:
      shutil.rmtree(self.testDir)
    except OSError:
      pass # ok if there is already no such directory

  def testConstructor(self):
    for i in range(len(self.expectedCtor)):
      if i in (1,3,5):
        root = self.expectedTestDir
      else:
        root = self.testDir
      d = dumpStorage.DumpStorage(root,**self.ctorData[i])
      for k in self.expectedCtor[i]:
        e = self.expectedCtor[i][k]
        g = eval("d."+k)
        assert e == g,'At loop %d, key %s: Wanted "%s", got "%s"'%(i,k,e,g)

  def testReadableOrThrow(self):
    d = dumpStorage.DumpStorage
    assert_raises(OSError,d.readableOrThrow,self.testDir)
    os.mkdir(self.testDir)
    tname = 'someUselessFile_'
    d.readableOrThrow(self.testDir)
    f = open(tname,'w')
    f.write('something')
    f.close()
    os.chmod(tname,0)
    try:
      assert_raises(OSError,d.readableOrThrow,tname)
    finally:
      os.chmod(tname,0200)
      os.unlink(tname)
      
  def testDailyPart(self):
    d = dumpStorage.DumpStorage(self.testDir)
    testData = [
      ('12345678-dead-beef-feeb-daed20081225',datetime.datetime(2008,12,25,1,2,3),'20081225'),
      ('12345678-dead-beef-feeb-daed20081225',datetime.datetime(2008,12,26,1,2,3),'20081226'),
      ('12345678-dead-beef-feeb-daed20081225',None,'20081225'),
      ('',datetime.datetime(2008,12,25,1,2,3),'20081225'),
      (None,None,None),
      ('',None,None),
      ]
    for ooid,date,expected in testData:
      if expected:
        got = d.dailyPart(ooid,date)
        assert expected == got, 'Expected "%s" but got "%s"'%(expected,got)
      else:
        expectedErrorType = TypeError
        if '' == ooid: expectedError = IndexError
        assert_raises(expectedErrorType, d.dailyPart, (ooid,date))
    
  def testRelativeNameParts(self):
    ooid = '12345678-dead-beef-feeb-daed20081225'
    expected = {1:['12'],2:['12','34'],3:['12','34','56'],4:['12','34','56','78']}
    for depth in range(1,5):
      d = dumpStorage.DumpStorage(self.testDir,storageDepth = depth)
      assert expected[depth] == d.relativeNameParts(ooid)
      
  def testNamePath(self):
    d = dumpStorage.DumpStorage(self.testDir)
    for k,v in self.testData.items():
      g = d.namePath(k,v[1])[0]
      e = os.sep.join((d.root,d.dailyPart(k,v[1]),d.indexName,v[0]))
      assert e == g, 'Expected "%s", got "%s"'%(e,g)

  def testDatePath(self):
    d = dumpStorage.DumpStorage(self.testDir)
    for k,v in self.testData.items():
      g = d.datePath(v[1])[0]
      e = os.sep.join((d.root,d.dailyPart(k,v[1]),d.dateName,v[2]))
      assert e == g, 'Expected "%s", got "%s"'%(e,g)
    d = dumpStorage.DumpStorage(self.testDir,subSlotCount=3)
    curcount = 0
    for k,v in self.testData.items():
      g = d.datePath(v[1])[0]
      e = os.sep.join((d.root,d.dailyPart(k,v[1]),d.dateName,"%s_%d"%(v[2],curcount)))
      curcount = (curcount + 1) % d.subSlotCount
      assert e == g, 'Expected "%s", got "%s"'%(e,g)
    curcount = 0
    for k,v in self.testData.items():
      g = d.datePath(v[1],webheadName='boot')[0]
      e = os.sep.join((d.root,d.dailyPart(k,v[1]),d.dateName,v[2],"%s_%d"%('boot',curcount)))
      curcount = (curcount + 1) % d.subSlotCount
      assert e == g, 'Expected "%s", got "%s"'%(e,g)
    
  def testMakeDateDir(self):
    d = dumpStorage.DumpStorage(self.testDir)
    d3 = dumpStorage.DumpStorage(self.testDir,subSlotCount=3)
    # first test: Make a file of the same name as a subdir and see it fail as expected
    testItem = self.testData.items()[0][1]
    date = testItem[1]
    datePathPart = testItem[2]
    while True:
      head,tail = os.path.split(datePathPart)
      if head == tail: break
      dirPart = os.sep.join((d.root,d.dailyPart('',date),d.dateName,head))
      try:
        shutil.rmtree(d.root)
      except:
        pass
      filePart = os.path.join(dirPart,tail)
      os.makedirs(dirPart)
      f = open(filePart,'w')
      f.write("nothing\n")
      f.close()
      assert_raises(OSError,d.makeDateDir,date)
      assert_raises(OSError,d3.makeDateDir,date,'boot')
      datePathPart = head
    try:
      shutil.rmtree(d.root)
    except:
      pass
    curSS = d3.currentSubSlot
    for k,v in self.testData.items():
      g,dum = d.makeDateDir(v[1])
      e = os.sep.join((d.root, d.dailyPart(k,v[1]),d.dateName,v[2]))

      g0,dum0 = d3.makeDateDir(v[1])
      e0 = os.sep.join((d.root, d.dailyPart(k,v[1]),d.dateName,"%s_%d"%(v[2],curSS)))
      curSS = (curSS+1)%3

      g3,dum3 = d3.makeDateDir(v[1],'boot')
      e3 = os.sep.join((d.root, d.dailyPart(k,v[1]),d.dateName,v[2],"%s_%d"%('boot',curSS)))
      curSS = (curSS+1)%3

      assert e == g, 'Expected "%s", got "%s"'%(e,g)
      assert os.path.isdir(g), 'But "%s" is not a dir'%g
      assert e0 == g0, 'Expected "%s", got "%s"'%(e0,g0)
      assert os.path.isdir(g0), 'But "%s" is not a dir'%g
      assert e3 == g3, 'Expected "%s", got "%s"'%(e3,g3)
      assert os.path.isdir(g3), 'But "%s" is not a dir'%g

  def testMakeNameDir(self):
    d = dumpStorage.DumpStorage(self.testDir)
    # first test: Make a file of the same name and see it fail as expected
    testItem = self.testData.items()[0]
    testOoid = testItem[0]
    testPath = testItem[1][0]
    testDate = testItem[1][1]
    while True:
      head,tail = os.path.split(testPath)
      if head == tail: break
      dirPart = os.sep.join((d.root,d.dailyPart(testOoid,testDate),d.indexName,head))
      try:
        shutil.rmtree(d.root)
      except:
        pass
      filePart = os.path.join(dirPart,tail)
      os.makedirs(dirPart)
      f = open(filePart,'w')
      f.write("nothing\n")
      f.close()
      assert_raises(OSError,d.makeNameDir,testOoid)
      testPath = head
    try:
      shutil.rmtree(d.root)
    except:
      pass

    for k,v in self.testData.items():
      g,dum = d.makeNameDir(k)
      e = os.path.join(d.root,d.dailyPart(k,v[1]),d.indexName,v[0])
      assert e == g, 'Expected "%s" got "%s"'%(e,g)

  def testNewEntry(self):
    # test the default case
    d = dumpStorage.DumpStorage(self.testDir)
    for k,v in self.testData.items():
      nd,dd = d.newEntry(k,v[1])
      assert os.path.isdir(nd)
      assert os.path.isdir(dd)
      assert os.path.islink(os.path.join(dd,k))
      e = os.path.abspath(nd)
      g = os.path.abspath(os.path.join(dd,os.readlink(os.path.join(dd,k))))
      assert e == g,'Expected %s, got %s'%(e,g)
    # test the trailing _n case at same level
    d = dumpStorage.DumpStorage(self.testDir,subSlotCount=3)
    for k,v in self.testData.items():
      nd,dd = d.newEntry(k,v[1])
      assert os.path.isdir(nd)
      assert os.path.isdir(dd)
      assert os.path.islink(os.path.join(dd,k))
      e = os.path.abspath(nd)
      g = os.path.abspath(os.path.join(dd,os.readlink(os.path.join(dd,k))))
      assert e == g,'Expected %s, got %s'%(e,g)
    # test with subdirectory further down
    d = dumpStorage.DumpStorage(self.testDir,subSlotCount=3)
    for k,v in self.testData.items():
      nd,dd = d.newEntry(k,v[1],webheadName='wh')
      assert os.path.isdir(nd)
      assert os.path.isdir(dd)
      assert os.path.islink(os.path.join(dd,k))
      e = os.path.abspath(nd)
      g = os.path.abspath(os.path.join(dd,os.readlink(os.path.join(dd,k))))
      assert e == g,'Expected %s, got %s'%(e,g)
