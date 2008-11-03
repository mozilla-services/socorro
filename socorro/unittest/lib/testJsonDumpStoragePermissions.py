import unittest
import os
import shutil
import socorro.lib.JsonDumpStorage as JDS
import socorro.lib.uuid as suuid

class TestJsonDumpStoragePermissions(unittest.TestCase):
  def setUp(self):
    self.testDir = os.path.join(',','TESTPERM')
  def tearDown(self):
    j = JDS.JsonDumpStorage()
    try:
      shutil.rmtree(self.testDir)
    except OSError:
      pass # ok if there is no such directory
  def testPermissions(self):
    dirPermissions=0777
    dumpPermissions=0755
    j = JDS.JsonDumpStorage(root=self.testDir,dirPermissions=dirPermissions,dumpPermissions=dumpPermissions)
    u = str(suuid.uuid1())
    f1, f2 = j.newEntry(u)
    f1.close()
    f2.close()

    import os
    import os.path as p
    import stat

    jpath = j.getJson(u)
    gotPermission = stat.S_IMODE(os.stat(jpath)[0])
    assert stat.S_IMODE(os.stat(jpath)[0]) == dumpPermissions, "%s: Expected %o, got %o" % (jpath, dumpPermissions, gotPermission)

    dpath = j.getDump(u)
    gotPermission = stat.S_IMODE(os.stat(dpath)[0])
    assert stat.S_IMODE(os.stat(dpath)[0]) == dumpPermissions, "%s: Expected %o, got %o" % (dpath, dumpPermissions, gotPermission)

    x = p.split(jpath)[0]
    y = p.split(dpath)[0]
    for tp in (x,y):
      while tp != j.nameBranch and tp != j.dateBranch:
        gotPermission = stat.S_IMODE(os.stat(tp)[0])
        assert dirPermissions == gotPermission, "%s: Expected %o, got %o"%(tp,dirPermissions,gotPermission)
        tp = p.split(tp)[0]

if __name__ == "__main__":
  unittest.main()
