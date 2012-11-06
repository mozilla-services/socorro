# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock

from datetime import datetime

from configman.dotdict import DotDict

from socorro.collector.wsgi_collector import Collector
from socorro.collector.throttler import ACCEPT, IGNORE


class ObjectWithValue(object):
    def __init__(self, v):
        self.value = v


class TestProcessorApp(unittest.TestCase):

    def get_standard_config(self):
        config = DotDict()

        config.logger = mock.MagicMock()

        config.throttler = mock.MagicMock()

        config.collector = DotDict()
        config.collector.dump_id_prefix = 'bp-'
        config.collector.dump_field = 'dump'

        config.crash_storage = mock.MagicMock()

        return config

    def test_setup(self):
        config = self.get_standard_config()
        c = Collector(config)
        self.assertEqual(c.config, config)
        self.assertEqual(c.logger, config.logger)
        self.assertEqual(c.throttler, config.throttler)
        self.assertEqual(c.crash_storage, config.crash_storage)
        self.assertEqual(c.dump_id_prefix, 'bp-')
        self.assertEqual(c.dump_field, 'dump')

    def test_make_raw_crash(self):
        config = self.get_standard_config()
        c = Collector(config)
        form = DotDict()
        form.ProductName = 'FireFloozy'
        form.Version = '99'
        form.dump = 'fake dump'
        form.some_field = '23'
        form.some_other_field = ObjectWithValue('XYZ')

        rc = c.make_raw_crash(form)
        self.assertEqual(rc.ProductName, 'FireFloozy')
        self.assertEqual(rc.Version, '99')
        self.assertEqual(rc.some_field, '23')
        self.assertEqual(rc.some_other_field, 'XYZ')

    def test_POST(self):
        config = self.get_standard_config()
        c = Collector(config)
        rawform = DotDict()
        rawform.ProductName = 'FireFloozy'
        rawform.Version = '99'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.some_field = '23'
        rawform.some_other_field = ObjectWithValue('XYZ')

        form = DotDict(rawform)
        form.dump = rawform.dump.value

        erc = DotDict()
        erc.ProductName = 'FireFloozy'
        erc.Version = '99'
        erc.some_field = '23'
        erc.some_other_field = 'XYZ'
        erc.legacy_processing = ACCEPT
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc = dict(erc)

        with mock.patch('socorro.collector.wsgi_collector.web') as mocked_web:
            mocked_web.input.return_value = form
            with mock.patch('socorro.collector.wsgi_collector.web.webapi') \
                    as mocked_webapi:
                mocked_webapi.rawinput.return_value = rawform
                with mock.patch('socorro.collector.wsgi_collector.utc_now') \
                        as mocked_utc_now:
                    mocked_utc_now.return_value = datetime(
                        2012, 5, 4, 15, 10
                        )
                    with mock.patch('socorro.collector.wsgi_collector.time') \
                            as mocked_time:
                        mocked_time.time.return_value = 3.0
                        c.throttler.throttle.return_value = ACCEPT
                        r = c.POST()
                        self.assertTrue(r.startswith('CrashID=bp-'))
                        self.assertTrue(r.endswith('120504\n'))
                        c.crash_storage.save_raw_crash.assert_called_with(
                            erc,
                            'fake dump',
                            r[11:-1]
                            )

    def test_POST_reject_browser_with_hangid(self):
        config = self.get_standard_config()
        c = Collector(config)
        rawform = DotDict()
        rawform.ProductName = 'FireFloozy'
        rawform.Version = '99'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.some_field = '23'
        rawform.some_other_field = ObjectWithValue('XYZ')
        rawform.HangID = 'xyz'
        rawform.ProcessType = 'browser'

        form = DotDict(rawform)
        form.dump = rawform.dump.value

        erc = DotDict()
        erc.ProductName = 'FireFloozy'
        erc.Version = '99'
        erc.some_field = '23'
        erc.some_other_field = 'XYZ'
        erc.legacy_processing = ACCEPT
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc = dict(erc)

        with mock.patch('socorro.collector.wsgi_collector.web') as mocked_web:
            mocked_web.input.return_value = form
            with mock.patch('socorro.collector.wsgi_collector.web.webapi') \
                    as mocked_webapi:
                mocked_webapi.rawinput.return_value = rawform
                with mock.patch('socorro.collector.wsgi_collector.utc_now') \
                        as mocked_utc_now:
                    mocked_utc_now.return_value = datetime(
                        2012, 5, 4, 15, 10
                        )
                    with mock.patch('socorro.collector.wsgi_collector.time') \
                            as mocked_time:
                        mocked_time.time.return_value = 3.0
                        c.throttler.throttle.return_value = IGNORE
                        r = c.POST()
                        self.assertEqual(r, "Unsupported=1\n")
                        self.assertFalse(
                          c.crash_storage.save_raw_crash.call_count
                        )
