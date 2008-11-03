import unittest

import datetime as DT
import os
import os.path as p
import shutil
import stat
import socorro.lib.JsonDumpStorage as JDS
import socorro.lib.uuid as suuid

class TestJsonDumpStoragePermissions(unittest.TestCase):
  def setUp(self):
    self.testDir = os.path.join('.','TESTPERM')
    self.testMoveFrom = os.path.join('.','TESTPERM-MOVEFROM')
  def tearDown(self):
    try:
      shutil.rmtree(self.testDir)
    except OSError:
      pass # ok if there is no such directory
    try:
      shutil.rmtree(self.testMoveFrom)
    except OSError:
      pass


  def testNewEntryPermissions(self):
    dirPermissions=0777
    dumpPermissions=0755
    j = JDS.JsonDumpStorage(root=self.testDir,dirPermissions=dirPermissions,dumpPermissions=dumpPermissions)
    u = str(suuid.uuid1())
    f1, f2 = j.newEntry(u)
    f1.close()
    f2.close()

    jpath = j.getJson(u)
    gotPermissions = stat.S_IMODE(os.stat(jpath)[0])
    assert stat.S_IMODE(os.stat(jpath)[0]) == dumpPermissions, "%s: Expected %o, got %o" % (jpath, dumpPermissions, gotPermissions)

    dpath = j.getDump(u)
    gotPermissions = stat.S_IMODE(os.stat(dpath)[0])
    assert stat.S_IMODE(os.stat(dpath)[0]) == dumpPermissions, "%s: Expected %o, got %o" % (dpath, dumpPermissions, gotPermissions)

    udir = os.path.split(dpath)[0]
    datePath = os.path.join(udir,os.readlink(os.path.abspath(os.path.splitext(dpath)[0])))

    x = p.split(jpath)[0]
    y = os.path.abspath(datePath)
    for tp in (x,y):
      while tp != j.nameBranch and tp != os.path.abspath(j.dateBranch):
        gotPermissions = stat.S_IMODE(os.stat(tp)[0])
        assert dirPermissions == gotPermissions, "%s: Expected %o, got %o"%(tp,dirPermissions,gotPermissions)
        tp = p.split(tp)[0]

  def testCopyFromPermissions(self):
    dirPermissions=0777
    dumpPermissions=0755
    j = JDS.JsonDumpStorage(root=self.testDir,dirPermissions=dirPermissions,dumpPermissions=dumpPermissions)
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
    gotPermissions = stat.S_IMODE(os.stat(jpath)[0])
    assert dumpPermissions == stat.S_IMODE(os.stat(jpath)[0]), "%s: Expected %o, got %o" % (jpath, dumpPermissions, gotPermissions)

    dpath = j.getDump(u)
    gotPermissions = stat.S_IMODE(os.stat(dpath)[0])
    assert dumpPermissions == stat.S_IMODE(os.stat(dpath)[0]), "%s: Expected %o, got %o" % (dpath, dumpPermissions, gotPermissions)

    udir = os.path.split(dpath)[0]
    datePath = os.path.join(udir,os.readlink(os.path.abspath(os.path.splitext(dpath)[0])))

    x = p.split(jpath)[0]
    y = os.path.abspath(datePath)
    for tp in (x,y):
      while tp != j.nameBranch and tp != os.path.abspath(j.dateBranch):
        gotPermissions = stat.S_IMODE(os.stat(tp)[0])
        assert dirPermissions == gotPermissions, "%s: Expected %o, got %o"%(tp,dirPermissions,gotPermissions)
        tp = p.split(tp)[0]

if __name__ == "__main__":
  unittest.main()
