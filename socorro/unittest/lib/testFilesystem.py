import unittest
import os
import shutil
import types
import sys

from nose.tools import *
import socorro.lib.filesystem as f
import socorro.unittest.testlib.util as tutil

def setup_module():
  tutil.nosePrintModule(__file__)

#import testWalkVersusFilesystem as f

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
      expected = [ x for x in testDir[self.tdir].keys() ]
      for (x,o,p) in tst:
        items.append(o)
        assert o in expected ,'Item %s must be expected: %s' %(o,expected)
      for k in expected:
        assert k in items, 'Expected item %s must be found in %s' %(k,items)

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

  def testFailMakedirsOnFileInPath(self):
    path = 'TestDir/1/2/3/4'
    tpath = path
    while True:
      head,tail = os.path.split(tpath)
      if tail == 'TestDir': break
      try:
        shutil.rmtree('TestDir')
      except:
        pass
      f.makedirs(head)
      t = open(tpath,'w')
      t.write('nothing\n')
      t.close()
      try:
        f.makedirs(path)
        assert False, 'We should have had an OSError, but success for %s a file'%tpath
      except OSError:
        pass
      except Exception,x:
        assert False, 'We should have had an OSError, got %s: %s'%(type(x),x)
      tpath = head

  def testCleanEmptySubdirectories(self):
    f.makedirs('TestDir/A/B/C/D')
    f.makedirs('TestDir/AA/BB/C')
    f.makedirs('TestDir/AA/BB/CC/DD')
    fi = open('TestDir/A/a','w')
    fi.write('file a\n')
    fi.close()
    # Test short-circuit path, full stopper
    assert os.path.isdir('TestDir/A/B/C/D')
    f.cleanEmptySubdirectories('TestDir/A/B/C/D','TestDir/A/B/C/D')
    assert os.path.isdir('TestDir/A/B/C/D')
    # Test short-circuit path, name stopper
    f.cleanEmptySubdirectories('D','TestDir/A/B/C/D')
    assert os.path.isdir('TestDir/A/B/C/D')

    # Test some empties, name stopper
    f.cleanEmptySubdirectories('C','TestDir/A/B/C/D')
    assert not os.path.exists('TestDir/A/B/C/D')
    assert os.path.isdir('TestDir/A/B/C')
    # Test some empties, path stopper
    f.cleanEmptySubdirectories('TestDir/A/B','TestDir/A/B/C')
    assert not os.path.exists('TestDir/A/B/C')
    assert os.path.isdir('TestDir/A/B')

    #Test stopping on a file in a subdir 
    f.cleanEmptySubdirectories('TestDir','TestDir/A/B')
    assert not os.path.exists('TestDir/A/B')
    assert os.path.isdir('TestDir/A')

    #Test stopping on another subdir
    f.cleanEmptySubdirectories('TestDir/AA','TestDir/AA/BB/CC/DD')
    assert not os.path.exists('TestDir/AA/BB/CC')
    assert os.path.isdir('TestDir/AA/BB')

    #Test for stopper not in path
    assert_raises(OSError,f.cleanEmptySubdirectories,'Woo','TestDir/AA/BB')

    #Test for non-existent leaf
    assert_raises(OSError,f.cleanEmptySubdirectories,'TestDir','TestDir/AA/BB/CC/DD')

  def testVisitPath(self):
    f.makedirs('TestDir/a/b/c/d/e/f')
    fi = open('TestDir/a/b/c/d/D0','w')
    fi.write("hi\n")
    fi.close
    seen = set()
    def collector(x):
      seen.add(x)
    top = 'TestDir/a'
    last = 'TestDir/a/b/c/d'
    absTop = os.path.normpath(top)
    expected = set([absTop])
    for i in [['b'],['b','c'],['b','c','d']]:
      expected.add(os.path.join(absTop,os.sep.join(i)))
    f.visitPath(top,last,collector)
    assert expected == seen, 'but x-s=%s and s-x=%s'%(expected-seen,seen-expected)

    seen.clear()
    top = 'TestDir/a/b'
    last = 'TestDir/a/b/c/d/D0'
    normTop = os.path.normpath(top)
    expected = set([normTop])
    for i in [['c'],['c','d']]:
      expected.add(os.path.join(absTop,os.sep.join(i)))
    f.visitPath(top,last,collector)
    assert expected == seen, 'but x-s=%s and s-x=%s'%(expected-seen,seen-expected)

    #Test for non-existent leaf
    assert_raises(OSError,f.visitPath,'TestDir','TestDir/A/BB',collector)

    #Test for rootDir not abover fullPath
    assert_raises(OSError,f.visitPath,'TestDir/A/B','TestDir/A',collector)

if __name__ == "__main__":
  unittest.main()
  
