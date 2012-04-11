import unittest
import os
import shutil
import datetime
import time
import sys

from nose.tools import *

import socorro.external.filesystem.json_dump_storage as JDS
import socorro.lib.util
from socorro.lib.datetimeutil import utc_now, UTC

import socorro.unittest.testlib.createJsonDumpStore as createJDS
import socorro.unittest.testlib.util as tutil

def setup_module():
  print tutil.getModuleFromFile(__file__)

class TestJsonDumpStorage(unittest.TestCase):
  def setUp(self):
    self.testDir = os.path.join('.','TEST-JSONDUMP')+'/'
    self.testMoveTo = os.path.join('.','TEST-MOVETO')
    self.testMoveFrom = os.path.join('.','TEST-MOVEFROM')
    self.testMoveToAlt = os.path.join('.','TEST-MOVETO-ALT')
    fakeLogger = socorro.lib.util.SilentFakeLogger()
    self.initKwargs =  {
      0:{'logger': fakeLogger},
      1:{'logger': fakeLogger,'dateName':'by_date','indexName':'by_name','jsonSuffix':'JS','dumpSuffix':'.DS',},
      2:{'logger': fakeLogger,'jsonSuffix':'JS','dumpSuffix':'.DS',},
      3:{'logger': fakeLogger,'dateName':'by_date','indexName':'index',},
      }

    self.currenttimes = {
      '0bba61c5-dfc3-43e7-dead-8afd20081225': ['+0','webhead02', '0b/ba/61/c5','webhead02_0'],
      '0bba929f-8721-460c-dead-a43c20081225': ['+0','webhead02', '0b/ba/92/9f','webhead02_0'],
      '0b9ff107-8672-4aac-dead-b2bd20081225': ['+0','webhead01', '0b/9f/f1/07','webhead01_0'],
      '22adfb61-f75b-11dc-dead-001320081225': ['+0','webhead01', '22/ad/fb/61','webhead01_0'],
      'b965de73-ae90-a935-dead-03ae20081225': ['+0','webhead01', 'b9/65/de/73','webhead01_0'],
      '0b781b88-ecbe-4cc4-dead-6bbb20081225': ['+5','webhead01', '0b/78/1b/88','webhead01_0'],
      '0b8344d6-9021-4db9-dead-a15320081225': ['+5','webhead01', '0b/83/44/d6','webhead01_0'],
      '0b94199b-b90b-4683-dead-411420081225': ['+5','webhead01', '0b/94/19/9b','webhead01_0'],
      '0b9eedc3-9a79-4ce2-dead-155920081225': ['+5','webhead01', '0b/9e/ed/c3','webhead01_0'],
      '0b9fd6da-27e4-46aa-dead-3deb20081225': ['+10','webhead02','0b/9f/d6/da','webhead02_0'],
      '0ba32a30-2476-4724-dead-de1720081225': ['+10','webhead02','0b/a3/2a/30','webhead02_0'],
      '0bad640f-5825-4d42-dead-21b820081225': ['+10','webhead02','0b/ad/64/0f','webhead02_0'],
      '0bae7049-bbff-49f2-dead-7e9f20081225': ['+10','webhead02','0b/ae/70/49','webhead02_0'],
      '0baf1b4d-dad3-4d35-dead-b9dc20081225': ['+10','webhead02','0b/af/1b/4d','webhead02_0'],
      }

    try:
      shutil.rmtree(self.testDir)
    except OSError:
      pass # ok if there is no such test directory
    os.mkdir(self.testDir)

  def tearDown(self):
    try:
      shutil.rmtree(self.testDir)
    except OSError:
      pass # ok if there is no such test directory
    try:
      shutil.rmtree(self.testMoveTo)
    except OSError:
      pass
    try:
      shutil.rmtree(self.testMoveFrom)
    except OSError:
      pass
    try:
      shutil.rmtree(self.testMoveToAlt)
    except OSError:
      pass

  def __getSlot(self,minsperslot,minute):
    return minsperslot * int(minute/minsperslot)

  def __hasLinkOrFail(self,jsonStorage,uuid):
    linkPath = jsonStorage.getJson(uuid)[:-len(jsonStorage.jsonSuffix)]
    try:
      os.readlink(linkPath)
    except Exception,x:
      assert False, '(%s:%s) Expected to be able to readlink from %s'%(type(x),x,linkPath)
  def __hasNoLinkOrFail(self,jsonStorage,uuid):
    linkPath = jsonStorage.getJson(uuid)[:-len(jsonStorage.jsonSuffix)]
    try:
      os.readlink(linkPath)
      assert False, 'Expected to find no link: %s '%linkPath
    except OSError,x:
      assert 2 == x.errno, "Expected errno=2, got %d for linkpath %s"%(x.errno,linkpath)
    except Exception,x:
      assert False, "Expected OSError, got %s for linkpath %s"%(x,linkpath)

  def __hasDatePathOrFail(self,jsonStorage,ooid,dt):
    dpath,dpathParts = jsonStorage.lookupOoidInDatePath(dt,ooid)
    assert os.path.isdir(dpath), 'Expect %s is a directory'%(dpath)

  def __relativeDateParts(self,dateString,minutesPerSlot):
    """ given "YYYY-mm-dd-hh-mm", return [hh,slot]"""
    hh,mm = dateString.split('-')[-2:]
    slot = int(mm) - int(mm)%minutesPerSlot
    return [hh,"%02d"%slot]

  def testConstructor(self):
    self.constructorAlt(self.testDir,**self.initKwargs[0])
    self.constructorAlt(self.testDir,**self.initKwargs[1])
    self.constructorAlt(self.testDir,**self.initKwargs[2])
    self.constructorAlt(self.testDir,**self.initKwargs[3])

  def constructorAlt(self,*args,**kwargs):
    storage = JDS.JsonDumpStorage(self.testDir,**kwargs)
    assert storage.dateName == kwargs.get('dateName','date'),'From kwargs=%s'%kwargs
    assert storage.indexName == kwargs.get('indexName','name'),'From kwargs=%s'%kwargs
    assert storage.jsonSuffix == '.'+kwargs.get('jsonSuffix','json'),'We will always pass non-dot json suffix. From kwargs=%s'%kwargs
    assert storage.dumpSuffix == kwargs.get('dumpSuffix','.dump'),'We will always pass dot dump suffix. From kwargs=%s'%kwargs
    assert self.testDir.rstrip(os.sep) == storage.root,'From kwargs=%s'%kwargs

  def testNewEntry(self):
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[2])
    for uuid,data in createJDS.jsonFileData.items():
      datetimedata = [int(x) for x in data[0].split('-')]
      uuid = ''.join((uuid[:-7],'2',uuid[-6:]))
      stamp = datetime.datetime(*datetimedata, tzinfo=UTC)
      try:
        fj,fd = storage.newEntry(uuid,webheadHostName=data[1],timestamp = stamp)
      except IOError:
        assert False, 'Expect to succeed with newEntry(%s,...)' % uuid

      assert fj, 'Expect a non-null json file handle from newEntry(%s,...)' % uuid
      loc2 = data[2][0:5] # We are not honoring ooid depth
      expectFileBase = os.sep.join((storage.root, storage.dailyPart('',stamp), storage.indexName,loc2))
      expectJson = os.path.join(expectFileBase,uuid+storage.jsonSuffix)
      assert expectJson == fj.name, 'For %s, expect %s, got %s' % (uuid,expectJson,fj.name)
      assert fd, 'Expect a non-null dump file handle from newEntry(%s,...)' % uuid
      expectDump = os.path.join(expectFileBase,uuid+storage.dumpSuffix)
      assert expectDump == fd.name, 'For %s, expect %s, got %s' % (uuid,expectDump,fj.name)
      loc3parts = self.__relativeDateParts(data[0],storage.minutesPerSlot)
      loc3parts.append(data[3][-len('webhead0x_x'):])
      loc3 = os.sep.join(loc3parts)
      lbase = os.sep.join((storage.root, storage.dailyPart('',stamp), storage.dateName, loc3))
      lpath = os.path.join(lbase,uuid)
      assert os.path.islink(lpath), 'Expect a link from timed to storage for %s' % uuid
      relNamePath = os.path.join(lbase,os.readlink(lpath))
      assert os.path.isdir(relNamePath), 'Expected %s to be a Name directory'%(relNamePath)
      lpath = os.path.join(expectFileBase,uuid)
      assert os.path.islink(lpath), 'Expect link from name storage to timed for %s' % uuid
      relDatePath = os.path.join(expectFileBase,os.readlink(lpath))
      assert os.path.isdir(relDatePath), 'Expected %s to be a Date directory'%(relDatePath)
      try:
        try:
          fj.write("testing\n")
          assert True, 'must be able to write to the json file for uuid %s' % uuid
        except:
          assert False, 'must not fail to write to the json file for uuid %s' % uuid
      finally:
        if fj: fj.close()

      try:
        try:
          fd.write("testing\n")
          assert True, 'must be able to write to the dump file for uuid %s' % uuid
        except:
          assert False, 'must not fail to write to the dump file for uuid %s' % uuid
      finally:
        if fd: fd.close()

  def testCopyFrom(self):
    os.makedirs(self.testMoveFrom)
    fromdata = [('aabbccdd-something20071020','2007-10-20-12-15','webalos',True,False),
                ('aabbccee-something20071020','2007-10-20-12-15','webalos',True,False),
                ('aabbccff-something20071020','2007-10-20-10-15','webalos',False,True),
                ]
    df = jf = None
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[1])
    for (uuid,stampS,head,doLink,doRm) in fromdata:
      jpath = "%s%s%s%s"%(self.testMoveFrom,os.sep,uuid,storage.jsonSuffix)
      dpath = "%s%s%s%s"%(self.testMoveFrom,os.sep,uuid,storage.dumpSuffix)
      jf = open(jpath,'w')
      df = open(dpath,'w')
      jf.write('json file: %s\n'%uuid)
      df.write('dump file: %s\n'%uuid)
      jf.close()
      df.close()
      stamp = datetime.datetime(*[int(x) for x in stampS.split('-')], tzinfo=UTC)
      newjpath = None
      try:
        ok = storage.copyFrom(uuid,jpath,dpath,head,stamp,doLink,doRm)
        assert ok, "Expect to succeed with %s" % (uuid)
      except Exception, e:
        assert False,'Expected to not raise "%s" from id %s' % (e,uuid)
      try:
        newjpath = storage.getJson(uuid)
      except Exception, e:
        assert False, 'getJson(%s) should not raise %s'%(uuid, e)
      try:
        storage.getDump(uuid)
      except Exception,e:
        assert False, 'getDump(%s) should not raise %s'%(uuid,e)
      if doLink:
        assert newjpath
        link = os.path.splitext(newjpath)[0]
        assert os.path.islink(link)
        dir = os.readlink(link)
        dir = os.path.join(os.path.split(link)[0],dir)
        assert os.path.islink(os.path.join(dir,uuid))
      if doRm:
        assert not os.path.isfile(jpath)
        assert not os.path.isfile(dpath)
      else:
        assert os.path.isfile(jpath)
        assert os.path.isfile(dpath)

  def testTransferOne(self):
    createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[0],rootDir=self.testMoveFrom)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[0])
    oldStorage = JDS.JsonDumpStorage(self.testMoveFrom, **self.initKwargs[0])
    itemNumber = 0
    xmas = datetime.datetime(2001,12,25,12,25, tzinfo=UTC)
    for id in createJDS.jsonFileData.keys():
      createLinks = 0 == itemNumber%2
      removeOld = 0 == itemNumber%3
      itemNumber += 1
      storage.transferOne(id,oldStorage,createLinks=createLinks,removeOld=removeOld,aDate=xmas)
      try:
        storage.getJson(id)
      except Exception,x:
        print '(%s): %s'%(type(x),x)
        assert False, 'Expected to find a transferred json file for %s' % id
      if createLinks:
        self.__hasLinkOrFail(storage,id)
        self.__hasDatePathOrFail(storage,id,xmas)
      if removeOld:
        assert_raises(OSError,oldStorage.getJson,id)

  def testGetJson(self):
    createJDS.createTestSet(createJDS.jsonFileData, self.initKwargs[0],self.testDir)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[0])
    for uuid,data in createJDS.jsonFileData.items():
      dateparts = data[0].split('-')
      daily = "%4d%02d%02d"%tuple([int(x) for x in dateparts[:3]])
      expected = os.sep.join((storage.root,daily,storage.indexName,data[2],uuid+storage.jsonSuffix))
      got = storage.getJson(uuid)
      assert expected == got, 'Expected json file %s, got %s' % (expected,got)
    try:
      storage.getJson(createJDS.jsonBadUuid)
      assert False, 'Expect to throw IOError from attempt to getJson(non-existent-uuid)'
    except OSError,e:
      assert True, 'Got expected error from attempt to getJson(non-existent-uuid)'
    except Exception, e:
      assert False, 'Got unexpected error %s from attempt to getJson(non-existent-uuid' % e

  def testGetDump(self):
    createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[1],self.testDir)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[1])
    for uuid,data in createJDS.jsonFileData.items():
      dateparts = data[0].split('-')
      daily = "%4d%02d%02d"%tuple([int(x) for x in dateparts[:3]])
      expected = os.sep.join((storage.root,daily,storage.indexName,data[2],uuid+storage.dumpSuffix))
      got =  storage.getDump(uuid)
      assert expected == got, 'Expected dump file %s, got %s' % (expected,got)
    try:
      storage.getDump(createJDS.jsonBadUuid)
      assert False, 'Should throw IOError from attempt to getDump(non-existent-uuid)'
    except OSError,e:
      assert True
    except Exception, e:
      assert False, 'Got unexpected error(type) %s from attempt to getDump(non-existent-uuid' % e

  def markAsSeen(self):
    createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[3],self.testDir)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[3])
    for uuid,data in createJDS.jsonFileData.items():
      assert os.path.islink(os.sep.join((storage.dateBranch,data[3],uuid))), 'Expect a link from date to name for %s' % uuid
      assert os.path.islink(os.sep.join((storage.nameBranch,data[2],uuid))), 'Expect link from name to timed for %s' % uuid
      assert not os.path.islink(os.sep.join((storage.dateBranch,data[3],uuid))), 'Expect no link from date to name for %s' % uuid
      assert not os.path.islink(os.sep.join((storage.nameBranch,data[2],uuid))), 'Expect no link from name to date for %s' % uuid
    try:
      storage.markAsSeen(createJDS.jsonBadUuid)
      assert False, 'Expect to throw IOError from attempt to openAndMarkAsSeen(non-existent-uuid)'
    except IOError:
      assert True, 'Got expected error from attempt to openAndMarkAsSeen(non-existent-uuid)'
    except Exception, e:
      assert False, 'Got unexpected error %s from attempt to openAndMarkAsSeen(non-existent-uuid' % e
    assert not os.listdir(storage.dateBranch), 'Expect empty, got %s' % os.listdir(storage.dateBranch)

  def testDestructiveDateWalk(self):
    createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[0],self.testDir)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[0])
    uuids = createJDS.jsonFileData.keys()
    uuidsSet = set(uuids)
    seenids = set()
    for id in storage.destructiveDateWalk():
      assert id in uuids, 'Expect that %s is among the uuids we stored\n%s' % (id,uuids)
      seenids.add(id)
    for id in uuids:
      assert id in seenids, 'Expect that we found every uuid we stored (%s) from %s' % (id,seenids)
    daily = os.listdir(storage.root)
    for d in daily:
      assert not storage.dateName in os.listdir(os.path.join(storage.root,d)), 'Expected all date subdirs to be gone, but %s'%d

  def testMarkAsSeen(self):
    """testNewJsonDumpStorage:TestJsonDumpStorage.testMarkAsSeen()
    somewhat bogus test: Doesn't look for failure modes
    """
    createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[0],rootDir=self.testDir)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[2])
    for ooid in createJDS.jsonFileData.keys():
      namePath,parts = storage.namePath(ooid)
      linkInName = os.path.join(namePath,ooid)
      assert os.path.islink(linkInName), 'expected %s as link'%linkInName
      dpath = os.path.join(namePath,os.readlink(linkInName))
      linkInDate = os.path.join(dpath,ooid)
      assert os.path.islink(linkInDate), 'expected %s as link'%linkInDate
      storage.markAsSeen(ooid)
      assert not os.path.exists(linkInName), 'expected %s gone'%linkInName
      assert not os.path.exists(linkInDate), 'expected %s gone'%linkInDate

  def testDestructiveDateWalkNotNow(self):
    createJDS.createTestSet(self.currenttimes,self.initKwargs[1],self.testDir)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[1])
    uuids = self.currenttimes.keys()
    seenids = []
    for id in storage.destructiveDateWalk():
      seenids.append(id)
    assert [] == seenids

  def testRemove(self):
    createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[2],self.testDir)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[2])
    counter = 0
    for uuid in createJDS.jsonFileData.keys():
      if 0 == counter % 3:
        # test that we don't throw for missing links
        storage.markAsSeen(uuid)
      if 1 == counter % 3:
        # test that we don't throw for one missing file
        if 0 == counter % 2:
          os.unlink(storage.getDump(uuid))
        else:
          os.unlink(storage.getJson(uuid))
      if 2 == counter % 3:
        # test that we don't throw for both missing files, but with links
        os.unlink(storage.getJson(uuid))
        os.unlink(storage.getDump(uuid))
      storage.remove(uuid)
      counter += 1
    allfiles = []
    alllinks = []
    for dir, dirs, files in os.walk(self.testDir):
      for file in files:
        allfiles.append(file)
        if os.path.islink(os.path.join(dir,file)):
          alllinks.append(file)
      for d in dirs:
        if os.path.islink(os.path.join(dir,d)):
          alllinks.append(d)

    assert [] == allfiles, 'Expect that all removed files are gone, but found %s' % allfiles
    assert [] == alllinks, 'Expect that all links are gone, but found %s' % alllinks
    assert_raises(JDS.NoSuchUuidFound,storage.remove,"bogusdatax3yymmdd")

  def testRemoveAlsoNames(self):
    """testJsonDumpStorage:TestJsonDumpStorage.testRemoveAlsoNames(self)
    Try to remove them all, and check that they are indeed all gone.
    """
    createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[2],self.testDir)
    kwargs = self.initKwargs[2]
    kwargs['cleanIndexDirectories'] = 'True'
    storage = JDS.JsonDumpStorage(self.testDir,**kwargs)
    for uuid,data in createJDS.jsonFileData.items():
      storage.remove(uuid)
    assert not os.listdir(storage.root), 'Expected them all to go, but %s'%(os.listdir(storage.root))

  def testRemoveRemovesOnlyDate(self):
    createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[2],self.testDir)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[2])
    dailies = set([])
    expectedSubs = []
    alldirs = []
    allfiles = []
    alllinks = []
    for uuid,data in createJDS.jsonFileData.items():
      dailies.add(''.join(data[0].split('-')[:3]))
      storage.remove(uuid)
    for day in dailies:
      for dir, dirs, files in os.walk(os.sep.join((storage.root,day,storage.dateName))):
        for file in files:
          allfiles.append(file)
          if os.path.islink(os.path.join(dir,file)):
            alllinks.append(file)
        for d in dirs:
          if os.path.islink(os.path.join(dir,d)):
            alllinks.append(d)
          alldirs.append(os.path.join(dir,d))
    assert [] == allfiles, 'Expect that all removed files are gone, but found %s' % allfiles
    assert [] == alllinks, 'Expcet that all links are gone, but found %s' % alllinks
    assert [] == alldirs, 'Expect that all date dirs are gone, but found %s' % alldirs

    for day in dailies:
      for dir,dirs,files in os.walk(os.sep.join((storage.root,day,storage.indexName))):
        for file in files:
          allfiles.append(file)
          if os.path.islink(os.path.join(dir,file)):
            alllinks.append(file)
        for d in dirs:
          if os.path.islink(os.path.join(dir,d)):
            alllinks.append(d)
          alldirs.append(os.path.join(dir,d))
    assert [] == allfiles, 'Expect that all removed files are gone, but found %s' % allfiles
    assert [] == alllinks, 'Expect that all links are gone, but found %s' % alllinks
    for sub in expectedSubs:
      assert sub in alldirs, "Expect each subdirectory is still there, but didn't find %s" % sub

  def testRemoveWithBadlyFormattedDateLink(self):
    createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[2],self.testDir)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[2])
    uuid = createJDS.jsonFileData.keys()[0]
    head,json = os.path.split(storage.getJson(uuid))
    target = os.readlink(os.path.join(head,uuid))
    idx = target.index('/date/')
    target = "%s%s%s" %(target[:idx+6],target[idx+7:idx+10],target[idx+10:])
    os.unlink(os.path.join(head,uuid))
    os.symlink(target,os.path.join(head,uuid))
    #print "LINK:%s"%(os.readlink(os.path.join(head,uuid)))
    # assure that we don't throw for a badly formatted path
    storage.remove(uuid)

#   def testRemoveOlderThan(self):
#     createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[0],self.testDir)
#     storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[0])
#     cutoff = datetime.datetime(2008,12,26,05,0, tzinfo=UTC)
#     youngkeys = [x for x,d in createJDS.jsonFileData.items() if datetime.datetime(*[int(i) for i in d[0].split('-')], tzinfo=UTC) >= cutoff]
#     oldkeys = [x for x,d in createJDS.jsonFileData.items() if datetime.datetime(*[int(i) for i in d[0].split('-')], tzinfo=UTC) < cutoff]

#     for k in youngkeys:
#       assert k in createJDS.jsonFileData.keys(),"Expected %s in %s"%(k,createJDS.jsonFileData.keys())
#     for k in oldkeys:
#       assert k in createJDS.jsonFileData.keys()
#     for k in createJDS.jsonFileData.keys():
#       assert (k in youngkeys or k in oldkeys)
#     storage.removeOlderThan(cutoff)
#     seenuuid = {}
#     seendirs = []
#     for dir,dirs,files in os.walk(storage.nameBranch):
#       for f in files:
#         if os.path.islink(os.path.join(dir,f)):
#           uuid = os.path.splitext(f)[0]
#           seenuuid[uuid] = True
#           assert uuid in youngkeys, 'File: Expect that each remaining link has a young uuid, got %s' % uuid
#           assert not uuid in oldkeys, 'File Expect no remaining link has old uuid, got %s' % uuid
#       for d in dirs:
#         if os.path.islink(os.path.join(dir,d)):
#           uuid = os.path.splitext(d)[0]
#           seenuuid[uuid] = True
#           assert uuid in youngkeys, 'Dir: Expect that each remaining link has a young uuid, got %s' % uuid
#           assert not uuid in oldkeys, 'Dir: Expect no remaining link has old uuid, got %s' % uuid
#     for id in oldkeys:
#       assert not id in seenuuid,'Expect that no old key is found, but %s' % id
#     for id in youngkeys:
#       assert id in seenuuid, 'Expect that every new key is found, but %s' % id

#     seenuuid = {}
#     seendirs = []
#     for dir, dirs, files in os.walk(storage.dateBranch):
#       for f in files:
#         uuid = os.path.splitext(f)[0]
#         seenuuid[uuid] = True
#         assert uuid in youngkeys, 'Expect that each remaining file has a young uuid, got %s' % uuid
#         assert not uuid in oldkeys, 'Expect no remaining file has old uuid, got %s' % uuid
#       for d in dirs:
#         uuid = os.path.splitext(d)[0]
#         if '-' in uuid:
#           seenuuid[uuid] = True
#           assert uuid in youngkeys, 'Expect that each remaining file has a young uuid, got %s' % uuid
#           assert not uuid in oldkeys, 'Expect no remaining file has old uuid, got %s' % uuid
#     for id in oldkeys:
#       assert not id in seenuuid,'Expect that no old key is found but %s' % id
#     for id in youngkeys:
#       assert id in seenuuid, 'Expect that every new key is found, but %s' % id
#       assert os.path.isdir(os.path.join(storage.dateBranch,createJDS.jsonFileData[id][3]))

#   def testMove(self):
#     createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[3],self.testDir)
#     storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[3])
#     os.mkdir(self.testMoveTo)
#     for uuid in createJDS.jsonFileData.keys():
#       storage.move(uuid,os.path.join('.','TEST-MOVETO'))
#     allfiles = []
#     alllinks = []
#     for dir, dirs, files in os.walk(self.testDir):
#       for file in files:
#         allfiles.append(file)
#         if os.path.islink(os.path.join(dir,file)):
#           alllinks.append(file)
#       for d in dirs:
#         if os.path.islink(os.path.join(dir,d)):
#           alllinks.append(d)
#     assert [] == allfiles, 'Expect that all moved files are gone, but found %s' % allfiles
#     assert [] == alllinks, 'Expcet that all links are gone, but found %s' % alllinks
#     allfiles = []
#     alllinks = []
#     expectedFiles = [x+storage.jsonSuffix for x in createJDS.jsonFileData.keys() ]
#     expectedFiles.extend([x+storage.dumpSuffix for x in createJDS.jsonFileData.keys() ])
#     for dir, dirs, files in os.walk(os.path.join('.','TEST-MOVETO')):
#       for file in files:
#         allfiles.append(file)
#         assert file in expectedFiles, 'Expect that each moved file will be expected but found %s' % file
#         if os.path.islink(os.path.join(dir,file)): alllinks.append(file)
#       for d in dirs:
#         if os.path.islink(os.path.join(dir,d)): alllinks.append(d)
#     assert [] == alllinks, 'Expect no links in the move-to directory, but found %s' % alllinks
#     for file in expectedFiles:
#       assert file in allfiles, 'Expect that every file will be moved but did not find %s' % file

#   def testTransferOne(self):
#     createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[0],rootDir=self.testMoveFrom)
#     storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[0])
#     oldStorage = JDS.JsonDumpStorage(self.testMoveFrom, **self.initKwargs[0])
#     itemNumber = 0
#     xmas = datetime.datetime(2001,12,25,12,25, tzinfo=UTC)
#     for id in createJDS.jsonFileData.keys():
#       #case 0: copyLinks = True, makeNewDateLinks = False and there are links
#       #case 1: copyLinks = True, makeNewDateLinks = False  and there are no links
#       #case 2: makeNewDateLinks = True and there were existing date links
#       #case 3: makeNewDateLinks = True and there were no existing date links
#       copyLinks = True
#       makeNewLinks = False
#       removeOldLink = False
#       newDate = None
#       if 0 == itemNumber % 4:
#         pass
#       elif 1 == itemNumber % 4:
#         removeOldLink = True
#       elif 2 == itemNumber % 4:
#         makeNewLinks = True
#         newDate = xmas
#       elif 3 == itemNumber % 4:
#         removeOldLink = True
#         makeNewLinks = True
#         newDate = xmas
#       itemNumber += 1
#       if(removeOldLink):
#         oldStorage.markAsSeen(id)
#         self.__hasNoLinkOrFail(oldStorage,id)
#       storage.transferOne(id,oldStorage,copyLinksBoolean=copyLinks,makeNewDateLinksBoolean=makeNewLinks,aDate=newDate)
#       try:
#         storage.getJson(id)
#       except Exception,x:
#         print '(%s): %s'%(type(x),x)
#         assert False, 'Expected to find a transferred json file for %s' % id
#       if makeNewLinks or not removeOldLink:
#         self.__hasLinkOrFail(storage,id)
#         if makeNewLinks:
#           self.__hasDatePathOrFail(storage,xmas)
#       if not makeNewLinks and removeOldLink:
#         self.__hasNoLinkOrFail(storage,id)

#   def testTransferMany(self):
#     createJDS.createTestSet(createJDS.jsonFileData,self.initKwargs[0],rootDir=self.testMoveFrom)
#     oldStorage = JDS.JsonDumpStorage(self.testMoveFrom, **self.initKwargs[0])
#     itemNumber = 0
#     xmas = datetime.datetime(2001,12,25,12,25, tzinfo=UTC)
#     hasLinks = {}
#     for id in createJDS.jsonFileData.keys():
#       hasLinks[id] = True
#       if 0 == itemNumber %2 :
#         oldStorage.markAsSeen(id)
#         self.__hasNoLinkOrFail(oldStorage,id)
#         hasLinks[id] = False

#     opts = ((False,True),(True,False),(False,False)) #copyLinks, makeNewLinks
#     targets = (self.testMoveTo, self.testMoveToAlt,self.testDir)
#     assert len(opts) == len(targets), "set of opts must be one-to-one with set of targets, or fail"
#     for i in range(len(opts)):
#       aDate = None
#       if opts[i][1]: aDate = xmas
#       storage = JDS.JsonDumpStorage(targets[i], **self.initKwargs[0])
#       storage.transferMany(createJDS.jsonFileData.keys(),oldStorage,copyLinksBoolean=opts[i][0],makeNewDateLinksBoolean=opts[i][1],aDate=aDate)
#       for id in createJDS.jsonFileData.keys():
#         try:
#           storage.getJson(id)
#         except Exception,x:
#           print '(%s): %s'%(type(x),x)
#           assert False, 'Expected to find a transferred json file for %s' % id
#         if opts[i][1] or hasLinks[id]:
#           self.__hasLinkOrFail(storage,id)
#           if opts[i][1]:
#             self.__hasDatePathOrFail(storage,xmas)
#         if not opts[i][1] and not hasLinks[id]:
#           self.__hasNoLinkOrFail(storage,id)

if __name__ == "__main__":
  unittest.main()
