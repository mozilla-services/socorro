# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This module holds the metrics base class. This is used in the collector.

"""

from configman import RequiredConfig, Namespace


class MetricsBase(RequiredConfig):
    """Base class for Metrics as well as a no-op default

    This is used by the collector on incoming crashes so that we can collect
    metrics on them. This data can be logged, sent to statsd,
    etc--functionality implemented by subclasses of this class.

    Subclasses should implement::

        def capture_stats(self, data_items):


    This method should never throw an exception. This method should return
    nothing.

    """

    required_config = Namespace()

    def __init__(self, config):
        super(MetricsBase, self).__init__()
        self.config = config

    def capture_stats(self, data_items):
        """Takes a dict of values to capture

        This is for measuring the statistical distribution of a set of values
        over time. For example, crash sizes or db query durations.

        :arg data_items: dict of key/value pairs; values are always ints

        """
        pass
