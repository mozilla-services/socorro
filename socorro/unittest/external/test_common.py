from datetime import datetime

import socorro.external.common as co


def test_get_parameters():
    """
    Test Common.get_parameters()
    """
    # Empty params, only default values are returned
    params = co.Common.get_parameters({})
    assert params, (
                "Common.get_parameters() returned something empty or null.")
    for i in params:
        typei = type(params[i])
        if i == "from_date" or i == "to_date":
            assert typei is datetime, (
                        "The parameter %s is of a non expected type %s, "
                        "should be datetime" % (i, typei))
        else:
            assert (not params[i] or typei is int or typei is str or
                    typei is list), (
                        "The parameter %s is of a non expected type %s" %
                        (i, typei))

    # Empty params
    params = co.Common.get_parameters({
        "for": "",
        "in": "",
        "product": "",
        "from": "",
        "to": "",
        "version": "",
        "reason": "",
        "os": "",
        "branches": "",
        "search_mode": "",
        "build": "",
        "report_process": "",
        "report_type": "",
        "plugin_in": "",
        "plugin_search_mode": "",
        "plugin_term": ""
    })
    assert params, (
                "Common.get_parameters() returned something empty or null.")
    for i in params:
        typei = type(params[i])
        if i == "from_date" or i == "to_date":
            assert typei is datetime, (
                        "The parameter %s is of a non expected type %s, "
                        "should be datetime" % (i, typei))
        else:
            assert (not params[i] or typei is int or typei is str or
                    typei is list), (
                        "The parameter %s is of a non expected type %s" %
                        (i, typei))


def test_secure_fields():
    """
    Test Common.restrict_fields()
    """
    fields = ["signatute", "signature", "123456sfdgerw&$%#&", "dump",
              None, "dump"]
    theoric_fields = ["signature", "dump"]
    restricted_fields = co.Common.restrict_fields(fields)
    assert restricted_fields == theoric_fields, (
                "Restricted fields expected %s, received %s" %
                (theoric_fields, restricted_fields))

    fields = []
    theoric_fields = "signature"
    restricted_fields = co.Common.restrict_fields(fields)
    assert restricted_fields == theoric_fields, (
                "Restricted fields expected %s, received %s" %
                (theoric_fields, restricted_fields))

    fields = None
    theoric_fields = "signature"
    restricted_fields = co.Common.restrict_fields(fields)
    assert restricted_fields == theoric_fields, (
                "Restricted fields expected %s, received %s" %
                (theoric_fields, restricted_fields))

    fields = ["nothing"]
    theoric_fields = "signature"
    restricted_fields = co.Common.restrict_fields(fields)
    assert restricted_fields == theoric_fields, (
                "Restricted fields expected %s, received %s" %
                (theoric_fields, restricted_fields))


def test_format_date():
    """
    Test Common.format_date()
    """
    # Empty date
    date = ""
    res = co.Common.format_date(date)
    assert not res, "Date is %s, null expected." % date

    # YY-mm-dd date
    date = "2001-11-30"
    res = co.Common.format_date(date)
    expected = datetime(2001, 11, 30)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # YY-mm-dd+HH:ii:ss date
    date = "2001-11-30+12:34:56"
    res = co.Common.format_date(date)
    expected = datetime(2001, 11, 30, 12, 34, 56)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # YY-mm-dd+HH:ii:ss.S date
    date = "2001-11-30 12:34:56.123456"
    res = co.Common.format_date(date)
    expected = datetime(2001, 11, 30, 12, 34, 56, 123456)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # Separated date
    date = ["2001-11-30", "12:34:56"]
    res = co.Common.format_date(date)
    expected = datetime(2001, 11, 30, 12, 34, 56)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # Invalid date
    date = "2001-11-32"
    res = co.Common.format_date(date)
    assert not res, "Date is %s, null expected." % date
