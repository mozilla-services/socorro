import unittest

from mtbf import ProductDimension
from mtbf import getWhereClauseFor

class TestMtbf(unittest.TestCase):
    
  def testGetWhereClauseForAProductAndVersion(self):  
    product = ProductDimension([6, 'Firefox', '3.0.1', 'ALL', 'major'])
    self.assertEquals(getWhereClauseFor(product), " AND version = '3.0.1' AND product = 'Firefox' ")
  
  def testGetWhereClauseForAProductAVersionAndAnOS(self):  
    product = ProductDimension([6, 'Firefox', '3.0.1', 'Win', 'major'])
    self.assertEquals(getWhereClauseFor(product), " AND version = '3.0.1' AND product = 'Firefox' AND substr(os_name, 1, 3) = 'Win' ")
    
  def testGetWhereClauseForAll(self):
    product = ProductDimension([6, 'ALL', 'ALL', 'ALL', 'ALL'])
    self.assertEquals(getWhereClauseFor(product), "")

if __name__ == "__main__":
  unittest.main()
