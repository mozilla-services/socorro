import unittest
import mock

from socorro.collector.collector_app import CollectorApp
from socorro.collector.wsgi_collector import Collector
from configman.dotdict import DotDict

class TestCollectorApp(unittest.TestCase):

    def get_standard_config(self):
        config = DotDict()

        config.logger = mock.MagicMock()

        config.collector = DotDict()
        config.collector.dump_id_prefix = 'bp-'
        config.collector.dump_field = 'dump'

        config.throttler = DotDict()
        self.mocked_throttler = mock.MagicMock()
        config.throttler.throttler_class = mock.MagicMock(
          return_value=self.mocked_throttler)

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

        self.assertEqual(config.crash_storage, self.mocked_crash_storage)
        self.assertEqual(config.throttler, self.mocked_throttler)
        self.assertEqual(c.web_server, self.mocked_web_server)

        config.storage.crashstorage_class.assert_called_with(config.storage)
        config.web_server.wsgi_server_class.assert_called_with(
          config,
          (Collector, )
        )
