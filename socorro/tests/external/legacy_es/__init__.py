# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from distutils.version import LooseVersion
from functools import wraps

import pytest


# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


def minimum_es_version(minimum_version):
    """Skip the test if the Elasticsearch version is less than specified

    :arg minimum_version: string; the minimum Elasticsearch version required

    """

    def decorated(test):
        """Decorator to only run the test if ES version is greater or equal than specified"""

        @wraps(test)
        def test_with_version(self):
            """Only run the test if ES version is not less than specified"""
            actual_version = self.conn.info()["version"]["number"]
            if LooseVersion(actual_version) >= LooseVersion(minimum_version):
                test(self)
            else:
                pytest.skip()

        return test_with_version

    return decorated
