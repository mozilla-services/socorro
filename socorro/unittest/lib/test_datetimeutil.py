import unittest

from datetime import datetime

import socorro.lib.datetimeutil as dtutil
import socorro.unittest.testlib.util as tutil


def setup_module():
    tutil.nosePrintModule(__file__)


def test_string_to_datetime():
    """
    Test datetimeutil.string_to_datetime()
    """
    # Empty date
    date = ""
    try:
        res = dtutil.string_to_datetime(date)
    except ValueError:
        res = None
    assert not res, "Date is %s, null expected." % date

    # YY-mm-dd date
    date = "2001-11-30"
    try:
        res = dtutil.string_to_datetime(date)
    except ValueError:
        res = None
    expected = datetime(2001, 11, 30)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # YY-mm-dd+HH:ii:ss date
    date = "2001-11-30+12:34:56"
    try:
        res = dtutil.string_to_datetime(date)
    except ValueError:
        res = None
    expected = datetime(2001, 11, 30, 12, 34, 56)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # YY-mm-dd+HH:ii:ss.S date
    date = "2001-11-30 12:34:56.123456"
    try:
        res = dtutil.string_to_datetime(date)
    except ValueError:
        res = None
    expected = datetime(2001, 11, 30, 12, 34, 56, 123456)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # Separated date
    date = ["2001-11-30", "12:34:56"]
    try:
        res = dtutil.string_to_datetime(date)
    except ValueError:
        res = None
    expected = datetime(2001, 11, 30, 12, 34, 56)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # Invalid date
    date = "2001-11-32"
    try:
        res = dtutil.string_to_datetime(date)
    except ValueError:
        res = None
    assert not res, "Date is %s, null expected." % date
