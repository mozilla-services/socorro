"""
Common functions for external modules.
"""

from datetime import datetime, timedelta
from socorro.lib.util import DotDict

import socorro.lib.datetimeutil as dtutil


def parse_arguments(filters, arguments):
    """
    Return a dict of parameters.

    Take a list of filters and for each try to get the corresponding
    value in arguments or a default value. Then check that value's type.

    Example:
        filters = [
            ("param1", "default", ["list", "str"]),
            ("param2", None, "int"),
            ("param3", ["list", "of", 4, "values"], ["list", "str"])
        ]
        arguments = {
            "param1": "value1",
            "unknown": 12345
        }
        =>
        {
            "param1": ["value1"],
            "param2": 0,
            "param3": ["list", "of", "4", "values"]
        }
    """
    params = DotDict()

    for i in filters:
        count = len(i)
        param = None

        if count <= 1:
            param = arguments.get(i[0])
        else:
            param = arguments.get(i[0], i[1])

        if count >= 3:
            types = i[2]
            if not isinstance(types, list):
                types = [types]

            for t in reversed(types):
                if t == "list" and not isinstance(param, list):
                    if param is None:
                        param = []
                    else:
                        param = [param]
                elif t == "list" and isinstance(param, list):
                    continue
                elif isinstance(param, list) and "list" not in types:
                    param = " ".join(param)
                    param = check_type(param, t)
                elif isinstance(param, list):
                    param = [check_type(x, t) for x in param]
                else:
                    param = check_type(param, t)

        params[i[0]] = param
    return params

def check_type(param, datatype):
    """
    Make sure that param is of type datatype and return it.

    If param is None, return it.
    If param is an instance of datatype, return it.
    If param is not an instance of datatype and is not None, cast it as
    datatype and return it.
    """
    if param is None:
        return param

    if datatype == "str" and not isinstance(param, basestring):
        try:
            param = str(param)
        except ValueError:
            param = str()

    elif datatype == "int" and not isinstance(param, int):
        try:
            param = int(param)
        except ValueError:
            param = int()

    elif datatype == "bool" and not isinstance(param, bool):
        try:
            param = param.lower() in ("true", "t", "1", "y", "yes")
        except AttributeError:
            param = False

    elif datatype == "datetime" and not isinstance(param, datetime):
        try:
            param = dtutil.string_to_datetime(param)
        except ValueError:
            param = None

    elif datatype == "timedelta" and not isinstance(param, timedelta):
        try:
            param = dtutil.strHoursToTimeDelta(param)
        except ValueError:
            param = None

    return param
