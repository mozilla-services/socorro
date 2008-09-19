import unittest
import os
import shutil
import types
import sys
import socorro.lib.filesystem as f

# Describes the directory/file structure we will look at:
# key is a name
# if value is a dictionary, the named item is a directory
# if value is None, the named item is an empty file
# otherwise, the named item is a file holding str(value)
testDir = {'TestDir':
           {'f0': 'file TestDir/f0',
            'g0': 'file TestDir/g0',
            '0': {'f0a': 'file TestDir/0/f0a', 'f0b': 'file TestDir/0/f0b' },
            '1': {'f1a': None,'f1b': None,
                  '10': {},
                  '11': {},
                  },
            '2': {'f2a': None,'f2b':None,
                  '20':
                  {'200':
                   {'2000':
                    {'d0': 'file TestDir/2/20/200/2000/d0',
                     'd1': 'file TestDir/2/20/200/2000/d1',
                     },
                    },
                   },
                  },
            '4': {'f4': None,
                  '40':
                  {'f40':None,
                   '400':
                   {'f400':None,
                    '4000':
                    {'f4000':None
                     },
                    },
                   },
                  },
            },
           }

def acceptDirOnly(t):
  return os.path.isdir(t[2])
def acceptFileOnly(t):
  return os.path.isfile(t[2])
def accept2Dirs(t):
  return t[1].startswith('2')
def revcmp(d0,d1):
  return cmp(d1,d0)

class TestFilesystem(unittest.TestCase):
  def createTestbed(self):
    self.deleteTestbed() # just in case
    self.createTestDir('.',testDir)
    
  def createTestDir(self,root,dict):
    for k in dict.keys():
      v = dict[k]
      if type(v) == types.DictionaryType:
        newroot = os.path.join(root,k)
        os.mkdir(newroot)
        self.createTestDir(newroot,dict.get(k))
      elif type(v) == types.NoneType:
        open(os.path.join(root,k),'w').close()
      else:
        f = open(os.path.join(root,k),'w')
        f.write("%s\n" %(v))
        f.close()

  def deleteTestbed(self):
    for topLevelDir in testDir.keys():
      if(os.path.exists(os.path.join('.',topLevelDir))):
        shutil.rmtree(os.path.join('.',topLevelDir))

  def setUp(self):
    self.createTestbed()
    assert 1 == len(testDir.keys()), 'Only one top-level test directory'
    self.tdir = testDir.keys()[0]

  def tearDown(self):
    self.deleteTestbed()

  def testLevel0(self):
    for depth in [ -12,-1,0]:
      tst = f.findFileGenerator(self.tdir,maxDepth = depth)
      items = [x for x in tst]
      assert not items, 'Expect nothing for 0 or negative. For %d, got %s' %(depth,items)

    
  def testLevel1(self):
    # Look for all top level items regardless of type.
    for depth in [1] :
      tst = f.findFileGenerator(self.tdir,maxDepth = depth)
      items = []
      for (x,o,p) in tst:
        items.append(o)
        assert o in testDir[self.tdir].keys(),'depth=%d,Every found item is at top level' % depth
      for k in testDir[self.tdir].keys():
        assert k in items, 'depth=%d,every top level item is found' % depth

      # look for only top level files
      items = []
      expected = ['f0','g0']
      t = f.findFileGenerator(self.tdir,acceptanceFunction = acceptFileOnly, maxDepth = depth)
      for (x,o,p) in t:
        items.append(o)
        assert o in expected, 'depth=%d,expect a top level file, got '+o+' not in '+str(expected) % depth
      for x in expected:
        assert x in items, 'depth=%d,expect both top level files' % depth

      # look for only top level directories
      items = []
      expected = ['0','1','2','4']
      t = f.findFileGenerator(testDir.keys()[0],acceptanceFunction = acceptDirOnly, maxDepth = depth)
      for (x,o,p) in t:
        items.append(o)
        assert o in expected, 'depth=%d,expect a top level directory' % depth
      for x in expected:
        assert x in items, 'depth=%d,expect all top level directories' % depth
     
  def testLevels(self):
    tst = f.findFileGenerator(self.tdir,maxDepth = 2)
    items = []
    expected = ['f0a', 'f0b', '0', '10', '11', 'f1a', 'f1b', '1', '20', 'f2a', 'f2b', '2', '40', 'f4', '4', 'f0', 'g0']
    for (x,o,p) in tst:
      items.append(o)
      assert o in expected
    for o in expected:
      assert o in items
    tst = f.findFileGenerator(self.tdir,maxDepth = 3)
    items = []
    expected = ['f0a', 'f0b', '0', '10', '11', 'f1a', 'f1b', '1', '200', '20', 'f2a', 'f2b', '2', '400', 'f40', '40', 'f4', '4', 'f0', 'g0']
    for (x,o,p) in tst:
      items.append(o)
      assert o in expected
    for o in expected:
      assert o in items
    tst = f.findFileGenerator(self.tdir,maxDepth = 4)
    items = []
    expected = ['f0a', 'f0b', '0', '10', '11', 'f1a', 'f1b', '1', '2000', '200', '20', 'f2a', 'f2b', '2', '4000', 'f400', '400', 'f40', '40', 'f4', '4', 'f0', 'g0']
    for (x,o,p) in tst:
      items.append(o)
      assert o in expected
    for o in expected:
      assert o in items
    tst = f.findFileGenerator(self.tdir,maxDepth = 100)
    items = []
    expected = ['f0a', 'f0b', '0', '10', '11', 'f1a', 'f1b', '1', 'd0', 'd1', '2000', '200', '20', 'f2a', 'f2b', '2', 'f4000', '4000', 'f400', '400', 'f40', '40', 'f4', '4', 'f0', 'g0']
    for (x,o,p) in tst:
      items.append(o)
      assert o in expected
    for o in expected:
      assert o in items

  def testCompare(self):
    #This test won't work for depth > 1 since the directories are visited individually
    tst = f.findFileGenerator(self.tdir,maxDepth = 1)
    items = []
    for (x,o,p) in tst:
      items.append(o)
    tst = f.findFileGenerator(self.tdir,maxDepth = 1,directorySortFunction=revcmp)
    ritems = []
    for (x,o,p) in tst:
      ritems.append(o)
    ritems.reverse()
    assert(items == ritems)

  def testDirAcceptance(self):
    tst = f.findFileGenerator(self.tdir,maxDepth = 100,directoryAcceptanceFunction=accept2Dirs)
    items = []
    expected = ['0', '1', 'd0', 'd1', '2000', '200', '20', 'f2a', 'f2b', '2', '4', 'f0', 'g0']
    for (x,o,p) in tst:
      items.append(o)
      assert o in expected
    for o in expected:
      assert o in items

if __name__ == "__main__":
  unittest.main()
  
