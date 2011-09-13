import socorro.lib.prioritize as prioritize

import socorro.unittest.testlib.util as tutil

def setup_module():
  tutil.nosePrintModule(__file__)

class TestNode:
  def testConstructor(self):
    n = prioritize.Node()
    assert None == n.item
    assert set() == n.parents
    assert [] == n.children
    n = prioritize.Node('a')
    assert 'a' == n.item
    assert set() == n.parents
    assert [] == n.children

  def testAddChild(self):
    p = prioritize.Node('a')
    n = p.addChild('c')
    assert isinstance(n,prioritize.Node)
    assert n in p.children
    assert p in n.parents
    d = prioritize.Node('d')
    n = p.addChild(d)
    assert d == n
    assert d in p.children
    assert p in d.parents
    assert 2 == len(p.children)
    n = p.addChild(d)
    assert d == n
    assert 2 == len(p.children)
    assert 1 == len(d.parents)

  def testAddParent(self):
    c = prioritize.Node('c')
    n = c.addParent('p')
    assert isinstance(n,prioritize.Node)
    assert n in c.parents
    assert c in n.children
    d = prioritize.Node('d')
    n = c.addParent(d)
    assert d == n
    assert d in c.parents
    assert c in d.children
    assert 2 == len(c.parents)
    n = c.addParent(d)
    assert d == n
    assert 2 == len(c.parents)

  def testFindChild(self):
    a = prioritize.Node('a')
    b = prioritize.Node('b')
    c = prioritize.Node('c')
    d = prioritize.Node('d')
    e = prioritize.Node('e')
    f = prioritize.Node('f')
    top = prioritize.Node('0')
    top.addChild(a)
    a.addChild(b)
    a.addChild(c)
    b.addChild(d)
    c.addChild(d)
    b.addChild(e)
    d.addChild(f)
    assert a == top.findChild('a')
    assert a == a.findChild('a')
    assert b == top.findChild('b')
    assert c == top.findChild('c')
    assert d == top.findChild('d')
    assert e == top.findChild('e')
    assert f == top.findChild('f')
    assert None == top.findChild(1)
    assert None == f.findChild('a')
    assert None == b.findChild('a')

  def testStr(self):
    n = prioritize.Node()
    assert "<node: set([])<- None ->[]>" == str(n)
    n.addChild('a')
    assert "<node: set([])<- None ->['a']>" == str(n)
    n.addParent('a')
    assert "<node: set(['a'])<- None ->['a']>" == str(n)
    n.addChild('b')
    assert "<node: set(['a'])<- None ->['a', 'b']>" == str(n)
    for p in ('b',3,'B','c', 1,'C','d',2,'D',):
      n.addParent(p)
      pdisp = set((x.item for x in n.parents))
      assert str(n).startswith("<node: %s<-"%pdisp),"Expected '%s', got '%s'"%("<node: %s<-"%pdisp,str(n))
    n = prioritize.Node()
    for c in (9,'A','a','b',3,'B','c', 1,'C','d',2,'D',):
      n.addChild(p)
      cdisp = [x.item for x in n.children]
      assert str(n).endswith("%s>"%cdisp)

def testFindChild():
  a = prioritize.Node('a')
  b = prioritize.Node('b')
  c = prioritize.Node('c')
  d = prioritize.Node('d')
  e = prioritize.Node('e')
  a.addChild(b)
  a.addChild(c)
  b.addChild(d)
  c.addChild(d)
  a.addChild(e)
  assert None == a.findChild('nope')
  assert None == b.findChild('e')
  assert None == b.findChild('a')
  assert a == a.findChild('a')
  assert b == a.findChild('b')
  assert c == a.findChild('c')
  assert d == a.findChild('d')
  assert e == a.findChild('e')
  c.addChild(e)
  e.addChild(a)
  assert a == c.findChild('a')
  assert None == b.findChild('a')

# [ aMap for test,
#   expected result map,
#   map of nodeName:expected dependencyOrder result for that node (aka BottomUpVisitor)
#   map of nodeName:expected top-down visit order for that node
# ]
# There is an issue here in that some of the expected orders are non-deterministic,
# such as when a depends on b and c, should we see a,b,c or a,c,b in top down (c,b,a or b,c,a in bottom up)
# The orders encoded here work on the original testing machine. If they fail on your machine, we'll need to
# think about how to do some kind of regular expression test, maybe.
dependencyTestCases = [
  [{},
   {},
   {},
   {},
   ],

  [{'a':()},
   {'a':[]},
   {'a':['a']},
   {'a':['a']},
   ],

  [{'a':(),'b':()},
   {'a':[],'b':[]},
   {'a':['a'],'b':['b']},
   {'a':['a'],'b':['b']},
   ],

  [{'a':('b',)},
   {'a':['b'],'b':[]},
   {'a':['b','a'], 'b':['b']},
   {'a':['a','b'], 'b':['b']},
   ],

  [{'a':('b','c',)},
   {'a':['b','c'],'b':[], 'c':[]},
   {'a':['b','c','a'],'b':['b'],'c':['c']},
   {'a':['a','b','c'], 'b':['b'],'c':['c']},
   ],
  [{'a':('b',),'b':('c',)},
   {'a':['b'],'b':['c'],'c':[]},
   {'a':['c','b','a'],'b':['c','b'],'c':['c']},
   {'a':['a','b','c'],'b':['b','c',],'c':['c']},
   ],

  [{'a':('b',),'b':('a',)},
   {'a':['b'],'b':['a']},
   {'a':['b','a'],'b':['a','b']},
   {'a':['a','b'],'b':['b','a']},
   ],

  [{'a':('b','c','d'),'b':('c',),'c':('d',),},
   {'a':['b','c','d'],'b':['c',],'c':['d'],'d':[]},
   {'a':['d','c','b','a'],'b':['d','c','b'],'c':['d','c'],'d':['d']},
   {'a':['a','b','c','d'],'b':['b','c','d'],'c':['c','d'],'d':['d']},
   ],

  [{'a':['d'],'b':['d'],'c':['b'],'d':['e','f','g']},
   {'a':['d'],'b':['d'],'c':['b'],'d':['e','f','g'],'e':[],'f':[],'g':[]},
   {'a':['e','f','g','d','a'],'b':['e','f','g','d','b'],'c':['e','f','g','d','b','c'],'d':['e','f','g','d'],'e':['e'],'f':['f'],'g':['g'],},
   {'a':['a','d','e','f','g'],'b':['b','d','e','f','g'],'c':['c','b','d','e','f','g'],'d':['d','e','f','g'],'e':['e'],'f':['f'],'g':['g'],},
   ],

  [{'a':['d'],'b':['d'],'c':['b'],'d':['e','f','g'],'e':[],'f':(),'g':[]},
   {'a':['d'],'b':['d'],'c':['b'],'d':['e','f','g'],'e':[],'f':[],'g':[]},
   {'a':['e','f','g','d','a'],'b':['e','f','g','d','b'],'c':['e','f','g','d','b','c'],'d':['e','f','g','d'],'e':['e'],'f':['f'],'g':['g'],},
   {'a':['a','d','e','f','g'],'b':['b','d','e','f','g'],'c':['c','b','d','e','f','g'],'d':['d','e','f','g'],'e':['e'],'f':['f'],'g':['g'],},
   ],
  ]

def testTopDownVisitor():
  global dependencyTestCases
  for aMap,ignore,ignore,expected in dependencyTestCases:
    result = prioritize.makeDependencyMap(aMap)
    if {} == expected:
      assert {} == aMap
    for k in expected.keys():
      v = prioritize.TopDownVisitor()
      v.visit(result[k])
      got = [x.item for x in v.history]
      assert expected[k]==got, "expected:%s, got:%s"%(expected[k],got)

def testBottomUpVisitor():
  global dependencyTestCases
  for aMap,ignore,expected,ignore in dependencyTestCases:
    result = prioritize.makeDependencyMap(aMap)
    if {} == expected:
      assert {} == aMap
    for k in expected.keys():
      v = prioritize.BottomUpVisitor()
      v.visit(result[k])
      got = [x.item for x in v.history]
      assert expected[k]==got, "expected:%s, got:%s"%(expected[k],got)

def testMakeDependencyMap():
  global dependencyTestCases
  for aMap,expected,ignore,ignore in dependencyTestCases:
    result = prioritize.makeDependencyMap(aMap)
    checkResult = dict([(k,[x.item for x in result[k].children]) for k in result.keys()])
    assert expected == checkResult, "expected:%s, got:%s"%(expected,checkResult)

def testDependencyOrder():
  for aMap,ignore,ordered,ignore in dependencyTestCases:
    if {} == aMap:
      assert {} == ordered
    for k in ordered.keys():
      result = prioritize.dependencyOrder(aMap,[k])
      assert ordered[k] == result, "expected:%s, got:%s"%(ordered[k],result)

    aMap = {'a':['b']}
    aList = ['0','a','b','c']
  result = prioritize.dependencyOrder(aMap,aList)
  assert ['b','a','0','c'] == result, "Expected ['b','a','0','c'], got %s"%(result)
