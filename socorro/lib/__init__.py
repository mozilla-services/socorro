# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""common library code for socorro modules"""


class InsertionError(Exception):
    """When an insertion into a storage system failed. """
    pass


class DatabaseError(Exception):
    """When querying a storage system failed. """
    pass


class MissingArgumentError(Exception):
    """When a mandatory argument is missing or empty. """
    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        try:
            msg = "Mandatory parameter(s) '%s' is missing or empty." \
                % self.arg
            return msg
        except Exception:
            pass


class BadArgumentError(Exception):
    """When a mandatory argument has a bad value. """
    def __init__(self, param, received=None, expected=None, msg=None):
        self.param = param
        self.msg = msg
        self.received = received
        self.expected = expected

    def __str__(self):
        if self.msg is not None:
            return self.msg

        try:
            msg = "Bad value for parameter(s) '%s'" % self.param
            if self.received is not None:
                msg = msg + " got '%s'" % self.received
            if self.expected is not None:
                msg = msg + " expected '%s'" % self.expected
            return msg
        except Exception:
            pass


class ResourceNotFound(Exception):
    """When a resource could not be found in a storage system. """
    pass


class ResourceUnavailable(Exception):
    """When a resource could not be found in a storage system because it is
    not ready yet (but could be accessible later). """
    pass


class ServiceUnavailable(Exception):
    """When a service is requested but cannot be found"""
    pass
