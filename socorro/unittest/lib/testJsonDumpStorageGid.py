# there is no use to this test if you have to be freakin' root to run it!


#import time
#import unittest
#import datetime as DT
#import os
#import os.path as p
#import pwd
#import shutil
#import stat
#import socorro.lib.JsonDumpStorage as JDS
#import socorro.lib.uuid as socorro_uuid
#import socorro.lib.filesystem as socorro_fs
#import socorro.unittest.testlib.util as tutil

#def setup_module():
  #tutil.nosePrintModule(__file__)

#class TestJsonDumpStorageGid(unittest.TestCase):
  #def setUp(self):
    #assert 'root' == pwd.getpwuid(os.geteuid())[0], "You must run this test as root (don't forget root's PYTHONPATH)"
    #self.testDir = os.path.join('.','TESTGID')
    #self.testMoveFrom = os.path.join('.','TESTGID-MOVEFROM')
    #self.newGid = 0777
  #def tearDown(self):
    #try:
      #shutil.rmtree(self.testDir)
    #except OSError:
      #pass # ok if there is no such directory
    #try:
      #shutil.rmtree(self.testMoveFrom)
    #except OSError:
      #pass

  #def testNewEntryGid(self):
    #j = JDS.JsonDumpStorage(root=self.testDir,dumpGID=self.newGid)
    #u = str(socorro_uuid.uuid1())
    #f1,f2 = j.newEntry(u)
    #f1.close()
    #f2.close()
    #jpath = j.getJson(u)
    #gotGid = os.stat(jpath)[stat.ST_GID]
    #assert self.newGid ==  gotGid, "%s: Expected %o, got %o" % (jpath, self.newGid, gotGid)
    #dpath = j.getDump(u)
    #gotGid = os.stat(dpath)[stat.ST_GID]
    #assert self.newGid == gotGid, "%s: Expected %o, got %o" % (dpath, self.newGid, gotGid)

    #udir = os.path.split(dpath)[0]
    #datePath = os.path.abspath(os.path.join(udir,os.readlink(os.path.splitext(dpath)[0])))
    #namePath = os.path.abspath(os.path.splitext(dpath)[0])
    #topPath = os.path.abspath(self.testDir)
    #dailies = os.listdir(topPath)
    #def assertGidVisitor(p):
      #gotGid = os.stat(p)[stat.ST_GID]
      #assert self.newGid == gotGid, "%s: expected %0o, got %0o"%(p,self.newGid,gotGid)

    #gotGid = os.stat(datePath)[stat.ST_GID]
    #assert self.newGid == gotGid, '%s: expected %0o, got %0o'%(datePath,self.newGid,gotGid)
    #gotGid = os.stat(namePath)[stat.ST_GID]
    #assert self.newGid == gotGid, '%s: expected %0o, got %0o'%(datePath,self.newGid,gotGid)
    #for d in dailies:
      ## visitPath quietly ignores a file as the leaf
      #socorro_fs.visitPath(os.path.join(topPath,d),datePath,assertGidVisitor)
      #socorro_fs.visitPath(os.path.join(topPath,d),namePath,assertGidVisitor)

  #def testCopyFromGid(self):
    #j = JDS.JsonDumpStorage(root=self.testDir,dumpGID = self.newGid)
    #socorro_fs.makedirs(self.testMoveFrom)
    #u = str(socorro_uuid.uuid1())
    #jopath = os.path.join(self.testMoveFrom,u+j.jsonSuffix)
    #dopath = os.path.join(self.testMoveFrom,u+j.dumpSuffix)
    #fj = open(jopath,'w')
    #fd = open(dopath,'w')
    #fj.close()
    #fd.close()
    #j.copyFrom(u,jopath,dopath,'w', DT.datetime(2008,8,8,8,8),createLinks = True)
    #jpath = j.getJson(u)
    #gotGid = os.stat(jpath)[stat.ST_GID]
    #assert self.newGid ==  gotGid, "%s: Expected %o, got %o" % (jpath, self.newGid, gotGid)
    #dpath = j.getDump(u)
    #gotGid = os.stat(dpath)[stat.ST_GID]
    #assert self.newGid == gotGid, "%s: Expected %o, got %o" % (dpath, self.newGid, gotGid)

    #udir = os.path.split(dpath)[0]
    #datePath = os.path.abspath(os.path.join(udir,os.readlink(os.path.splitext(dpath)[0])))
    #namePath = os.path.abspath(os.path.splitext(dpath)[0])
    #topPath = os.path.abspath(self.testDir)
    #dailies = os.listdir(topPath)
    #def assertGidVisitor(p):
      #gotGid = os.stat(p)[stat.ST_GID]
      #assert self.newGid == gotGid, "%s: expected %0o, got %0o"%(p,self.newGid,gotGid)

    #gotGid = os.stat(datePath)[stat.ST_GID]
    #assert self.newGid == gotGid, '%s: expected %0o, got %0o'%(datePath,self.newGid,gotGid)
    #gotGid = os.stat(namePath)[stat.ST_GID]
    #assert self.newGid == gotGid, '%s: expected %0o, got %0o'%(datePath,self.newGid,gotGid)
    #for d in dailies:
      ## visitPath quietly ignores a file as the leaf
      #socorro_fs.visitPath(os.path.join(topPath,d),datePath,assertGidVisitor)
      #socorro_fs.visitPath(os.path.join(topPath,d),namePath,assertGidVisitor)

#if __name__ == "__main__":
  #unittest.main()


