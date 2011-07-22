from datetime import timedelta, datetime

import socorro.unittest.testlib.expectations as expect
import socorro.search.searchapi as sapi
import socorro.lib.util as util


def test_get_parameters():
    """
    Test SearchAPI.get_parameters()

    """
    params = sapi.SearchAPI.get_parameters({})
    assert params, "SearchAPI.get_parameters() returned something empty or null."
    for i in params:
        typei = type(params[i])
        if i == "from_date" or i == "to_date":
            assert typei is datetime, "The parameter %s is of a non expected type %s, should be datetime" % (i, typei)
        else:
            assert not params[i] or typei is int or typei is str or typei is list, "The parameter %s is of a non expected type %s" % (i, typei)

def test_secure_fields():
    """
    Test SearchAPI.secure_fields()

    """
    fields = ["signatute", "signature", "123456sfdgerw&$%#&", "dump", None, "dump"]
    theoric_fields = ["signature", "dump"]
    secured_fields = sapi.SearchAPI.secure_fields(fields)
    assert secured_fields == theoric_fields, "Secured fields expected %s, received %s" % (theoric_fields, secured_fields)

    fields = []
    theoric_fields = "signature"
    secured_fields = sapi.SearchAPI.secure_fields(fields)
    assert secured_fields == theoric_fields, "Secured fields expected %s, received %s" % (theoric_fields, secured_fields)

    fields = None
    theoric_fields = "signature"
    secured_fields = sapi.SearchAPI.secure_fields(fields)
    assert secured_fields == theoric_fields, "Secured fields expected %s, received %s" % (theoric_fields, secured_fields)

    fields = ["nothing"]
    theoric_fields = "signature"
    secured_fields = sapi.SearchAPI.secure_fields(fields)
    assert secured_fields == theoric_fields, "Secured fields expected %s, received %s" % (theoric_fields, secured_fields)
