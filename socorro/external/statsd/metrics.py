# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""This module holds statsd metrics classes. Currently these are used in the
collector.

"""

from configman import Namespace, class_converter
from socorro.external.metrics_base import MetricsBase


class StatsdMetrics(MetricsBase):
    """Metrics component that sends data to statsd

    """
    required_config = Namespace()
    required_config.add_option(
        'statsd_class',
        doc='the fully qualified name of the statsd client',
        default='socorro.external.statsd.dogstatsd.StatsClient',
        reference_value_from='resource.statsd',
        from_string_converter=class_converter,
    )
    required_config.add_option(
        'statsd_host',
        doc='the hostname of statsd',
        default='',
        reference_value_from='resource.statsd',
    )
    required_config.add_option(
        'statsd_port',
        doc='the port number for statsd',
        default=8125,
        reference_value_from='resource.statsd',
    )
    required_config.add_option(
        'statsd_prefix',
        doc='a string to be used as the prefix for statsd names',
        default='save_processed',
        reference_value_from='resource.statsd',
    )

    def __init__(self, config):
        super(StatsdMetrics, self).__init__(config)

        if config.statsd_prefix:
            self.prefix = config.statsd_prefix
        else:
            self.prefix = ''

        self.statsd = self.config.statsd_class(
            config.statsd_host,
            config.statsd_port,
            self.prefix
        )

        # Cache whether the statds client has a .histogram() method or not.
        self._has_histogram = hasattr(self.statsd, 'histogram')

    def capture_stats(self, data_items):
        for key, val in sorted(data_items.items()):
            if self._has_histogram:
                # .histogram() is a dogstatsd enhancement to statsd, so we can
                # only use it with dogstatsd.
                self.statsd.histogram(key, val)
            else:
                # .timing() takes a value which is a duration in milliseconds,
                # but we're going to use it for non duration type values, too.
                self.statsd.timing(key, int(val))
