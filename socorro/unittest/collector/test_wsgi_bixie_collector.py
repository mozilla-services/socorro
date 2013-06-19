# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock

from datetime import datetime

from configman.dotdict import DotDict

from socorro.collector.wsgi_bixie_collector import BixieCollector
from socorro.collector.throttler import ACCEPT, IGNORE

expected_raw_crash = {
    "submitted_timestamp": "2013-05-04T15:10:00",
    "base_uri": "BASE_URI",
    "project_id": "PROJECT_ID",
    "sentry_version": u"2.0",
    "crash_id": "c796b8db-f5b4-40b1-8849-bb7682130504",
    "sentry_client": u"raven-js/1.0.7",
    "sentry_key": "public",
    "sentry_data": {
        u"sentry.interfaces.Exception": {
            u"type": u"ReferenceError",
            u"value": u"Can't find variable: doSomething"
        },
        "culprit": u"file:///Users/lonnen/repos/hrafnsmal/pages/index.html",
        u"message": u"Can't find variable: doSomething",
        u"project": 0,
        u"platform": u"javascript",
        u"sentry.interfaces.Http": {
            u"url": u"file:///Users/lonnen/repos/hrafnsmal/pages/index.html",
            u"headers": {
                u"User-Agent": u"Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/534.34 (KHTML, like Gecko) PhantomJS/1.9.0 Safari/534.34"
            }
        },
        u"logger": u"javascript",
        u"sentry.interfaces.Stacktrace": {
            u"frames": [
                {
                    u"function": u"?",
                    u"in_app": True,
                    u"lineno": 3,
                    u"colno": None,
                    u"filename": u"file:///Users/lonnen/repos/hrafnsmal/pages/hrafnsmal.js"
                }
            ]
        }
    }
}


class TestProcessorApp(unittest.TestCase):

    def get_standard_config(self):
        config = DotDict()

        config.logger = mock.MagicMock()

        config.throttler = mock.MagicMock()

        config.collector = DotDict()
        config.collector.collector_class = BixieCollector

        config.crash_storage = mock.MagicMock()

        return config

    def test_setup(self):
        config = self.get_standard_config()
        c = BixieCollector(config)
        self.assertEqual(c.config, config)
        self.assertEqual(c.logger, config.logger)
        self.assertEqual(c.throttler, config.throttler)
        self.assertEqual(c.crash_storage, config.crash_storage)

    def test_GET(self):
        config = self.get_standard_config()
        c = BixieCollector(config)
        web_input = {'sentry_client': u'raven-js/1.0.7', 'sentry_version': u'2.0', 'sentry_data': u'{"project":0,"logger":"javascript","platform":"javascript","sentry.interfaces.Http":{"url":"file:///Users/lonnen/repos/hrafnsmal/pages/index.html","headers":{"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/534.34 (KHTML, like Gecko) PhantomJS/1.9.0 Safari/534.34"}},"sentry.interfaces.Exception":{"type":"ReferenceError","value":"Can\'t find variable: doSomething"},"sentry.interfaces.Stacktrace":{"frames":[{"filename":"file:///Users/lonnen/repos/hrafnsmal/pages/hrafnsmal.js","lineno":3,"colno":null,"function":"?","in_app":true}]},"culprit":"file:///Users/lonnen/repos/hrafnsmal/pages/index.html","message":"Can\'t find variable: doSomething"}', 'sentry_key': u'public'}
        mock_web_str = 'socorro.collector.wsgi_bixie_collector.web.input'
        with mock.patch(mock_web_str) as mock_web:
            mock_web.return_value = web_input
            mock_utc_str = 'socorro.collector.wsgi_bixie_collector.utc_now'
            with mock.patch(mock_utc_str) as mocked_utc_now:
                mocked_utc_now.return_value = datetime(
                    2013, 5, 4, 15, 10
                )
                mock_createNewOoid_str = 'socorro.collector.wsgi_bixie_collector.createNewOoid'
                with mock.patch(mock_createNewOoid_str) as mocked_createNewOoid:
                    mocked_createNewOoid.return_value = \
                        "c796b8db-f5b4-40b1-8849-bb7682130504"

                    result = c.GET("BASE_URI", "PROJECT_ID")
                    config.crash_storage.save_raw_crash.assert_called_once_with(
                        expected_raw_crash,
                        {},
                        "c796b8db-f5b4-40b1-8849-bb7682130504"
                    )



