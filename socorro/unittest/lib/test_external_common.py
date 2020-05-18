# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from configman.dotdict import DotDict
import isodate
import pytest

from socorro.lib import BadArgumentError, external_common


class TestExternalCommon:
    """Test functions of the external_common module. """

    def test_check_type(self):
        # Test 1: null
        param = None
        datatype = "datetime"
        res = external_common.check_type(param, datatype)
        assert res is None

        # Test 2: integer
        param = 12
        datatype = "int"
        res = external_common.check_type(param, datatype)

        assert res == param

        # Test 3: integer
        param = "12"
        datatype = "int"
        res = external_common.check_type(param, datatype)

        assert res == 12

        # Test 4: string
        param = datetime.datetime(2012, 1, 1)
        datatype = "str"
        res = external_common.check_type(param, datatype)

        assert res == "2012-01-01 00:00:00"

        # Test 5: boolean
        param = 1
        datatype = "bool"
        res = external_common.check_type(param, datatype)

        assert res is True

        # Test 6: boolean
        param = "T"
        datatype = "bool"
        res = external_common.check_type(param, datatype)

        assert res is True

        # Test 7: boolean
        param = 14
        datatype = "bool"
        res = external_common.check_type(param, datatype)

        assert res is False

        # Test 8: datetime
        param = "2012-01-01T00:00:00"
        datatype = "datetime"
        res = external_common.check_type(param, datatype)

        assert isinstance(res, datetime.datetime)
        assert res.year == 2012
        assert res.month == 1
        assert res.hour == 0

        # Test 9: timedelta
        param = "72"
        datatype = "timedelta"
        res = external_common.check_type(param, datatype)

        assert isinstance(res, datetime.timedelta)
        assert res.days == 3

        # Test: date
        param = "2012-01-01"
        datatype = "date"
        res = external_common.check_type(param, datatype)

        assert isinstance(res, datetime.date)
        assert res.year == 2012
        assert res.month == 1
        assert res.day == 1

    def test_parse_arguments_old_way(self):
        """Test external_common.parse_arguments(). """
        filters = [
            ("param1", "default", ["list", "str"]),
            ("param2", None, "int"),
            ("param3", ["list", "of", 4, "values"], ["list", "str"]),
        ]
        arguments = {"param1": "value1", "unknown": 12345}
        params_exp = DotDict()
        params_exp.param1 = ["value1"]
        params_exp.param2 = None
        params_exp.param3 = ["list", "of", "4", "values"]

        params = external_common.parse_arguments(filters, arguments, modern=False)

        assert params == params_exp

    def test_parse_arguments(self):
        """Test external_common.parse_arguments(). """
        filters = [
            ("param1", "default", [str]),
            ("param2", None, int),
            ("param3", ["some", "default", "list"], [str]),
            ("param4", ["list", "of", 4, "values"], [str]),
            ("param5", None, bool),
            ("param6", None, datetime.date),
            ("param7", None, datetime.date),
            ("param8", None, datetime.datetime),
            ("param9", None, [str]),
        ]
        arguments = {
            "param1": "value1",
            "unknown": 12345,
            "param5": "true",
            "param7": datetime.date(2016, 2, 9).isoformat(),
            "param8": datetime.datetime(2016, 2, 9).isoformat(),
            # note the 'param9' is deliberately not specified.
        }
        params_exp = DotDict()
        params_exp.param1 = ["value1"]
        params_exp.param2 = None
        params_exp.param3 = ["some", "default", "list"]
        params_exp.param4 = ["list", "of", "4", "values"]
        params_exp.param5 = True
        params_exp.param6 = None
        params_exp.param7 = datetime.date(2016, 2, 9)
        params_exp.param8 = datetime.datetime(2016, 2, 9).replace(tzinfo=isodate.UTC)
        params_exp.param9 = None

        params = external_common.parse_arguments(filters, arguments, modern=True)
        for key in params:
            assert params[key] == params_exp[key]
        assert params == params_exp

    def test_parse_arguments_with_class_validators(self):
        class NumberConverter:
            def clean(self, value):
                conv = {"one": 1, "two": 2, "three": 3}
                try:
                    return conv[value]
                except KeyError:
                    raise ValueError("No idea?!")

        # Define a set of filters with some types being non-trivial types
        # but instead a custom validator.

        filters = [("param1", 0, NumberConverter())]
        arguments = {"param1": "one"}
        params_exp = DotDict()
        params_exp.param1 = 1

        params = external_common.parse_arguments(filters, arguments, modern=True)
        assert params == params_exp

        # note that a ValueError becomes a BadArgumentError
        arguments = {"param1": "will cause a ValueError in NumberConverter.clean"}
        with pytest.raises(BadArgumentError):
            external_common.parse_arguments(filters, arguments, modern=True)
