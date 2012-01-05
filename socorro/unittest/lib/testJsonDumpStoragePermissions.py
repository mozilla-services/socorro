import unittest

import datetime as DT
import os
import os.path as p
import shutil
import stat
import time

import socorro.lib.JsonDumpStorage as JDS
import socorro.lib.uuid as socorro_uuid
from socorro.lib.util import SilentFakeLogger
import socorro.lib.filesystem as socorro_fs

import socorro.unittest.testlib.util as tutil
from socorro.lib.datetimeutil import utc_now, UTC

def setup_module():
  tutil.nosePrintModule(__file__)

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
    dirPermissions=0707
    dumpPermissions=0500
    sfl = SilentFakeLogger()
    j = JDS.JsonDumpStorage(root=self.testDir,dirPermissions=dirPermissions,dumpPermissions=dumpPermissions,logger=sfl)
    u = str(socorro_uuid.uuid1())
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
    datePath = os.path.abspath(os.path.join(udir,os.readlink(os.path.splitext(dpath)[0])))
    namePath = os.path.abspath(os.path.splitext(dpath)[0])
    topPath = os.path.abspath(self.testDir)
    dailies = os.listdir(topPath)

    def assertPermVisitor(p):
      gotPerm = stat.S_IMODE(os.stat(p)[0])
      assert dirPermissions == gotPerm, "%s: Expected %0o, got %0o"%(p,dirPermissions,gotPerm)
    for d in dailies:
      # visitPath quietly ignores a file as the leaf
      socorro_fs.visitPath(os.path.join(topPath,d),datePath,assertPermVisitor)
      socorro_fs.visitPath(os.path.join(topPath,d),namePath,assertPermVisitor)

  def testCopyFromPermissions(self):
    dirPermissions=0777
    dumpPermissions=0755
    sfl = SilentFakeLogger()
    j = JDS.JsonDumpStorage(root=self.testDir,dirPermissions=dirPermissions,dumpPermissions=dumpPermissions,logger=sfl)
    os.makedirs(self.testMoveFrom)
    u = str(socorro_uuid.uuid1())
    jopath = os.path.join(self.testMoveFrom,u+j.jsonSuffix)
    dopath = os.path.join(self.testMoveFrom,u+j.dumpSuffix)
    fj = open(jopath,'w')
    fd = open(dopath,'w')
    fj.close()
    fd.close()
    j.copyFrom(u,jopath,dopath,'w', DT.datetime(2008,8,8,8,8, tzinfo=UTC),createLinks = True)

    jpath = j.getJson(u)
    gotPermissions = stat.S_IMODE(os.stat(jpath)[0])
    assert dumpPermissions == stat.S_IMODE(os.stat(jpath)[0]), "%s: Expected %o, got %o" % (jpath, dumpPermissions, gotPermissions)

    dpath = j.getDump(u)
    gotPermissions = stat.S_IMODE(os.stat(dpath)[0])
    assert dumpPermissions == stat.S_IMODE(os.stat(dpath)[0]), "%s: Expected %o, got %o" % (dpath, dumpPermissions, gotPermissions)

    udir = os.path.split(dpath)[0]
    datePath = os.path.abspath(os.path.join(udir,os.readlink(os.path.splitext(dpath)[0])))
    namePath = os.path.abspath(os.path.splitext(dpath)[0])
    topPath = os.path.abspath(self.testDir)
    dailies = os.listdir(topPath)

    def assertPermVisitor(p):
      gotPerm = stat.S_IMODE(os.stat(p)[0])
      assert dirPermissions == gotPerm, "%s: Expected %0o, got %0o"%(p,dirPermissions,gotPerm)
    for d in dailies:
      # visitPath quietly ignores a file as the leaf
      socorro_fs.visitPath(os.path.join(topPath,d),datePath,assertPermVisitor)
      socorro_fs.visitPath(os.path.join(topPath,d),namePath,assertPermVisitor)

if __name__ == "__main__":
  unittest.main()
