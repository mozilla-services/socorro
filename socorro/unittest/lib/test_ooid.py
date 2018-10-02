# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import uuid
from socorro.lib import ooid

import pytest

from socorro.lib.datetimeutil import utc_now, UTC
from socorro.unittest.testbase import TestCase


@pytest.mark.parametrize('crashid, expected', [
    ('', False),
    ('aaa', False),
    ('de1bb258cbbf4589a67334f800160918', False),
    ('DE1BB258-CBBF-4589-A673-34F800160918', False),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', False),
    ('00000000-0000-0000-0000-000000000000', True),
])
def test_validate_crash_id(crashid, expected):
    assert ooid.is_crash_id_valid(crashid) == expected


class TestOoid(TestCase):
    def setUp(self):
        self.baseDate = datetime.datetime(2008, 12, 25, tzinfo=UTC)
        self.rawuuids = []
        self.yyyyoids = []
        self.dyyoids = []
        self.depths = [4, 4, 3, 3, 3, 2, 2, 2, 1, 1]
        self.badooid0 = "%s%s" % (str(uuid.uuid4())[:-8], 'ffeea1b2')
        self.badooid1 = "%s%s" % (str(uuid.uuid4())[:-8], 'f3eea1b2')

        for i in range(10):
            self.rawuuids.append(str(uuid.uuid4()))
        assert len(self.depths) == len(self.rawuuids)

        for i in self.rawuuids:
            self.yyyyoids.append("%s%4d%02d%02d" % (
                i[:-8], self.baseDate.year, self.baseDate.month, self.baseDate.day))

        for i in range(len(self.rawuuids)):
            self.dyyoids.append("%s%d%02d%02d%02d" % (
                self.rawuuids[i][:-7],
                self.depths[i],
                self.baseDate.year % 100,
                self.baseDate.month,
                self.baseDate.day
            ))

        today = utc_now()
        self.nowstamp = datetime.datetime(
            today.year, today.month, today.day, tzinfo=UTC)
        self.xmas05 = datetime.datetime(2005, 12, 25, tzinfo=UTC)

    def testCreateNewOoid(self):
        new_ooid = ooid.create_new_ooid()
        ndate = ooid.dateFromOoid(new_ooid)
        ndepth = ooid.depthFromOoid(new_ooid)
        assert self.nowstamp == ndate
        assert ooid.defaultDepth == ndepth

        new_ooid = ooid.create_new_ooid(timestamp=self.xmas05)
        ndate = ooid.dateFromOoid(new_ooid)
        ndepth = ooid.depthFromOoid(new_ooid)
        assert self.xmas05 == ndate
        assert ooid.defaultDepth == ndepth

        for d in range(1, 5):
            ooid0 = ooid.create_new_ooid(depth=d)
            ooid1 = ooid.create_new_ooid(timestamp=self.xmas05, depth=d)
            ndate0 = ooid.dateFromOoid(ooid0)
            ndepth0 = ooid.depthFromOoid(ooid0)
            ndate1 = ooid.dateFromOoid(ooid1)
            ndepth1 = ooid.depthFromOoid(ooid1)
            assert self.nowstamp == ndate0
            assert self.xmas05 == ndate1
            assert ndepth0 == ndepth1
            assert d == ndepth0
        assert ooid.depthFromOoid(self.badooid0) is None
        assert ooid.depthFromOoid(self.badooid1) is None

    def testUuidToOid(self):
        for i in range(len(self.rawuuids)):
            u = self.rawuuids[i]
            o0 = ooid.uuid_to_ooid(u)
            expected = (self.nowstamp, ooid.defaultDepth)
            got = ooid.dateAndDepthFromOoid(o0)
            assert expected == got
            o1 = ooid.uuid_to_ooid(u, timestamp=self.baseDate)
            expected = (self.baseDate, ooid.defaultDepth)
            got = ooid.dateAndDepthFromOoid(o1)
            assert expected == got
            o2 = ooid.uuid_to_ooid(u, depth=self.depths[i])
            expected = (self.nowstamp, self.depths[i])
            got = ooid.dateAndDepthFromOoid(o2)
            assert expected == got
            o3 = ooid.uuid_to_ooid(u, depth=self.depths[i], timestamp=self.xmas05)
            expected = (self.xmas05, self.depths[i])
            got = ooid.dateAndDepthFromOoid(o3)
            assert expected == got

    def testGetDate(self):
        for this_ooid in self.yyyyoids:
            assert self.baseDate == ooid.dateFromOoid(this_ooid)
            assert 4 == ooid.depthFromOoid(this_ooid)
        assert ooid.dateFromOoid(self.badooid0) is None
        assert ooid.dateFromOoid(self.badooid1) is None

    def testGetDateAndDepth(self):
        for i in range(len(self.dyyoids)):
            date, depth = ooid.dateAndDepthFromOoid(self.dyyoids[i])
            assert self.depths[i] == depth
            assert self.baseDate == date
        assert (None, None) == ooid.dateAndDepthFromOoid(self.badooid0)
        assert (None, None) == ooid.dateAndDepthFromOoid(self.badooid1)
