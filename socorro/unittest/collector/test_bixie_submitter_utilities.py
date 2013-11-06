# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock

from datetime import datetime

from configman.dotdict import DotDict

from socorro.collector.bixie_submitter_utilities import BixieGETDestination
from socorro.external.crashstorage_base import Redactor

raw_crash = {
    "submitted_timestamp": "2013-05-04T15:10:00",
    "base_uri": "this_is_the_base",
    "project_id": "this_is_the_project_id",
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

url_encoded_raw_crash = "http://127.0.0.1:8882/this_is_the_base/api/this_is_the_project_id/store/?sentry_client=raven-js%2F1.0.7&sentry_version=2.0&sentry_data=%7B%22project%22%3A+0%2C+%22platform%22%3A+%22javascript%22%2C+%22sentry.interfaces.Exception%22%3A+%7B%22type%22%3A+%22ReferenceError%22%2C+%22value%22%3A+%22Can%27t+find+variable%3A+doSomething%22%7D%2C+%22culprit%22%3A+%22file%3A%2F%2F%2FUsers%2Flonnen%2Frepos%2Fhrafnsmal%2Fpages%2Findex.html%22%2C+%22message%22%3A+%22Can%27t+find+variable%3A+doSomething%22%2C+%22sentry.interfaces.Stacktrace%22%3A+%7B%22frames%22%3A+%5B%7B%22function%22%3A+%22%3F%22%2C+%22filename%22%3A+%22file%3A%2F%2F%2FUsers%2Flonnen%2Frepos%2Fhrafnsmal%2Fpages%2Fhrafnsmal.js%22%2C+%22lineno%22%3A+3%2C+%22colno%22%3A+null%2C+%22in_app%22%3A+true%7D%5D%7D%2C+%22logger%22%3A+%22javascript%22%2C+%22sentry.interfaces.Http%22%3A+%7B%22url%22%3A+%22file%3A%2F%2F%2FUsers%2Flonnen%2Frepos%2Fhrafnsmal%2Fpages%2Findex.html%22%2C+%22headers%22%3A+%7B%22User-Agent%22%3A+%22Mozilla%2F5.0+%28Macintosh%3B+Intel+Mac+OS+X%29+AppleWebKit%2F534.34+%28KHTML%2C+like+Gecko%29+PhantomJS%2F1.9.0+Safari%2F534.34%22%7D%7D%7D&sentry_key=public"


class TestBixieGETDestination(unittest.TestCase):

    def get_standard_config(self):
        config = DotDict()
        config.logger = mock.MagicMock()
        config.url = "http://127.0.0.1:8882/"
        config.redactor_class = Redactor
        config.forbidden_keys = Redactor.required_config.forbidden_keys.default
        config.echo_response = False
        return config

    def test_setup(self):
        config = self.get_standard_config()
        c = BixieGETDestination(config)
        self.assertEqual(c.config, config)
        self.assertEqual(c.logger, config.logger)

    def test_save_raw_crash(self):
        config = self.get_standard_config()
        b = BixieGETDestination(config)
        mock_urllib2_str = 'socorro.collector.bixie_submitter_utilities.urllib2'
        with mock.patch(mock_urllib2_str) as mock_urllib2:
            mock_response = mock.Mock()
            mock_response.read.return_value = 'ok'
            mock_urllib2.urlopen.return_value = mock_response
            b.save_raw_crash(raw_crash, {}, raw_crash['crash_id'])
            mock_urllib2.urlopen.assert_called_once_with(url_encoded_raw_crash)

    def test_save_raw_crash_missing_sentry_entries(self):
        config = self.get_standard_config()
        b = BixieGETDestination(config)
        mock_urllib2_str = 'socorro.collector.bixie_submitter_utilities.urllib2'
        with mock.patch(mock_urllib2_str) as mock_urllib2:
            mock_response = mock.Mock()
            mock_response.read.return_value = 'ok'
            mock_urllib2.urlopen.return_value = mock_response
            not_a_bixie_crash = raw_crash.copy()
            del not_a_bixie_crash['sentry_data']
            b.save_raw_crash(
                not_a_bixie_crash,
                {},
                not_a_bixie_crash['crash_id']
            )
            self.assertEqual(mock_urllib2.urlopen.call_count,0)


