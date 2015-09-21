# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import mock
from nose.tools import eq_, ok_

from socorro.collector.collector_app import CollectorApp, Collector2015App
from socorro.collector.wsgi_breakpad_collector import BreakpadCollector2015
from socorro.unittest.testbase import TestCase
from configman.dotdict import DotDict


class TestCollectorApp(TestCase):

    def get_standard_config(self):
        config = DotDict()

        config.logger = mock.MagicMock()

        config.collector = DotDict()
        config.collector.collector_class = BreakpadCollector2015
        config.collector.dump_id_prefix = 'bp-'
        config.collector.dump_field = 'dump'
        config.collector.accept_submitted_crash_id = False

        config.throttler = DotDict()
        self.mocked_throttler = mock.MagicMock()
        config.throttler.throttler_class = mock.MagicMock(
            return_value=self.mocked_throttler
        )

        config.storage = mock.MagicMock()
        self.mocked_crash_storage = mock.MagicMock()
        config.storage.crashstorage_class = mock.MagicMock(
            return_value=self.mocked_crash_storage
        )

        config.web_server = mock.MagicMock()
        self.mocked_web_server = mock.MagicMock()
        config.web_server.wsgi_server_class = mock.MagicMock(
            return_value=self.mocked_web_server
        )

        return config

    def test_main(self):
        config = self.get_standard_config()
        c = CollectorApp(config)
        c.main()

        eq_(c.web_server, self.mocked_web_server)

        config.web_server.wsgi_server_class.assert_called_with(
            config,
            (BreakpadCollector2015, )
        )


class TestCollector2015App(TestCase):

    def get_standard_config(self):
        config = DotDict()

        config.logger = mock.MagicMock()

        config.services = DotDict()
        config.services.services_controller = DotDict()

        class Service1(object):
            pass
        config.services.service1 = DotDict()
        config.services.service1.service_implementation_class = Service1

        class Service2(object):
            pass
        config.services.service2 = DotDict()
        config.services.service2.service_implementation_class = Service2

        config.services.services_controller.service_list = [
            ('service1', '/submit', Service1),
            ('service2', '/unsubmit', Service2),
        ]

        config.web_server = DotDict()
        self.mocked_web_server = mock.MagicMock()
        config.web_server.wsgi_server_class = mock.MagicMock(
            return_value=self.mocked_web_server
        )

        return config

    def test_main(self):
        config = self.get_standard_config()
        c = Collector2015App(config)
        c.main()

        eq_(config.web_server.wsgi_server_class.call_count, 1)
        args, kwargs = config.web_server.wsgi_server_class.call_args
        eq_(len(args), 2)
        eq_(len(kwargs), 0)

        eq_(args[0], config)

        service1_uri, service1_impl = args[1][0]
        eq_(service1_uri, '/submit')
        ok_(hasattr(service1_impl, 'wrapped_partial'))

        service2_uri, service2_impl = args[1][1]
        eq_(service2_uri, '/unsubmit')
        ok_(hasattr(service2_impl, 'wrapped_partial'))
