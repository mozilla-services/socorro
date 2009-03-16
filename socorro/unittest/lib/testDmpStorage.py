import gzip
import os
import shutil

import unittest
from nose.tools import *

import socorro.unittest.testlib.createJsonDumpStore as createJDS

import socorro.lib.util as socorro_util
import socorro.lib.dmpStorage as dmpStorage

class TestDmpStorage(unittest.TestCase):
  def setUp(self):
    self.testDir = os.path.join('.','TEST-DMPDMP')+'/'
    fakeLogger = socorro_util.SilentFakeLogger()
    self.initKwargs =  {
      0:{'logger': fakeLogger},
      1:{'logger': fakeLogger,'dataName':'by_data','dmpSuffix':'DSgz',},
      2:{'logger': fakeLogger,'dmpSuffix':'.DSgz',},
      3:{'logger': fakeLogger,'gzipCompression':'3',},
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

  def testConstructor(self):
    self.constructorAlt(self.testDir,**self.initKwargs[0])
    self.constructorAlt(self.testDir,**self.initKwargs[1])
    self.constructorAlt(self.testDir,**self.initKwargs[2])
    self.constructorAlt(self.testDir,**self.initKwargs[3])

  def constructorAlt(self,*args,**kwargs):
    storage = dmpStorage.DmpStorage(self.testDir,**kwargs)
    assert os.path.join(self.testDir,kwargs.get('dmpName','dmps')) == storage.dmpBranch
    assert storage.dmpName == kwargs.get('dmpName','dmps'),'From kwargs=%s'%kwargs
    suffix = kwargs.get('dmpSuffix','.dmpgz')
    if not suffix.startswith('.'):suffix = '.%s'%suffix
    assert suffix == storage.dmpSuffix,'expected "%s", got "%s" From kwargs=%s'%(suffix,storage.dmpSuffix,kwargs)
    assert os.path.join(self.testDir,storage.dmpName) == storage.dmpBranch,'From kwargs=%s'%kwargs
    compression = int(kwargs.get('gzipCompression','9'))
    assert compression == storage.gzipCompression

  def testNewEntry(self):
    storage = dmpStorage.DmpStorage(self.testDir,**self.initKwargs[0])
    for ooid,(ig0,ig1,pathprefix,ig2) in createJDS.jsonFileData.items():
      expectedDir = os.path.join(storage.dmpBranch,pathprefix)
      expectedPath = os.path.join(expectedDir,"%s%s"%(ooid,storage.dmpSuffix))
      fh = storage.newEntry(ooid)
      try:
        assert expectedPath == fh.fileobj.name, 'Expected: %s, got: %s'%(expected,fh.name)
      finally:
        fh.close()

  def testMakeDmp(self):
    storage = dmpStorage.DmpStorage(self.testDir,**self.initKwargs[2])
    ooid = createJDS.jsonFileData.keys()[0]
    pfx = createJDS.jsonFileData[ooid][2]
    expectedPath = os.sep.join([storage.dmpBranch,pfx,ooid+storage.dmpSuffix])
    assert not os.path.exists(expectedPath), 'Better not exist at start of test'
    data = ['line ONE','lineTWO\n','', 'last line  \n\n']
    storage.makeDmp(ooid,iter(data))
    assert os.path.exists(expectedPath), 'Just a nicer way to say your test is FUBAR'
    f = gzip.open(expectedPath)
    lines = f.readlines()
    f.close()
    assert len(data) == len(lines),'But expected %s got %s'%(str(data),str(lines))
    for i in range(len(lines)):
      assert data[i].strip()+"\n" == lines[i], 'But expected "%s", got "%s"'%(data[i].strip+'\n', lines[i])

  def testGetDmpFile(self):
    storage = dmpStorage.DmpStorage(self.testDir,**self.initKwargs[1])
    seq = 0
    seqs = {}
    for ooid,(ig0,ig1,pathprefix,ig2) in createJDS.jsonFileData.items():
      seqs[ooid] = seq
      expectedDir = os.path.join(storage.dmpBranch,pathprefix)
      expectedPath = os.path.join(expectedDir,"%s%s"%(ooid,storage.dmpSuffix))
      fh = storage.newEntry(ooid)
      fh.write("Sequence Number %d\n"%seq)
      fh.close()
      seq += 1
    for ooid in createJDS.jsonFileData.keys():
      path = storage.getDmpFile(ooid)
      f = gzip.open(path,'r')
      lines = f.readlines()
      f.close()
      assert 1 == len(lines)
      assert 'Sequence Number %d\n'%(seqs[ooid]) == lines[0],'But expected "Sequence Number %d\n", got "%s"'%(seqs[ooid],lines[0])
    assert_raises(OSError, storage.getDmpFile,createJDS.jsonBadUuid)

  def createDmpSet(self, dmpStorage):
    data = ['I am a dump file','My ooid is %s']
    for ooid in createJDS.jsonFileData.keys():
      d = [x for x in data]
      d[1] = d[1]%(ooid)
      dmpStorage.makeDmp(ooid,d)

  def testRemove(self):
    storage = dmpStorage.DmpStorage(self.testDir,**self.initKwargs[0])
    self.createDmpSet(storage)
    expectedCount = len(createJDS.jsonFileData)
    dmpFiles = set()

    # should fail quitely
    storage.removeDmpFile(createJDS.jsonBadUuid)

    ooids = createJDS.jsonFileData.keys()
    for dir,dirs,files in os.walk(storage.dmpBranch):
      dmpFiles.update(files)
    assert expectedCount == len(dmpFiles)

    #should happily remove them each and all
    for ooid in ooids:
      dmpFiles = set()
      storage.removeDmpFile(ooid)
      expectedCount -= 1
      for dir,dirs,files in os.walk(storage.dmpBranch):
        dmpFiles.update(files)
      assert expectedCount == len(dmpFiles)

if __name__ == "__main__":
  unittest.main()
