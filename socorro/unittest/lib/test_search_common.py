import unittest

from datetime import datetime

import socorro.lib.search_common as co
import socorro.unittest.testlib.util as tutil


def setup_module():
    tutil.nosePrintModule(__file__)


def test_get_parameters():
    """
    Test SearchCommon.get_parameters()
    """
    # Empty params, only default values are returned
    params = co.get_parameters({})
    assert params, (
            "SearchCommon.get_parameters() returned something empty or null.")
    for i in params:
        typei = type(params[i])
        if i in ("from_date", "to_date", "build_from", "build_to"):
            assert typei is datetime, (
                        "The parameter %s is of a non expected type %s, "
                        "should be datetime" % (i, typei))
        else:
            assert (not params[i] or typei is int or typei is str or
                    typei is list), (
                        "The parameter %s is of a non expected type %s" %
                        (i, typei))

    # Empty params
    params = co.get_parameters({
        "terms": "",
        "fields": "",
        "products": "",
        "from_date": "",
        "to_date": "",
        "versions": "",
        "reasons": "",
        "os": "",
        "branches": "",
        "search_mode": "",
        "build_ids": "",
        "report_process": "",
        "report_type": "",
        "plugin_in": "",
        "plugin_search_mode": "",
        "plugin_terms": ""
    })
    assert params, (
            "SearchCommon.get_parameters() returned something empty or null.")
    for i in params:
        typei = type(params[i])
        if i in ("from_date", "to_date", "build_from", "build_to"):
            assert typei is datetime, (
                        "The parameter %s is of a non expected type %s, "
                        "should be datetime" % (i, typei))
        else:
            assert (not params[i] or typei is int or typei is str or
                    typei is list), (
                        "The parameter %s is of a non expected type %s" %
                        (i, typei))


def test_restrict_fields():
    """
    Test SearchCommon.restrict_fields()
    """
    fields = ["signatute", "signature", "123456sfdgerw&$%#&", "dump",
              None, "dump"]
    theoric_fields = ["signature", "dump"]
    restricted_fields = co.restrict_fields(fields)
    assert restricted_fields == theoric_fields, (
                "Restricted fields expected %s, received %s" %
                (theoric_fields, restricted_fields))

    fields = []
    theoric_fields = "signature"
    restricted_fields = co.restrict_fields(fields)
    assert restricted_fields == theoric_fields, (
                "Restricted fields expected %s, received %s" %
                (theoric_fields, restricted_fields))

    fields = None
    theoric_fields = "signature"
    restricted_fields = co.restrict_fields(fields)
    assert restricted_fields == theoric_fields, (
                "Restricted fields expected %s, received %s" %
                (theoric_fields, restricted_fields))

    fields = ["nothing"]
    theoric_fields = "signature"
    restricted_fields = co.restrict_fields(fields)
    assert restricted_fields == theoric_fields, (
                "Restricted fields expected %s, received %s" %
                (theoric_fields, restricted_fields))
