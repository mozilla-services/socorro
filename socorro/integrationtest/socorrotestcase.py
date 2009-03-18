import unittest

class SocorroTestCase(unittest.TestCase):
  "The helper class for integration tests"
  def assertContainsOnce(self, needle, haystack, msg=''):
    index1 = self.assertContains(haystack, needle)
    index1 += 1
    index2 = haystack.find(needle, index1)
    self.assertEqual(index2, -1, "Expected %s once, but appears more at %d. %s" %(needle, index2, msg))
  
  def assertAIsBeforeB(self, content, aString, bString):
    index1 = self.assertContains(content, aString)
    index2 = self.assertContains(content, bString)
    self.assertTrue( index1 < index2, "'%s' is after '%s' in '%s'. found at %d, second string found at %d" % (aString, bString, content, index1, index2))
    
  def assertContains(self, haystack, needle, msg=''):
    index1 = haystack.find( needle )
    self.assertNotEqual(index1, -1, "Expected to find %s in %s but didn't. %s" % (needle, haystack, msg))
    return index1

class TestSocorroTestCase(SocorroTestCase):
  "Tests for this helper class"
  
  def testContainsOnce(self):
    self.assertContainsOnce("apple", "the big apple")
    self.assertRaises(self.failureException, self.assertContainsOnce, "york", "new york new york")
  
  def testassertAIsBeforeB(self):
    self.assertAIsBeforeB("The order things happen in are usually important", "order", "usually")
    self.assertRaises(self.failureException, self.assertAIsBeforeB, "a b c d e f", "e", "b")

if __name__ == "__main__":
  unittest.main()
