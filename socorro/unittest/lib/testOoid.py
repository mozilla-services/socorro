# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import socorro.lib.uuid as uu
import socorro.lib.ooid as oo
import datetime as dt

from socorro.lib.datetimeutil import utc_now, UTC

class TestOoid(unittest.TestCase):
  def setUp(self):
    self.baseDate = dt.datetime(2008,12,25, tzinfo=UTC)
    self.rawuuids = []
    self.yyyyoids = []
    self.dyyoids = []
    self.depths = [4,4,3,3,3,2,2,2,1,1]
    self.badooid0 = "%s%s" %(str(uu.uuid4())[:-8],'ffeea1b2')
    self.badooid1 = "%s%s" %(str(uu.uuid4())[:-8],'f3eea1b2')

    for i in range(10):
      self.rawuuids.append(str(uu.uuid4()))
    assert len(self.depths) == len(self.rawuuids)

    for i in self.rawuuids:
      self.yyyyoids.append("%s%4d%02d%02d" % (i[:-8],self.baseDate.year,self.baseDate.month,self.baseDate.day))

    for i in range(len(self.rawuuids)):
      self.dyyoids.append("%s%d%02d%02d%02d" %(self.rawuuids[i][:-7],self.depths[i],self.baseDate.year%100,self.baseDate.month,self.baseDate.day))

    today = utc_now()
    self.nowstamp = dt.datetime(today.year,today.month,today.day,tzinfo=UTC)
    self.xmas05 = dt.datetime(2005,12,25,tzinfo=UTC)


  def testCreateNewOoid(self):
    ooid = oo.createNewOoid()
    ndate = oo.dateFromOoid(ooid)
    ndepth = oo.depthFromOoid(ooid)
    assert self.nowstamp == ndate, 'Expect date of %s, got %s' %(self.nowstamp,ndate)
    assert oo.defaultDepth == ndepth, 'Expect default depth (%d) got %d' % (oo.defaultDepth,ndepth)

    ooid = oo.createNewOoid(timestamp=self.xmas05)
    ndate = oo.dateFromOoid(ooid)
    ndepth = oo.depthFromOoid(ooid)
    assert self.xmas05 == ndate, 'Expect date of %s, got %s' %(self.xmas05,ndate)
    assert oo.defaultDepth == ndepth, 'Expect default depth (%d) got %d' % (oo.defaultDepth,ndepth)

    for d in range(1,5):
      ooid0 = oo.createNewOoid(depth=d)
      ooid1 = oo.createNewOoid(timestamp=self.xmas05,depth=d)
      ndate0 = oo.dateFromOoid(ooid0)
      ndepth0 = oo.depthFromOoid(ooid0)
      ndate1 = oo.dateFromOoid(ooid1)
      ndepth1 = oo.depthFromOoid(ooid1)
      assert self.nowstamp == ndate0, 'Expect date of %s, got %s' %(self.nowstamp,ndate0)
      assert self.xmas05 == ndate1, 'Expect date of %s, got %s' %(self.xmas05,ndate1)
      assert ndepth0 == ndepth1, 'Expect depth0(%d) == depth1(%d)' %(ndepth0,ndepth1)
      assert d == ndepth0, 'Expect depth %d, got %d' % (d,ndepth0)
    assert None == oo.depthFromOoid(self.badooid0)
    assert None == oo.depthFromOoid(self.badooid1)

  def testUuidToOid(self):
    for i in range(len(self.rawuuids)):
      u = self.rawuuids[i]
      o0 = oo.uuidToOoid(u)
      expected =  (self.nowstamp,oo.defaultDepth)
      got = oo.dateAndDepthFromOoid(o0)
      assert expected == got, 'Expected %s, got %s'%(expected,got)
      o1 = oo.uuidToOoid(u,timestamp=self.baseDate)
      expected =  (self.baseDate,oo.defaultDepth)
      got = oo.dateAndDepthFromOoid(o1)
      assert expected == got, 'Expected %s, got %s'%(expected,got)
      o2 = oo.uuidToOoid(u,depth=self.depths[i])
      expected = (self.nowstamp,self.depths[i])
      got = oo.dateAndDepthFromOoid(o2)
      assert expected == got, 'Expected %s, got %s'%(expected,got)
      o3 = oo.uuidToOoid(u,depth=self.depths[i],timestamp=self.xmas05)
      expected = (self.xmas05,self.depths[i])
      got = oo.dateAndDepthFromOoid(o3)
      assert expected == got, 'Expected %s, got %s'%(expected,got)

  def testGetDate(self):
    for ooid in self.yyyyoids:
      assert self.baseDate == oo.dateFromOoid(ooid), 'Expected %s got %s' %(self.baseDate, oo.dateFromOoid(ooid))
      assert 4 == oo.depthFromOoid(ooid), 'Expected %d, got %d' %(4, oo.depthFromOoid(ooid))
    assert None == oo.dateFromOoid(self.badooid0)
    assert None == oo.dateFromOoid(self.badooid1)

  def testGetDateAndDepth(self):
    for i in range(len(self.dyyoids)):
      date,depth = oo.dateAndDepthFromOoid(self.dyyoids[i])
      assert self.depths[i] == depth, 'Expect depth=%d, got %d (%s)'%(self.depth[i],depth,self.dyyoids[i])
      assert self.baseDate == date, 'Expect %s, got %s' %(self.baseDate, date)
    assert (None,None) == oo.dateAndDepthFromOoid(self.badooid0)
    assert (None,None) == oo.dateAndDepthFromOoid(self.badooid1)

if __name__ == "__main__":
  unittest.main()
