# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""Tools to interact with external resources we use in Socorro. It contains
mainly storage systems. """


class InsertionError(Exception):
    """When an insertion into a storage system failed. """
    pass


class DatabaseError(Exception):
    """When querying a storage system failed. """
    pass


class MissingOrBadArgumentError(Exception):
    """When a mandatory argument is missing or has a bad value. """
    pass
