# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman.dotdict import DotDict
from mock import patch, call, Mock
import statsd

from socorro.external.statsd import dogstatsd
from socorro.external.statsd.metrics import StatsdMetrics
from socorro.unittest.testbase import TestCase


class TestStatsdMetrics(TestCase):
    def setup_config(self, statsd_class):
        config = DotDict()
        config.statsd_class = statsd_class
        config.statsd_host = 'localhost'
        config.statsd_port = 3333
        config.statsd_prefix = 'prefix'
        return config

    def test_capture_stats_with_dogstatsd(self):
        """Tests with dogstatsd StatsClient.

        Verifies .histogram() is called once for every key/val pair.

        """
        config = self.setup_config(statsd_class=dogstatsd.StatsClient)

        with patch('socorro.external.statsd.dogstatsd.statsd') as statsd_obj:
            statsd_metrics = StatsdMetrics(config)
            statsd_metrics.capture_stats(
                {'foo': 5, 'bar': 10}
            )

            statsd_obj.histogram.assert_has_calls([
                call('bar', 10),
                call('foo', 5),
            ])

    def test_capture_stats_with_statsd(self):
        """Tests with statsd StatsClient

        Verifies:

        * that .timing() gets called once for every key/val pair
        * that non-ints are converted to ints

        """
        config = self.setup_config(statsd_class=statsd.StatsClient)

        statsd_mock = Mock()
        statsd_metrics = StatsdMetrics(config)

        # Swap out the statsd client instance with a mock
        statsd_metrics.statsd = statsd_mock
        statsd_metrics.capture_stats(
            {'foo': 5, 'bar': 5.0}
        )

        statsd_mock.timing.assert_has_calls([
            call('bar', 5),
            call('foo', 5),
        ])
