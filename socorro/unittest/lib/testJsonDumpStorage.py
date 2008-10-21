import unittest
import os
import shutil
import datetime as DT
import time
import socorro.lib.JsonDumpStorage as JDS

class FakeLogger(object):
  def log(self,*x): pass
  def debug(self,msg): pass
  def info(self,msg): pass
  def warning(self,msg): pass
  def error(self,msg): pass
  def critical(self,msg): pass

class TestJsonDumpStorage(unittest.TestCase):

  def setUp(self):
    self.testDir = os.path.join('.','TEST-JSONDUMP')
    self.testMoveTo = os.path.join('.','TEST-MOVETO')
    self.testMoveFrom = os.path.join('.','TEST-MOVEFROM')
    self.initKwargs =  {
      0:{'logger': FakeLogger()},
      1:{'logger': FakeLogger(),'dateName':'DATE','indexName':'INDEX','jsonSuffix':'JS','dumpSuffix':'.DS',},
      2:{'logger': FakeLogger(),'jsonSuffix':'JS','dumpSuffix':'.DS',},
      3:{'logger': FakeLogger(),'dateName':'DATE','indexName':'INDEX',},
      }
    self.data = {
      '0bba61c5-dfc3-43e7-87e6-8afda3564352': ('2007-10-25-05-04','webhead02','0b/ba/61/c5','2007/10/25/05/00/webhead02_0'),
      '0bba929f-8721-460c-8e70-a43c95d04ed2': ('2007-10-25-05-04','webhead02','0b/ba/92/9f','2007/10/25/05/00/webhead02_0'),
      '0b9ff107-8672-4aac-8b75-b2bd825c3d58': ('2008-12-25-05-00','webhead01','0b/9f/f1/07','2008/12/25/05/00/webhead01_0'),
      '22adfb61-f75b-11dc-b6be-001321b0783d': ('2008-12-25-05-01','webhead01','22/ad/fb/61','2008/12/25/05/00/webhead01_0'),
      'b965de73-ae90-a935-1357-03ae102b893f': ('2008-12-25-05-04','webhead01','b9/65/de/73','2008/12/25/05/00/webhead01_0'),
      '0b781b88-ecbe-4cc4-893f-6bbbfd50e548': ('2008-12-25-05-05','webhead01','0b/78/1b/88','2008/12/25/05/05/webhead01_0'),
      '0b8344d6-9021-4db9-bf34-a15394f96ff5': ('2008-12-25-05-06','webhead01','0b/83/44/d6','2008/12/25/05/05/webhead01_0'),
      '0b94199b-b90b-4683-a38a-4114d3fd5253': ('2008-12-26-05-21','webhead01','0b/94/19/9b','2008/12/26/05/20/webhead01_0'),
      '0b9eedc3-9a79-4ce2-83eb-1559e5234fde': ('2008-12-26-05-24','webhead01','0b/9e/ed/c3','2008/12/26/05/20/webhead01_0'),
      '0b9fd6da-27e4-46aa-bef3-3deb9ef0d364': ('2008-12-26-05-25','webhead02','0b/9f/d6/da','2008/12/26/05/25/webhead02_0'),
      '0ba32a30-2476-4724-b825-de1727afa9cb': ('2008-11-25-05-00','webhead02','0b/a3/2a/30','2008/11/25/05/00/webhead02_0'),
      '0bad640f-5825-4d42-b96e-21b8b1d250df': ('2008-11-25-05-04','webhead02','0b/ad/64/0f','2008/11/25/05/00/webhead02_0'),
      '0bae7049-bbff-49f2-b408-7e9f41602507': ('2008-11-25-05-05','webhead02','0b/ae/70/49','2008/11/25/05/05/webhead02_0'),
      '0baf1b4d-dad3-4d35-ae7e-b9dcb217d27f': ('2008-11-25-05-06','webhead02','0b/af/1b/4d','2008/11/25/05/05/webhead02_0'),
      }
    self.badUuid = '66666666-6666-6666-6666-666666666666'
    self.toomany = {
      '23adfb61-f75b-11dc-b6be-001321b0783d': ('2008-12-25-05-01','webhead01','23/ad/fb/61','2008/12/25/05/00'),
      '24adfb61-f75b-11dc-b6be-001321b0783d': ('2008-12-25-05-01','webhead01','24/ad/fb/61','2008/12/25/05/00'),
      '25adfb61-f75b-11dc-b6be-001321b0783d': ('2008-12-25-05-02','webhead01','25/ad/fb/61','2008/12/25/05/00'),
      '26adfb61-f75b-11dc-b6be-001321b0783d': ('2008-12-25-05-02','webhead01','26/ad/fb/61','2008/12/25/05/00'),
      '27adfb61-f75b-11dc-b6be-001321b0783d': ('2008-12-25-05-03','webhead01','27/ad/fb/61','2008/12/25/05/00'),
      }
    self.evenmore =  {
      '28adfb61-f75b-11dc-b6be-001321b0783d': ('2008-12-25-05-01','webhead01','28/ad/fb/61','2008/12/25/05/00'),
      '29adfb61-f75b-11dc-b6be-001321b0783d': ('2008-12-25-05-00','webhead01','29/ad/fb/61','2008/12/25/05/00'),
      }

    self.currenttimes = {
      '0bba61c5-dfc3-43e7-87e6-8afda3564352': ['+0','webhead02','0b/ba/61/c5','webhead02_0'],
      '0bba929f-8721-460c-8e70-a43c95d04ed2': ['+0','webhead02','0b/ba/92/9f','webhead02_0'],
      '0b9ff107-8672-4aac-8b75-b2bd825c3d58': ['+0','webhead01','0b/9f/f1/07','webhead01_0'],
      '22adfb61-f75b-11dc-b6be-001321b0783d': ['+0','webhead01','22/ad/fb/61','webhead01_0'],
      'b965de73-ae90-a935-1357-03ae102b893f': ['+0','webhead01','b9/65/de/73','webhead01_0'],
      '0b781b88-ecbe-4cc4-893f-6bbbfd50e548': ['+5','webhead01','0b/78/1b/88','webhead01_0'],
      '0b8344d6-9021-4db9-bf34-a15394f96ff5': ['+5','webhead01','0b/83/44/d6','webhead01_0'],
      '0b94199b-b90b-4683-a38a-4114d3fd5253': ['+5','webhead01','0b/94/19/9b','webhead01_0'],
      '0b9eedc3-9a79-4ce2-83eb-1559e5234fde': ['+5','webhead01','0b/9e/ed/c3','webhead01_0'],
      '0b9fd6da-27e4-46aa-bef3-3deb9ef0d364': ['+10','webhead02','0b/9f/d6/da','webhead02_0'],
      '0ba32a30-2476-4724-b825-de1727afa9cb': ['+10','webhead02','0b/a3/2a/30','webhead02_0'],
      '0bad640f-5825-4d42-b96e-21b8b1d250df': ['+10','webhead02','0b/ad/64/0f','webhead02_0'],
      '0bae7049-bbff-49f2-b408-7e9f41602507': ['+10','webhead02','0b/ae/70/49','webhead02_0'],
      '0baf1b4d-dad3-4d35-ae7e-b9dcb217d27f': ['+10','webhead02','0b/af/1b/4d','webhead02_0'],
      }

    try:
      shutil.rmtree(self.testDir)
    except OSError:
      pass # ok if there is no such test directory
    os.mkdir(self.testDir)

  def tearDown(self):
    try:
      shutil.rmtree(self.testDir)
    except OSError, e:
      pass # ok if there is no such test directory
    try:
      shutil.rmtree(self.testMoveTo)
    except OSError:
      pass
    try:
      shutil.rmtree(self.testMoveFrom)
    except OSError:
      pass

  def __getSlot(self,minsperslot,minute):
    return minsperslot * int(minute/minsperslot)

  def __createTestSet(self,testData, initIndex=1):
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[initIndex])
    thedt = DT.datetime.now()
    for uuid,data in testData.items():
      if data[0].startswith('+'):
        if thedt.second >= 58:
          print "\nSleeping for %d seconds" %(61-thedt.second)
          time.sleep(61-thedt.second)
          thedt = DT.datetime.now()
        slot = {
          '+0': self.__getSlot(storage.minutesPerSlot,thedt.minute),
          '+5': self.__getSlot(storage.minutesPerSlot,thedt.minute+5),
          '+10':self.__getSlot(storage.minutesPerSlot,thedt.minute+10),
        }
        d3h = '%d/%02d/%02d/%02d/%s' %(thedt.year,thedt.month,thedt.day,thedt.hour,slot[data[0]])
        data[3] = "%s/%s" % (d3h,data[3])
      else:
        thedt = DT.datetime(*[int(x) for x in data[0].split('-')])
      fj,fd = storage.newEntry(uuid,webheadHostName=data[1],timestamp = thedt)
      try:
        fj.write('json test of %s\n' % uuid)
      finally:
        if fj: fj.close()
      try:
        fd.write('dump test of %s\n' % uuid)
      finally:
        if fd: fd.close()

  def testConstructor(self):
    self.constructorAlt(self.testDir,**self.initKwargs[0])
    self.constructorAlt(self.testDir,**self.initKwargs[1])
    self.constructorAlt(self.testDir,**self.initKwargs[2])
    self.constructorAlt(self.testDir,**self.initKwargs[3])

  def constructorAlt(self,*args,**kwargs):
    storage = JDS.JsonDumpStorage(self.testDir,**kwargs)
    assert os.path.join(self.testDir,kwargs.get('dateName','date')) == storage.dateBranch
    assert os.path.join(self.testDir,kwargs.get('indexName','name')) == storage.nameBranch
    assert storage.dateName == kwargs.get('dateName','date'),'From kwargs=%s'%kwargs
    assert storage.indexName == kwargs.get('indexName','name'),'From kwargs=%s'%kwargs
    assert storage.jsonSuffix == '.'+kwargs.get('jsonSuffix','json'),'We will always pass non-dot json suffix. From kwargs=%s'%kwargs
    assert storage.dumpSuffix == kwargs.get('dumpSuffix','.dump'),'We will always pass dot dump suffix. From kwargs=%s'%kwargs
    assert os.path.join(self.testDir,storage.dateName) == storage.dateBranch,'From kwargs=%s'%kwargs
    assert os.path.join(self.testDir,storage.indexName) == storage.nameBranch,'From kwargs=%s'%kwargs


  def testNewEntry(self):
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[2])
    for uuid,data in self.data.items():
      datetimedata = [int(x) for x in data[0].split('-')]
      try:
        fj,fd = storage.newEntry(uuid,webheadHostName=data[1],timestamp = DT.datetime(*datetimedata))
      except IOError:
        assert False, 'Expect to succeed with newEntry(%s,...)' % uuid

      assert fj, 'Expect a non-null json file handle from newEntry(%s,...)' % uuid
      expectJson = os.sep.join((storage.nameBranch,data[2],uuid+storage.jsonSuffix))
      assert expectJson == fj.name, 'For %s, expect %s, got %s' % (uuid,expectJson,fj.name)
      assert fd, 'Expect a non-null dump file handle from newEntry(%s,...)' % uuid
      expectDump = os.sep.join((storage.nameBranch,data[2],uuid+storage.dumpSuffix))
      assert expectDump == fd.name, 'For %s, expect %s, got %s' % (uuid,expectDump,fj.name)
      lpath = os.sep.join((storage.dateBranch,data[3],uuid))
      assert os.path.islink(lpath), 'Expect a link from timed to storage for %s' % uuid
      assert storage.toNameFromDate in os.readlink(lpath)
      lpath = os.sep.join((storage.nameBranch,data[2],uuid))
      assert os.path.islink(lpath), 'Expect link from name storage to timed for %s' % uuid
      assert storage.toDateFromName in os.readlink(lpath)
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

  def testNewEntryDirectoryOverflow(self):
    ''' tests that we write new date links in appropriate overflow dir when we get too many in the regular dir'''
    self.__createTestSet(self.data,initIndex=3)
    storage = JDS.JsonDumpStorage(self.testDir,maxDirectoryEntries=3,**self.initKwargs[3])
    for uuid,data in self.toomany.items():
      abspathpart = data[3]
      datetimedata = [int(x) for x in data[0].split('-')]
      storage.newEntry(uuid,webheadHostName=data[1],timestamp = DT.datetime(*datetimedata))
    datePathUpOne = os.path.join(storage.dateBranch,abspathpart)
    webheads = os.listdir(datePathUpOne)
    assert 3 == len(webheads)
    for datePath in [os.path.join(datePathUpOne,x) for x in webheads]:
      assert 3 >= len(os.listdir(datePath))
    storage2 = JDS.JsonDumpStorage(self.testDir,maxDirectoryEntries=3, **self.initKwargs[3])
    for uuid,data in self.evenmore.items():
      abspathpart = data[3]
      datetimedata = [int(x) for x in data[0].split('-')]
      storage2.newEntry(uuid,webheadHostName=data[1],timestamp = DT.datetime(*datetimedata))
    webheads = os.listdir(datePathUpOne)
    assert 4 == len(webheads)
    for datePath in [os.path.join(datePathUpOne,x) for x in webheads]:
      assert 3 >= len(os.listdir(datePath))

  def testCopyFrom(self):
    os.makedirs(self.testMoveFrom)
    fromdata = [('aabbccdd-something','2007-10-20-12-15','webalos',True,False),
                ('aabbccee-something','2007-10-20-12-15','webalos',True,False),
                ('aabbccff-something','2007-10-20-10-15','webalos',False,True),
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
      stamp = DT.datetime(*[int(x) for x in stampS.split('-')])
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

  def testGetJson(self):
    self.__createTestSet(self.data, initIndex=0)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[0])
    for uuid,data in self.data.items():
      expected = os.sep.join((storage.nameBranch,data[2],uuid+storage.jsonSuffix))
      got = storage.getJson(uuid)
      assert expected == got, 'Expected json file %s, got %s' % (expected,got)
    try:
      storage.getJson(self.badUuid)
      assert False, 'Expect to throw IOError from attempt to getJson(non-existent-uuid)'
    except OSError,e:
      assert True, 'Got expected error from attempt to getJson(non-existent-uuid)'
    except Exception, e:
      assert False, 'Got unexpected error %s from attempt to getJson(non-existent-uuid' % e

  def testGetDump(self):
    self.__createTestSet(self.data,initIndex=1)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[1])
    for uuid,data in self.data.items():
      expected = os.sep.join((storage.nameBranch,data[2],uuid+storage.dumpSuffix))
      got =  storage.getDump(uuid)
      assert expected == got, 'Expected dump file %s, got %s' % (expected,got)
    try:
      storage.getDump(self.badUuid)
      assert False, 'Should throw IOError from attempt to getDump(non-existent-uuid)'
    except OSError,e:
      assert True
    except Exception, e:
      assert False, 'Got unexpected error(type) %s from attempt to getDump(non-existent-uuid' % e

  def markAsSeen(self):
    self.__createTestSet(self.data,initIndex=3)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[3])
    for uuid,data in self.data.items():
      assert os.path.islink(os.sep.join((storage.dateBranch,data[3],uuid))), 'Expect a link from date to name for %s' % uuid
      assert os.path.islink(os.sep.join((storage.nameBranch,data[2],uuid))), 'Expect link from name to timed for %s' % uuid
      assert not os.path.islink(os.sep.join((storage.dateBranch,data[3],uuid))), 'Expect no link from date to name for %s' % uuid
      assert not os.path.islink(os.sep.join((storage.nameBranch,data[2],uuid))), 'Expect no link from name to date for %s' % uuid
    try:
      storage.markAsSeen(self.badUuid)
      assert False, 'Expect to throw IOError from attempt to openAndMarkAsSeen(non-existent-uuid)'
    except IOError:
      assert True, 'Got expected error from attempt to openAndMarkAsSeen(non-existent-uuid)'
    except Exception, e:
      assert False, 'Got unexpected error %s from attempt to openAndMarkAsSeen(non-existent-uuid' % e
    assert not os.listdir(storage.dateBranch), 'Expect empty, got %s' % os.listdir(storage.dateBranch)

  def testDestructiveDateWalk(self):
    self.__createTestSet(self.data,initIndex=0)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[0])
    uuids = self.data.keys()
    seenids = []
    for id in storage.destructiveDateWalk():
      assert id in uuids, 'Expect that %s is among the uuids we stored' % uuid
      seenids.append(id)
    for id in uuids:
      assert id in seenids, 'Expect that we found every uuid we stored (%s) from %s' % (id,seenids)
    assert not os.listdir(storage.dateBranch), 'Expect that destructive walk will remove all date links, and their dirs'

  def testDestructiveDateWalkNotNow(self):
    self.__createTestSet(self.currenttimes,initIndex=1)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[1])
    uuids = self.currenttimes.keys()
    seenids = []
    for id in storage.destructiveDateWalk():
      seenids.append(id)
    assert [] == seenids

  def testRemove(self):
    self.__createTestSet(self.data,initIndex=2)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[2])
    for uuid in self.data.keys():
      storage.remove(uuid)
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
    assert [] == alllinks, 'Expcet that all links are gone, but found %s' % alllinks
    try:
      storage.remove("bogusdata")
    except:
      assert False, 'Should be able to remove bogus data'

  def testMove(self):
    self.__createTestSet(self.data,initIndex=3)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[3])
    os.mkdir(self.testMoveTo)
    for uuid in self.data.keys():
      storage.move(uuid,os.path.join('.','TEST-MOVETO'))
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
    assert [] == allfiles, 'Expect that all moved files are gone, but found %s' % allfiles
    assert [] == alllinks, 'Expcet that all links are gone, but found %s' % alllinks
    allfiles = []
    alllinks = []
    expectedFiles = [x+storage.jsonSuffix for x in self.data.keys() ]
    expectedFiles.extend([x+storage.dumpSuffix for x in self.data.keys() ])
    for dir, dirs, files in os.walk(os.path.join('.','TEST-MOVETO')):
      for file in files:
        allfiles.append(file)
        assert file in expectedFiles, 'Expect that each moved file will be expected but found %s' % file
        if os.path.islink(os.path.join(dir,file)): alllinks.append(file)
      for d in dirs:
        if os.path.islink(os.path.join(dir,d)): alllinks.append(d)
    assert [] == alllinks, 'Expect no links in the move-to directory, but found %s' % alllinks
    for file in expectedFiles:
      assert file in allfiles, 'Expect that every file will be moved but did not find %s' % file

  def testRemoveOlderThan(self):
    self.__createTestSet(self.data,initIndex=0)
    storage = JDS.JsonDumpStorage(self.testDir,**self.initKwargs[0])
    cutoff = DT.datetime(2008,12,26,05,0)
    youngkeys = [x for x,d in self.data.items() if DT.datetime(*[int(i) for i in d[0].split('-')]) >= cutoff]
    oldkeys = [x for x,d in self.data.items() if DT.datetime(*[int(i) for i in d[0].split('-')]) < cutoff]

    for k in youngkeys:
      assert k in self.data.keys(),"Expected %s in %s"%(k,self.data.keys())
    for k in oldkeys:
      assert k in self.data.keys()
    for k in self.data.keys():
      assert (k in youngkeys or k in oldkeys)
    storage.removeOlderThan(cutoff)
    seenuuid = {}
    seendirs = []
    for dir,dirs,files in os.walk(storage.nameBranch):
      for f in files:
        if os.path.islink(os.path.join(dir,f)):
          uuid = os.path.splitext(f)[0]
          seenuuid[uuid] = True
          assert uuid in youngkeys, 'File: Expect that each remaining link has a young uuid, got %s' % uuid
          assert not uuid in oldkeys, 'File Expect no remaining link has old uuid, got %s' % uuid
      for d in dirs:
        if os.path.islink(os.path.join(dir,d)):
          uuid = os.path.splitext(d)[0]
          seenuuid[uuid] = True
          assert uuid in youngkeys, 'Dir: Expect that each remaining link has a young uuid, got %s' % uuid
          assert not uuid in oldkeys, 'Dir: Expect no remaining link has old uuid, got %s' % uuid
    for id in oldkeys:
      assert not id in seenuuid,'Expect that no old key is found, but %s' % id
    for id in youngkeys:
      assert id in seenuuid, 'Expect that every new key is found, but %s' % id

    seenuuid = {}
    seendirs = []
    for dir, dirs, files in os.walk(storage.dateBranch):
      for f in files:
        uuid = os.path.splitext(f)[0]
        seenuuid[uuid] = True
        assert uuid in youngkeys, 'Expect that each remaining file has a young uuid, got %s' % uuid
        assert not uuid in oldkeys, 'Expect no remaining file has old uuid, got %s' % uuid
      for d in dirs:
        uuid = os.path.splitext(d)[0]
        if '-' in uuid:
          seenuuid[uuid] = True
          assert uuid in youngkeys, 'Expect that each remaining file has a young uuid, got %s' % uuid
          assert not uuid in oldkeys, 'Expect no remaining file has old uuid, got %s' % uuid
    for id in oldkeys:
      assert not id in seenuuid,'Expect that no old key is found but %s' % id
    for id in youngkeys:
      assert id in seenuuid, 'Expect that every new key is found, but %s' % id
      assert os.path.isdir(os.path.join(storage.dateBranch,self.data[id][3]))

if __name__ == "__main__":
  unittest.main()
