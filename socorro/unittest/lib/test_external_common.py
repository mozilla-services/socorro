# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from nose.tools import eq_, ok_

from socorro.lib import external_common, util
from socorro.unittest.testbase import TestCase


#==============================================================================
class TestExternalCommon(TestCase):
    """Test functions of the external_common module. """

    #--------------------------------------------------------------------------
    def test_check_type(self):
        # Test 1: null
        param = None
        datatype = "datetime"
        res = external_common.check_type(param, datatype)
        eq_(res, None)

        # .....................................................................
        # Test 2: integer
        param = 12
        datatype = "int"
        res = external_common.check_type(param, datatype)

        ok_(isinstance(res, int))
        eq_(res, param)

        # .....................................................................
        # Test 3: integer
        param = "12"
        datatype = "int"
        res = external_common.check_type(param, datatype)

        ok_(isinstance(res, int))
        eq_(res, 12)

        # .....................................................................
        # Test 4: string
        param = datetime.datetime(2012, 01, 01)
        datatype = "str"
        res = external_common.check_type(param, datatype)

        ok_(isinstance(res, str))
        eq_(res, "2012-01-01 00:00:00")

        # .....................................................................
        # Test 5: boolean
        param = 1
        datatype = "bool"
        res = external_common.check_type(param, datatype)

        ok_(isinstance(res, bool))
        eq_(res, True)

        # .....................................................................
        # Test 6: boolean
        param = "T"
        datatype = "bool"
        res = external_common.check_type(param, datatype)

        ok_(isinstance(res, bool))
        eq_(res, True)

        # .....................................................................
        # Test 7: boolean
        param = 14
        datatype = "bool"
        res = external_common.check_type(param, datatype)

        ok_(isinstance(res, bool))
        eq_(res, False)

        # .....................................................................
        # Test 8: datetime
        param = "2012-01-01T00:00:00"
        datatype = "datetime"
        res = external_common.check_type(param, datatype)

        ok_(isinstance(res, datetime.datetime))
        eq_(res.year, 2012)
        eq_(res.month, 1)
        eq_(res.hour, 0)

        # .....................................................................
        # Test 9: timedelta
        param = "72"
        datatype = "timedelta"
        res = external_common.check_type(param, datatype)

        ok_(isinstance(res, datetime.timedelta))
        eq_(res.days, 3)

        # Test: date
        param = "2012-01-01"
        datatype = "date"
        res = external_common.check_type(param, datatype)

        ok_(isinstance(res, datetime.date))
        eq_(res.year, 2012)
        eq_(res.month, 1)
        eq_(res.day, 1)

    #--------------------------------------------------------------------------
    def test_parse_arguments(self):
        """Test external_common.parse_arguments(). """
        filters = [
            ("param1", "default", ["list", "str"]),
            ("param2", None, "int"),
            ("param3", ["list", "of", 4, "values"], ["list", "str"])
        ]
        arguments = {
            "param1": "value1",
            "unknown": 12345
        }
        params_exp = util.DotDict()
        params_exp.param1 = ["value1"]
        params_exp.param2 = None
        params_exp.param3 = ["list", "of", "4", "values"]

        params = external_common.parse_arguments(filters, arguments)

        eq_(params, params_exp)
