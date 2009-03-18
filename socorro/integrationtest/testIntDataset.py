from intdataset import IntDataset
from socorrotestcase import SocorroTestCase

import httplib2
import sys
import unittest

from testconfig import baseUrl

def url(path):
  return baseUrl + path

class TestIntDataset(SocorroTestCase):
  def setUp(self):
    #IntDataset().fresh()
    pass

  def testRegression(self):
    h = httplib2.Http()
    
    self.assertServerStatus(h)
    
    self.assertCrashReportsForDevBuild(h)
    

  def assertServerStatus(self, h):
    print url('/status')
    resp, cont = h.request( url('/status') )
    self.assertContainsOnce( '<dd>2</dd>', cont,  'Waiting Jobs is most recent id 28')
    self.assertContainsOnce( '<dd>1</dd>', cont,  'Avg Wait')
    self.assertContainsOnce( '<dd>3.2</dd>', cont, 'Average Seconds to Process')
    
  def assertCrashReportsForDevBuild(self, h):
    resp, cont = h.request( url('/report/list?version=Firefox%3A3.0.3pre&query_search=signature&query_type=contains&query=&date=&range_value=2&range_unit=weeks&do_query=1&signature=%400x0'))
    self.assertAIsBeforeB(cont, "10\/23", "10\/25")
    

if __name__ == "__main__":
  unittest.main()
