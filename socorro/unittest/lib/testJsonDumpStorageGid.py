import unittest
import datetime as DT
import os
import os.path as p
import pwd
import shutil
import stat
import socorro.lib.JsonDumpStorage as JDS
import socorro.lib.uuid as suuid

class TestJsonDumpStorageGid(unittest.TestCase):
  def setUp(self):
    assert 'root' == pwd.getpwuid(os.geteuid())[0], 'You must run this test as root'
    self.testDir = os.path.join('.','TESTGID')
    self.testMoveFrom = os.path.join('.','TESTGID-MOVEFROM')
    self.newGid = 0777
  def tearDown(self):
    try:
      shutil.rmtree(self.testDir)
    except OSError:
      pass # ok if there is no such directory
    try:
      shutil.rmtree(self.testMoveFrom)
    except OSError:
      pass

  def testNewEntryGid(self):
    j = JDS.JsonDumpStorage(root=self.testDir,dumpGID=self.newGid)
    u = str(suuid.uuid1())
    f1,f2 = j.newEntry(u)
    f1.close()
    f2.close()

    jpath = j.getJson(u)
    gotGid = os.stat(jpath)[stat.ST_GID]
    assert self.newGid ==  gotGid, "%s: Expected %o, got %o" % (jpath, self.newGid, gotGid)

    dpath = j.getDump(u)
    gotGid = os.stat(dpath)[stat.ST_GID]
    assert self.newGid == gotGid, "%s: Expected %o, got %o" % (dpath, self.newGid, gotGid)

    udir = os.path.split(dpath)[0]
    datePath = os.path.join(udir,os.readlink(os.path.abspath(os.path.splitext(dpath)[0])))

    x = p.split(jpath)[0]
    y = os.path.abspath(datePath)
    for tp in (x,y):
      while tp != j.nameBranch and tp != os.path.abspath(j.dateBranch):
        gotGid = os.stat(tp)[stat.ST_GID]
        assert self.newGid == gotGid, "%s: Expected %o, got %o"%(tp,077,gotGid)
        tp = p.split(tp)[0]

  def testCopyFromGid(self):
    j = JDS.JsonDumpStorage(root=self.testDir,dumpGID = self.newGid)
    os.makedirs(self.testMoveFrom)
    u = str(suuid.uuid1())
    jopath = os.path.join(self.testMoveFrom,u+j.jsonSuffix)
    dopath = os.path.join(self.testMoveFrom,u+j.dumpSuffix)
    fj = open(jopath,'w')
    fd = open(dopath,'w')
    fj.close()
    fd.close()
    j.copyFrom(u,jopath,dopath,'w', DT.datetime(2008,8,8,8,8),createLinks = True)

    jpath = j.getJson(u)
    gotGid = os.stat(jpath)[stat.ST_GID]
    assert self.newGid ==  gotGid, "%s: Expected %o, got %o" % (jpath, self.newGid, gotGid)

    dpath = j.getDump(u)
    gotGid = os.stat(dpath)[stat.ST_GID]
    assert self.newGid == gotGid, "%s: Expected %o, got %o" % (dpath, self.newGid, gotGid)

    udir = os.path.split(dpath)[0]
    datePath = os.path.join(udir,os.readlink(os.path.abspath(os.path.splitext(dpath)[0])))

    x = p.split(jpath)[0]
    y = os.path.abspath(datePath)
    for tp in (x,y):
      while tp != j.nameBranch and tp != os.path.abspath(j.dateBranch):
        gotGid = os.stat(tp)[stat.ST_GID]
        assert self.newGid == gotGid, "%s: Expected %o, got %o"%(tp,077,gotGid)
        tp = p.split(tp)[0]

if __name__ == "__main__":
  unittest.main()


