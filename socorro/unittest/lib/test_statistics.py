# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from mock import Mock, patch, call

from socorro.lib.util import DotDict, SilentFakeLogger
from socorro.lib.statistics import StatisticsForStatsd

class TestStatsd(unittest.TestCase):

    def setUp(self):
        self.logger = SilentFakeLogger()
        pass

    def tearDown(self):
        pass

    def test_statistics_all_good(self):
        d = DotDict()
        d.statsd_host = 'localhost'
        d.statsd_port = 666
        d.prefix = 'a.b'
        d.active_counters_list = ['x', 'y', 'z']

        with patch('socorro.lib.statistics.StatsClient') as StatsClientMocked:
            s = StatisticsForStatsd(d, 'processor')
            StatsClientMocked.assert_called_with(
                'localhost', 666, 'a.b.processor')

            s.incr('x')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [call.incr('a.b.processor.x')]
            )

            s.incr('y')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [call.incr('a.b.processor.y')]
            )

            s.incr('z')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [call.incr('a.b.processor.z')]
            )

            s.incr('w')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [
                    call.incr('a.b.processor.y'),
                    call.incr('a.b.processor.x'),
                    call.incr('a.b.processor.y')
                ]
            )

            s.incr(None)
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [
                    call.incr('a.b.processor.y'),
                    call.incr('a.b.processor.x'),
                    call.incr('a.b.processor.y'),
                    call.incr('a.b.processor.unknown')
                ]
            )



    def test_statistics_all_missing_prefix(self):
        d = DotDict()
        d.statsd_host = 'localhost'
        d.statsd_port = 666
        d.prefix = None
        d.active_counters_list = ['x', 'y', 'z']

        with patch('socorro.lib.statistics.StatsClient') as StatsClientMocked:
            s = StatisticsForStatsd(d, 'processor')
            StatsClientMocked.assert_called_with(
                'localhost', 666, 'processor')

            s.incr('x')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [call.incr('processor.x')]
            )

            s.incr('y')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [call.incr('processor.y')]
            )

            s.incr('z')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [call.incr('processor.z')]
            )

            s.incr('w')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [
                    call.incr('processor.y'),
                    call.incr('processor.x'),
                    call.incr('processor.y')
                ]
            )

            s.incr(None)
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [
                    call.incr('processor.y'),
                    call.incr('processor.x'),
                    call.incr('processor.y'),
                    call.incr('processor.unknown')
                ]
            )


    def test_statistics_all_missing_prefix_and_missing_name(self):
        d = DotDict()
        d.statsd_host = 'localhost'
        d.statsd_port = 666
        d.prefix = None
        d.active_counters_list = ['x', 'y', 'z']

        with patch('socorro.lib.statistics.StatsClient') as StatsClientMocked:
            s = StatisticsForStatsd(d, None)
            StatsClientMocked.assert_called_with(
                'localhost', 666, '')

            s.incr('x')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [call.incr('x')]
            )

            s.incr('y')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [call.incr('y')]
            )

            s.incr('z')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [call.incr('z')]
            )

            s.incr('w')
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [
                    call.incr('y'),
                    call.incr('x'),
                    call.incr('y')
                ]
            )

            s.incr(None)
            StatsClientMocked.assert_has_calls(
                StatsClientMocked.mock_calls,
                [
                    call.incr('y'),
                    call.incr('x'),
                    call.incr('y'),
                    call.incr('unknown')
                ]
            )




