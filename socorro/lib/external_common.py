# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Common functions for external modules.
"""

import json
import datetime

from socorro.lib import BadArgumentError
from socorro.lib.util import DotDict
import socorro.lib.datetimeutil as dtutil


def parse_arguments(filters, arguments, modern=False):
    """
    Return a dict of parameters.
    Take a list of filters and for each try to get the corresponding
    value in arguments or a default value. Then check that value's type.
    The @modern parameter indicates how the arguments should be
    interpreted. The old way is that you always specify a list and in
    the list you write the names of types as strings. I.e. instad of
    `str` you write `'str'`.
    The modern way allows you to specify arguments by real Python types
    and entering it as a list means you accept and expect it to be a list.
    For example, using the modern way:
        filters = [
            ("param1", "default", [str]),
            ("param2", None, int),
            ("param3", ["list", "of", 4, "values"], [str])
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
    And an example for the old way:
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
    The reason for having the modern and the non-modern way is
    transition of legacy code. One day it will all be the modern way.
    """
    params = DotDict()

    for i in filters:
        count = len(i)
        param = None

        if count <= 1:
            param = arguments.get(i[0])
        else:
            param = arguments.get(i[0], i[1])

        # proceed and do the type checking
        if count >= 3:
            types = i[2]

            if modern:
                if isinstance(types, list) and param is not None:
                    assert len(types) == 1
                    if not isinstance(param, list):
                        param = [param]
                    param = [check_type(x, types[0]) for x in param]
                else:
                    param = check_type(param, types)
            else:
                if not isinstance(types, list):
                    types = [types]

                for t in reversed(types):
                    if t == "list" and not isinstance(param, list):
                        if param is None or param == '':
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

    if getattr(datatype, 'clean', None) and callable(datatype.clean):
        try:
            return datatype.clean(param)
        except ValueError:
            raise BadArgumentError(param)

    elif isinstance(datatype, str):
        # You've given it something like `'bool'` as a string.
        # This is the legacy way of doing it.
        datatype = {
            'str': str,
            'bool': bool,
            'float': float,
            'date': datetime.date,
            'datetime': datetime.datetime,
            'timedelta': datetime.timedelta,
            'json': 'json',  # exception
            'int': int,
        }[datatype]

    if datatype is str and not isinstance(param, basestring):
        try:
            param = str(param)
        except ValueError:
            param = str()

    elif datatype is int and not isinstance(param, int):
        try:
            param = int(param)
        except ValueError:
            param = int()

    elif datatype is bool and not isinstance(param, bool):
        param = str(param).lower() in ("true", "t", "1", "y", "yes")

    elif (
        datatype is datetime.datetime and
        not isinstance(param, datetime.datetime)
    ):
        try:
            param = dtutil.string_to_datetime(param)
        except ValueError:
            param = None

    elif datatype is datetime.date and not isinstance(param, datetime.date):
        try:
            param = dtutil.string_to_datetime(param).date()
        except ValueError:
            param = None

    elif (
        datatype is datetime.timedelta and
        not isinstance(param, datetime.timedelta)
    ):
        try:
            param = dtutil.strHoursToTimeDelta(param)
        except ValueError:
            param = None

    elif datatype == "json" and isinstance(param, basestring):
        try:
            param = json.loads(param)
        except ValueError:
            param = None

    return param
