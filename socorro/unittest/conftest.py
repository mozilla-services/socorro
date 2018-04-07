# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from markus.testing import MetricsMock
import pytest


@pytest.fixture
def metricsmock():
    """Returns MetricsMock that a context to record metrics records

    Usage::

        def test_something(metricsmock):
            with metricsmock as mm:
                # do stuff
                assert mm.has_record(
                    'incr',
                    stat='some.stat',
                    value=1
                )

    https://markus.readthedocs.io/en/latest/testing.html

    """
    return MetricsMock()
