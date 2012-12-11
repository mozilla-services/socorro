# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock
from contextlib import nested

from datetime import datetime

from configman.dotdict import DotDict

from socorro.collector.wsgicollector import Collector
from socorro.collector.throttler import ACCEPT, IGNORE


class ObjectWithValue(object):
    def __init__(self, v):
        self.value = v


class TestProcessorApp(unittest.TestCase):

    def get_standard_config(self):
        config = DotDict()

        config.logger = mock.MagicMock()

        config.legacyThrottler = mock.MagicMock()

        config.dumpIDPrefix = 'bp-'
        config.dumpField = 'dump'

        config.crashStoragePool = mock.MagicMock()
        config.crashStoragePool.crashStorage = mock.MagicMock()
        self.crash_storage = mock.MagicMock()
        config.crashStoragePool.crashStorage.return_value = self.crash_storage

        return config

    def test_setup(self):
        config = self.get_standard_config()
        c = Collector(config)
        self.assertEqual(c.context, config)
        self.assertEqual(c.logger, config.logger)
        self.assertEqual(c.legacy_throttler, config.legacyThrottler)
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

        rc, dmp = c._make_raw_crash_and_dumps(form)
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
        rawform.aux_dump = DotDict({'value': 'aux_dump contents', 'file':
                                    'silliness'})
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

        with nested(mock.patch('socorro.collector.wsgicollector.web'),
                    mock.patch('socorro.collector.wsgicollector.web.webapi'),
                    mock.patch('socorro.collector.wsgicollector.utc_now'),
                    mock.patch('socorro.collector.wsgicollector.time')) \
            as (mocked_web, mocked_webapi, mocked_utc_now, mocked_time):
            mocked_web.input.return_value = form
            mocked_webapi.rawinput.return_value = rawform
            mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
            mocked_time.time.return_value = 3.0
            c.legacy_throttler.throttle.return_value = ACCEPT
            r = c.POST()
            self.assertTrue(r.startswith('CrashID=bp-'))
            self.assertTrue(r.endswith('120504\n'))
            self.crash_storage.save_raw.assert_called_with(
              r[11:-1],
              erc,
              {'dump':'fake dump', 'aux_dump':'aux_dump contents'},
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

        with nested(mock.patch('socorro.collector.wsgicollector.web'),
                    mock.patch('socorro.collector.wsgicollector.web.webapi'),
                    mock.patch('socorro.collector.wsgicollector.utc_now'),
                    mock.patch('socorro.collector.wsgicollector.time')) \
            as (mocked_web, mocked_webapi, mocked_utc_now, mocked_time):

            mocked_web.input.return_value = form
            mocked_webapi.rawinput.return_value = rawform
            mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
            mocked_time.time.return_value = 3.0
            c.legacy_throttler.throttle.return_value = IGNORE
            r = c.POST()
            self.assertEqual(r, "Unsupported=1\n")
            self.assertFalse(self.crash_storage.save_raw.call_count)
