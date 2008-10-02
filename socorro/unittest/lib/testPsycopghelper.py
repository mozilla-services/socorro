import unittest
import socorro.lib.psycopghelper as ppghelper
import psycopg2
import psycopg2.extensions
"""
Assume that psycopg2 works, then all we need to do is assure ourselves
that our simplistic wrap around a returned array is correct
"""

class TestMultiCursor(psycopg2.extensions.cursor):
  def __init__(self,numCols = 4, numRows=2, **kwargs):
    self.result = []
    for i in range(numRows):
      aRow = []
      for j in range(numCols):
        aRow.append('Row %d, Column %d' %(i,j))
      self.result.append(aRow)
      
  def execute(self,sql, args=None):
    pass
  def fetchall(self):
    return self.result
        
class TestEmptyCursor(psycopg2.extensions.cursor):
  def __init__(self):
    self.result = []
      
  def execute(self,sql, args=None):
    pass
  def fetchall(self):
    return self.result
        
class TestSingleCursor(psycopg2.extensions.cursor):
  def __init__(self):
    self.result = [['Row 0, Column 0']]
      
  def execute(self,sql, args=None):
    pass
  def fetchall(self):
    return self.result
        

class TestPsycopghelper(unittest.TestCase):
  def testSingleValueEmpty(self):
    try:
      cur = TestEmptyCursor()
      ppghelper.singleValueSql(cur,"")
      assert False, "must raise SQLDidNotReturnSingleValue"
    except ppghelper.SQLDidNotReturnSingleValue,e:
      pass

  def testSingleValueSingle(self):
    try:
      cur = TestSingleCursor()
      assert "Row 0, Column 0" == ppghelper.singleValueSql(cur,"")
    except Exception, e:
      assert False, "must not raise an exception for this %s" %e

  def testSingleValueMulti(self):
    try:
      cur = TestMultiCursor(numRows=5)
      assert "Row 0, Column 0" == ppghelper.singleValueSql(cur,"")
    except Exception, e:
      assert False, "must not raise an exception for this "+e

  def testSingleRowEmpty(self):
    try:
      cur = TestEmptyCursor()
      ppghelper.singleRowSql(cur,"")
      assert False, "must raise SQLDidNotReturnSingleRow"
    except ppghelper.SQLDidNotReturnSingleRow,e:
      pass

  def testSingleRowSingle(self):
    try:
      cur = TestSingleCursor()
      assert ["Row 0, Column 0"] == ppghelper.singleRowSql(cur,"")
    except Exception, e:
      assert False, "must not raise this exception"

  def testSingleRowMulti(self):
    try:
      cur = TestMultiCursor(numRows=5, numCols=1)
      assert ["Row 0, Column 0"] == ppghelper.singleRowSql(cur,"")
    except Exception, e:
      assert False, "must not raise this exception"

if __name__ == "__main__":
  unittest.main()
  
