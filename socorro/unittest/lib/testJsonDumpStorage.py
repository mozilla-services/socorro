import unittest
import os
import shutil
import datetime
import socorro.lib.JsonDumpStorage as JDS

class TestJsonDumpStorage(unittest.TestCase):

  def setUp(self):
    self.testDir = os.path.join('.','TEST-JSONDUMP')
    self.data = {
      '0b9ff107-8672-4aac-8b75-b2bd825c3d58': ('2008-12-25-05-00','webhead01','0b/9f/f1/07','2008/12/25/05/00/webhead01'),
      '22adfb61-f75b-11dc-b6be-001321b0783d': ('2008-12-25-05-01','webhead01','22/ad/fb/61','2008/12/25/05/00/webhead01'),
      'b965de73-ae90-a935-1357-03ae102b893f': ('2008-12-25-05-04','webhead01','b9/65/de/73','2008/12/25/05/00/webhead01'),
      '0b781b88-ecbe-4cc4-893f-6bbbfd50e548': ('2008-12-25-05-05','webhead01','0b/78/1b/88','2008/12/25/05/05/webhead01'),
      '0b8344d6-9021-4db9-bf34-a15394f96ff5': ('2008-12-25-05-06','webhead01','0b/83/44/d6','2008/12/25/05/05/webhead01'),
      '0b94199b-b90b-4683-a38a-4114d3fd5253': ('2008-12-26-05-21','webhead01','0b/94/19/9b','2008/12/26/05/20/webhead01'),
      '0b9eedc3-9a79-4ce2-83eb-1559e5234fde': ('2008-12-26-05-24','webhead01','0b/9e/ed/c3','2008/12/26/05/20/webhead01'),
      '0b9fd6da-27e4-46aa-bef3-3deb9ef0d364': ('2008-12-26-05-25','webhead02','0b/9f/d6/da','2008/12/26/05/25/webhead02'),
      '0ba32a30-2476-4724-b825-de1727afa9cb': ('2008-11-25-05-00','webhead02','0b/a3/2a/30','2008/11/25/05/00/webhead02'),
      '0bad640f-5825-4d42-b96e-21b8b1d250df': ('2008-11-25-05-04','webhead02','0b/ad/64/0f','2008/11/25/05/00/webhead02'),
      '0bae7049-bbff-49f2-b408-7e9f41602507': ('2008-11-25-05-05','webhead02','0b/ae/70/49','2008/11/25/05/05/webhead02'),
      '0baf1b4d-dad3-4d35-ae7e-b9dcb217d27f': ('2008-11-25-05-06','webhead02','0b/af/1b/4d','2008/11/25/05/05/webhead02'),
      '0bba61c5-dfc3-43e7-87e6-8afda3564352': ('2019-10-25-05-04','webhead02','0b/ba/61/c5','2019/10/25/05/00/webhead02'),
      '0bba929f-8721-460c-8e70-a43c95d04ed2': ('2019-10-25-05-04','webhead02','0b/ba/92/9f','2019/10/25/05/00/webhead02'),
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

  def _createTestSet(self):
    storage = JDS.JsonDumpStorage(self.testDir)
    for uuid,data in self.data.items():
      fj,fd = storage.newEntry(uuid,webheadHostName=data[1],timestamp = datetime.datetime(*datetimedata))
      try:
        fj.write('json test of %s\n' % uuid)
      finally:
        if fj: fj.close()
      try:
        fd.write('dump test of %s\n' % uuid)
      finally:
        if fd: fd.close()

  def testNewEntry(self):
    storage = JDS.JsonDumpStorage(self.testDir)
    for uuid,data in self.data.items():
      datetimedata = [int(x) for x in data[0].split('-')]
      try:
        fj,fd = storage.newEntry(uuid,webheadHostName=data[1],timestamp = datetime.datetime(*datetimedata))
      except IOError:
        assert False, 'Expect to succeed with newEntry(%s,...)' % (uuid)
        
      assert fj, 'Expect a non-null json file handle from newEntry(%s,...)' % (uuid)
      assert os.sep.join((self.testDir,data[2],uuid+'.json')) == fj.name
      assert fd, 'Expect a non-null dump file handle from newEntry(%s,...)' % (uuid)
      assert os.sep.join((self.testDir,data[2],uuid+'.dump')) == fj.name, 'Expect appropriate json filename for %s' % (uuid)
      assert os.path.islink(os.sep.join((self.testDir,data[3],uuid))), 'Expect a link from timed to storage for %s' % (uuid)
      assert os.path.islink(os.sep.join((self.testDir,data[2],uuid+'.link'))), 'Expect link from radix storage to timed for %s' %(uuid)
      try:
        fj.write("testing\n")
        assert True, 'must be able to write to the json file for uuid %s' % (uuid)
      except:
        assert False, 'must not fail to write to the json file for uuid %s' % (uuid)
      finally:
        if fj: fj.close()

      try:
        fd.write("testing\n")
        assert True, 'must be able to write to the dump file for uuid %s' % (uuid)
      except:
        assert False, 'must not fail to write to the dump file for uuid %s' % (uuid)
      finally:
        if fd: fd.close()

  def testGetJson(self):
    self.createTestSet()

  def testGetDump(self):
    self.createTestSet()

  def testOpenAndMarkAsSeen(self):
    self.createTestSet()

  def testDestructiveDateWalk(self)
    self.createTestSet()

  def testRemove(self):
    self.createTestSet()

  def testMove(self):
    self.createTestSet()

  def testRemoveOlderThan(self):
    pass
    
if __name__ == "__main__":
  unittest.main()

