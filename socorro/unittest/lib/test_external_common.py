import unittest
import datetime

from socorro.lib import external_common, util

import socorro.unittest.testlib.util as testutil


#------------------------------------------------------------------------------
def setup_module():
    testutil.nosePrintModule(__file__)


#==============================================================================
class TestExternalCommon(unittest.TestCase):
    """Test functions of the external_common module. """

    #--------------------------------------------------------------------------
    def test_check_type(self):
        # Test 1: null
        param = None
        datatype = "datetime"
        res = external_common.check_type(param, datatype)
        self.assertEqual(res, None)

        # .....................................................................
        # Test 2: integer
        param = 12
        datatype = "int"
        res = external_common.check_type(param, datatype)

        self.assertTrue(isinstance(res, int))
        self.assertEqual(res, param)

        # .....................................................................
        # Test 3: integer
        param = "12"
        datatype = "int"
        res = external_common.check_type(param, datatype)

        self.assertTrue(isinstance(res, int))
        self.assertEqual(res, 12)

        # .....................................................................
        # Test 4: string
        param = datetime.datetime(2012, 01, 01)
        datatype = "str"
        res = external_common.check_type(param, datatype)

        self.assertTrue(isinstance(res, str))
        self.assertEqual(res, "2012-01-01 00:00:00")

        # .....................................................................
        # Test 5: boolean
        param = 1
        datatype = "bool"
        res = external_common.check_type(param, datatype)

        self.assertTrue(isinstance(res, bool))
        self.assertEqual(res, True)

        # .....................................................................
        # Test 6: boolean
        param = "T"
        datatype = "bool"
        res = external_common.check_type(param, datatype)

        self.assertTrue(isinstance(res, bool))
        self.assertEqual(res, True)

        # .....................................................................
        # Test 7: boolean
        param = 14
        datatype = "bool"
        res = external_common.check_type(param, datatype)

        self.assertTrue(isinstance(res, bool))
        self.assertEqual(res, False)

        # .....................................................................
        # Test 8: datetime
        param = "2012-01-01T00:00:00"
        datatype = "datetime"
        res = external_common.check_type(param, datatype)

        self.assertTrue(isinstance(res, datetime.datetime))
        self.assertEqual(res.year, 2012)
        self.assertEqual(res.month, 1)
        self.assertEqual(res.hour, 0)

        # .....................................................................
        # Test 9: timedelta
        param = "72"
        datatype = "timedelta"
        res = external_common.check_type(param, datatype)

        self.assertTrue(isinstance(res, datetime.timedelta))
        self.assertEqual(res.days, 3)

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

        self.assertEqual(params, params_exp)
