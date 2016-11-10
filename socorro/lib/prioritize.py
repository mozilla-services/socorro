# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

class Node(object):
  """
  Node is a generic node in a directed graph. It contains an item, a set of parents and a list of children
  It is not possible to have the same parent or child more than once (no duplicate edges). It is possible to
  have a parent whose child is also its parent, or longer cycles. If you do that, its your own problem.
  """
  def __init__(self,item=None):
    """You may create an empty Node or a Node that already has an item"""
    self.item = item
    self.children = []
    self.parents = set()

  def addChild(self,item):
    """
    When you add a child to a Node, you are adding yourself as a parent to the child
    You cannot have the same node as a child more than once.
    If you add a Node, it is used. If you add a non-node, a new child Node is created. Thus: You cannot
    add a child as an item which is a Node. (You can, however, construct such a node, and add it as a child)
    """
    if not isinstance(item,Node):
      item = Node(item)
    if item in self.children:
      return item
    self.children.append(item)
    item.parents.add(self)
    return item

  def addParent(self,item):
    """
    When you add a parent to a Node, you are adding yourself as a child to the parent.
    You cannot have the same node as a parent more than once.
    If you add a Node, it is used. If you add a non-node, a new parent Node is created. Thus: You cannot
    add a parent as an item which is a Node. (You can, however, construct such a node, and add it as a parent)
    """
    if not isinstance(item,Node):
      item = Node(item)
    self.parents.add(item)
    if not self in item.children:
      item.children.append(self)
    return item

  def findChild(self,item):
    """ Do a top down search for the item in a node, and return the first node found, else None. """
    return FindChildVisitor(item).visit(self)

  def __str__(self):
    children = [x.item for x in self.children]
    parents =  set([x.item for x in self.parents])
    return "<node: %s<- %s ->%s>"%(parents,self.item,children)

class FindChildVisitor(object):
  """Do a top down search for a particular item. Stop traversing when that item is found"""
  def __init__(self,item):
    self.item = item
    self.marks = set()
    self.child = None
  def visit(self,node):
    if node in self.marks: return self.child
    if self.item == node.item:
      self.child = node
    if self.child:
      return self.child
    self.marks.add(node)
    for c in node.children:
      self.child = self.visit(c)
      if self.child:
        return self.child
    return self.child

class BottomUpVisitor(object):
  """Visit each child before visiting self, retaining a list of visited Nodes in self.history"""
  def __init__(self):
    self.history = []
    self.marks = set()
    self.cycleMark = set()
  def visit(self,node):
    if node in self.cycleMark:
      return
    self.cycleMark.add(node)
    for c in node.children:
      self.visit(c)
    if not node in self.marks:
      self.history.append(node)
      self.marks.add(node)

class TopDownVisitor(object):
  """Visit self before visiting each child, retaining a list of visited Nodes in self.history"""
  def __init__(self):
    self.history = []
    self.marks = set()
  def visit(self,node):
    if node in self.marks:
      return
    self.history.append(node)
    self.marks.add(node)
    for c in node.children:
      self.visit(c)

def makeDependencyMap(aMap):
  """
  create a dependency data structure as follows:
  - Each key in aMap represents an item that depends on each item in the iterable which is that key's value
  - Each Node represents an item which is a precursor to its parents and depends on its children
  Returns a map whose keys are the items described in aMap and whose values are the dependency (sub)tree for that item
  Thus, for aMap = {a:(b,c), b:(d,), c:[]},
  returns {a:Node(a),b:Node(b),c:Node(c),d:Node(d)} where
     - Node(a) has no parent and children: Node(b) and Node(c)
     - Node(b) has parent: Node(a) and child: Node(d)
     - Node(c) has parent: Node(a) and no child
     - Node(d) which was not a key in aMap was created. It has parent: Node(b) and no child
  This map is used to find the precursors for a given item by using BottomUpVisitor on the Node associated with that item
  """
  index = {}
  for i in aMap.keys():
    iNode = index.get(i,None)
    if not iNode:
      iNode = Node(i)
      index[i] = iNode
    for c in aMap[i]:
      cNode = index.get(c,None)
      if not cNode:
        cNode = Node(c)
        index[c] = cNode
      iNode.addChild(cNode)
  return index

def debugTreePrint(node,pfx="->"):
  """Purely a debugging aid: Ascii-art picture of a tree descended from node"""
  print pfx,node.item
  for c in node.children:
    debugTreePrint(c,"  "+pfx)

def dependencyOrder(aMap, aList = None):
  """
  Given descriptions of dependencies in aMap and an optional list of items in aList
  if not aList, aList = aMap.keys()
  Returns a list containing each element of aList and all its precursors so that every precursor of
  any element in the returned list is seen before that dependent element.
  If aMap contains cycles, something will happen. It may not be pretty...
  """
  dependencyMap = makeDependencyMap(aMap)
  outputList = []
  if not aList:
    aList = aMap.keys()
  items = []
  v = BottomUpVisitor()
  for item in aList:
    try:
      v.visit(dependencyMap[item])
    except KeyError:
      outputList.append(item)
  outputList = [x.item for x in v.history]+outputList
  return outputList

