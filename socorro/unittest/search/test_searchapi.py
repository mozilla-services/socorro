from datetime import datetime

import socorro.search.searchapi as sapi


def test_get_parameters():
    """
    Test SearchAPI.get_parameters()

    """
    # Empty params, only default values are returned
    params = sapi.SearchAPI.get_parameters({})
    assert params, (
                "SearchAPI.get_parameters() returned something empty or null.")
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
    params = sapi.SearchAPI.get_parameters({
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
                "SearchAPI.get_parameters() returned something empty or null.")
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
    Test SearchAPI.secure_fields()

    """
    fields = ["signatute", "signature", "123456sfdgerw&$%#&", "dump",
              None, "dump"]
    theoric_fields = ["signature", "dump"]
    secured_fields = sapi.SearchAPI.secure_fields(fields)
    assert secured_fields == theoric_fields, (
                "Secured fields expected %s, received %s" %
                (theoric_fields, secured_fields))

    fields = []
    theoric_fields = "signature"
    secured_fields = sapi.SearchAPI.secure_fields(fields)
    assert secured_fields == theoric_fields, (
                "Secured fields expected %s, received %s" %
                (theoric_fields, secured_fields))

    fields = None
    theoric_fields = "signature"
    secured_fields = sapi.SearchAPI.secure_fields(fields)
    assert secured_fields == theoric_fields, (
                "Secured fields expected %s, received %s" %
                (theoric_fields, secured_fields))

    fields = ["nothing"]
    theoric_fields = "signature"
    secured_fields = sapi.SearchAPI.secure_fields(fields)
    assert secured_fields == theoric_fields, (
                "Secured fields expected %s, received %s" %
                (theoric_fields, secured_fields))


def test_format_date():
    """
    Test SearchAPI.format_date()

    """
    # Empty date
    date = ""
    res = sapi.SearchAPI.format_date(date)
    assert not res, "Date is %s, null expected." % date

    # YY-mm-dd date
    date = "2001-11-30"
    res = sapi.SearchAPI.format_date(date)
    expected = datetime(2001, 11, 30)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # YY-mm-dd+HH:ii:ss date
    date = "2001-11-30+12:34:56"
    res = sapi.SearchAPI.format_date(date)
    expected = datetime(2001, 11, 30, 12, 34, 56)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # YY-mm-dd+HH:ii:ss.S date
    date = "2001-11-30 12:34:56.123456"
    res = sapi.SearchAPI.format_date(date)
    expected = datetime(2001, 11, 30, 12, 34, 56, 123456)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # Separated date
    date = ["2001-11-30", "12:34:56"]
    res = sapi.SearchAPI.format_date(date)
    expected = datetime(2001, 11, 30, 12, 34, 56)
    assert res == expected, "Date is %s, %s expected." % (date, expected)

    # Invalid date
    date = "2001-11-32"
    res = sapi.SearchAPI.format_date(date)
    assert not res, "Date is %s, null expected." % date
