# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest
import mock
from nose.tools import eq_, ok_
from datetime import datetime

from configman.dotdict import DotDict

from socorro.collector.wsgi_breakpad_collector import BreakpadCollector
from socorro.collector.throttler import ACCEPT, IGNORE, DEFER


class ObjectWithValue(object):
    def __init__(self, v):
        self.value = v


class TestCollectorApp(unittest.TestCase):

    def get_standard_config(self):
        config = DotDict()

        config.logger = mock.MagicMock()

        config.throttler = mock.MagicMock()

        config.collector = DotDict()
        config.collector.collector_class = BreakpadCollector
        config.collector.dump_id_prefix = 'bp-'
        config.collector.dump_field = 'dump'
        config.collector.accept_submitted_crash_id = False
        config.collector.accept_submitted_legacy_processing = False

        config.crash_storage = mock.MagicMock()

        return config

    def test_setup(self):
        config = self.get_standard_config()
        c = BreakpadCollector(config)
        eq_(c.config, config)
        eq_(c.logger, config.logger)
        eq_(c.throttler, config.throttler)
        eq_(c.crash_storage, config.crash_storage)
        eq_(c.dump_id_prefix, 'bp-')
        eq_(c.dump_field, 'dump')

    def test_make_raw_crash(self):
        config = self.get_standard_config()
        c = BreakpadCollector(config)
        form = DotDict()
        form.ProductName = 'FireSquid'
        form.Version = '99'
        form.dump = 'fake dump'
        form.some_field = '23'
        form.some_other_field = ObjectWithValue('XYZ')

        rc, dmp = c._make_raw_crash_and_dumps(form)
        eq_(rc.ProductName, 'FireSquid')
        eq_(rc.Version, '99')
        eq_(rc.some_field, '23')
        eq_(rc.some_other_field, 'XYZ')

    def test_POST(self):
        config = self.get_standard_config()
        c = BreakpadCollector(config)
        rawform = DotDict()
        rawform.ProductName = 'FireSquid'
        rawform.Version = '99'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.aux_dump = DotDict({'value': 'aux_dump contents', 'file': 'silliness'})
        rawform.some_field = '23'
        rawform.some_other_field = ObjectWithValue('XYZ')

        form = DotDict(rawform)
        form.dump = rawform.dump.value

        erc = DotDict()
        erc.ProductName = 'FireSquid'
        erc.Version = '99'
        erc.some_field = '23'
        erc.some_other_field = 'XYZ'
        erc.legacy_processing = ACCEPT
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc.throttle_rate = 100
        erc = dict(erc)

        with mock.patch('socorro.collector.wsgi_breakpad_collector.web') as mocked_web:
            mocked_web.input.return_value = form
            with mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi') \
                    as mocked_webapi:
                mocked_webapi.rawinput.return_value = rawform
                with mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now') \
                        as mocked_utc_now:
                    mocked_utc_now.return_value = datetime(
                        2012, 5, 4, 15, 10
                        )
                    with mock.patch('socorro.collector.wsgi_breakpad_collector.time') \
                            as mocked_time:
                        mocked_time.time.return_value = 3.0
                        c.throttler.throttle.return_value = (ACCEPT, 100)
                        r = c.POST()
                        ok_(r.startswith('CrashID=bp-'))
                        ok_(r.endswith('120504\n'))
                        erc['uuid'] = r[11:-1]
                        c.crash_storage.save_raw_crash.assert_called_with(
                          erc,
                          {'dump':'fake dump', 'aux_dump':'aux_dump contents'},
                          r[11:-1]
                        )

    def test_POST_reject_browser_with_hangid(self):
        config = self.get_standard_config()
        c = BreakpadCollector(config)
        rawform = DotDict()
        rawform.ProductName = 'FireSquid'
        rawform.Version = '99'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.some_field = '23'
        rawform.some_other_field = ObjectWithValue('XYZ')
        rawform.HangID = 'xyz'
        rawform.ProcessType = 'browser'

        form = DotDict(rawform)
        form.dump = rawform.dump.value

        erc = DotDict()
        erc.ProductName = 'FireSquid'
        erc.Version = '99'
        erc.some_field = '23'
        erc.some_other_field = 'XYZ'
        erc.legacy_processing = ACCEPT
        erc.throttle_rate = None
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc = dict(erc)

        with mock.patch('socorro.collector.wsgi_breakpad_collector.web') as mocked_web:
            mocked_web.input.return_value = form
            with mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi') \
                    as mocked_webapi:
                mocked_webapi.rawinput.return_value = rawform
                with mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now') \
                        as mocked_utc_now:
                    mocked_utc_now.return_value = datetime(
                        2012, 5, 4, 15, 10
                        )
                    with mock.patch('socorro.collector.wsgi_breakpad_collector.time') \
                            as mocked_time:
                        mocked_time.time.return_value = 3.0
                        c.throttler.throttle.return_value = (IGNORE, None)
                        r = c.POST()
                        eq_(r, "Unsupported=1\n")
                        ok_(not
                          c.crash_storage.save_raw_crash.call_count
                        )

    def test_POST_with_existing_crash_id(self):
        config = self.get_standard_config()
        c = BreakpadCollector(config)
        rawform = DotDict()
        rawform.ProductName = 'FireSquid'
        rawform.Version = '99'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.aux_dump = DotDict({'value': 'aux_dump contents', 'file': 'silliness'})
        rawform.some_field = '23'
        rawform.some_other_field = ObjectWithValue('XYZ')
        rawform.uuid = '332d798f-3c42-47a5-843f-a0f892140107'

        form = DotDict(rawform)
        form.dump = rawform.dump.value

        erc = DotDict()
        erc.ProductName = 'FireSquid'
        erc.Version = '99'
        erc.some_field = '23'
        erc.some_other_field = 'XYZ'
        erc.legacy_processing = ACCEPT
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc.throttle_rate = 100
        erc = dict(erc)

        with mock.patch('socorro.collector.wsgi_breakpad_collector.web') as mocked_web:
            mocked_web.input.return_value = form
            with mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi') \
                    as mocked_webapi:
                mocked_webapi.rawinput.return_value = rawform
                with mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now') \
                        as mocked_utc_now:
                    mocked_utc_now.return_value = datetime(
                        2012, 5, 4, 15, 10
                        )
                    with mock.patch('socorro.collector.wsgi_breakpad_collector.time') \
                            as mocked_time:
                        mocked_time.time.return_value = 3.0
                        c.throttler.throttle.return_value = (ACCEPT, 100)
                        r = c.POST()
                        ok_(r.startswith('CrashID=bp-'))
                        ok_(r.endswith('120504\n'))
                        erc['uuid'] = r[11:-1]
                        c.crash_storage.save_raw_crash.assert_called_with(
                          erc,
                          {'dump':'fake dump', 'aux_dump':'aux_dump contents'},
                          r[11:-1]
                        )

    def test_POST_with_existing_crash_id_and_use_it(self):
        config = self.get_standard_config()
        config.collector.accept_submitted_crash_id = True
        c = BreakpadCollector(config)

        rawform = DotDict()
        rawform.ProductName = 'FireSquid'
        rawform.Version = '99'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.aux_dump = DotDict({'value': 'aux_dump contents', 'file': 'silliness'})
        rawform.some_field = '23'
        rawform.some_other_field = ObjectWithValue('XYZ')
        rawform.uuid = '332d798f-3c42-47a5-843f-a0f892140107'
        rawform.legacy_processing = str(DEFER)
        rawform.throttle_rate = 100

        form = DotDict(rawform)
        form.dump = rawform.dump.value

        erc = DotDict()
        erc.ProductName = 'FireSquid'
        erc.Version = '99'
        erc.some_field = '23'
        erc.some_other_field = 'XYZ'
        erc.legacy_processing = DEFER
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc.throttle_rate = 100
        erc.uuid = '332d798f-3c42-47a5-843f-a0f892140107'
        erc = dict(erc)

        with mock.patch('socorro.collector.wsgi_breakpad_collector.web') as mocked_web:
            mocked_web.input.return_value = form
            with mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi') \
                    as mocked_webapi:
                mocked_webapi.rawinput.return_value = rawform
                with mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now') \
                        as mocked_utc_now:
                    mocked_utc_now.return_value = datetime(
                        2012, 5, 4, 15, 10
                        )
                    with mock.patch('socorro.collector.wsgi_breakpad_collector.time') \
                            as mocked_time:
                        mocked_time.time.return_value = 3.0
                        c.throttler.throttle.return_value = (DEFER, 100)
                        r = c.POST()
                        ok_(r.startswith('CrashID=bp-'))
                        ok_(r.endswith('140107\n'))
                        c.crash_storage.save_raw_crash.assert_called_with(
                          erc,
                          {'dump':'fake dump', 'aux_dump':'aux_dump contents'},
                          r[11:-1]
                        )

    def test_POST_with_existing_legacy_processing(self):
        config = self.get_standard_config()
        c = BreakpadCollector(config)
        rawform = DotDict()
        rawform.ProductName = 'FireSquid'
        rawform.Version = '99'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.aux_dump = DotDict({'value': 'aux_dump contents', 'file': 'silliness'})
        rawform.some_field = '23'
        rawform.some_other_field = ObjectWithValue('XYZ')
        rawform.uuid = '332d798f-3c42-47a5-843f-a0f892140107'
        rawform.legacy_processing = u'1'

        form = DotDict(rawform)
        form.dump = rawform.dump.value

        erc = DotDict()
        erc.ProductName = 'FireSquid'
        erc.Version = '99'
        erc.some_field = '23'
        erc.some_other_field = 'XYZ'
        erc.legacy_processing = ACCEPT
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc.throttle_rate = 100
        erc = dict(erc)

        with mock.patch('socorro.collector.wsgi_breakpad_collector.web') as mocked_web:
            mocked_web.input.return_value = form
            with mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi') \
                    as mocked_webapi:
                mocked_webapi.rawinput.return_value = rawform
                with mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now') \
                        as mocked_utc_now:
                    mocked_utc_now.return_value = datetime(
                        2012, 5, 4, 15, 10
                        )
                    with mock.patch('socorro.collector.wsgi_breakpad_collector.time') \
                            as mocked_time:
                        mocked_time.time.return_value = 3.0
                        c.throttler.throttle.return_value = (ACCEPT, 100)
                        r = c.POST()
                        ok_(r.startswith('CrashID=bp-'))
                        ok_(r.endswith('120504\n'))
                        erc['uuid'] = r[11:-1]
                        c.crash_storage.save_raw_crash.assert_called_with(
                          erc,
                          {'dump':'fake dump', 'aux_dump':'aux_dump contents'},
                          r[11:-1]
                        )

    def test_POST_with_existing_legacy_processing_and_use_it(self):
        config = self.get_standard_config()
        config.collector.accept_submitted_crash_id = True
        config.collector.accept_submitted_legacy_processing = True
        c = BreakpadCollector(config)

        rawform = DotDict()
        rawform.ProductName = 'FireSquid'
        rawform.Version = '99'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.aux_dump = DotDict({'value': 'aux_dump contents', 'file': 'silliness'})
        rawform.some_field = '23'
        rawform.some_other_field = ObjectWithValue('XYZ')
        rawform.uuid = '332d798f-3c42-47a5-843f-a0f892140107'
        rawform.legacy_processing = str(DEFER)
        rawform.throttle_rate = 100

        form = DotDict(rawform)
        form.dump = rawform.dump.value

        erc = DotDict()
        erc.ProductName = 'FireSquid'
        erc.Version = '99'
        erc.some_field = '23'
        erc.some_other_field = 'XYZ'
        erc.legacy_processing = DEFER
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc.throttle_rate = 100
        erc.uuid = '332d798f-3c42-47a5-843f-a0f892140107'
        erc = dict(erc)

        with mock.patch('socorro.collector.wsgi_breakpad_collector.web') as mocked_web:
            mocked_web.input.return_value = form
            with mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi') \
                    as mocked_webapi:
                mocked_webapi.rawinput.return_value = rawform
                with mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now') \
                        as mocked_utc_now:
                    mocked_utc_now.return_value = datetime(
                        2012, 5, 4, 15, 10
                        )
                    with mock.patch('socorro.collector.wsgi_breakpad_collector.time') \
                            as mocked_time:
                        mocked_time.time.return_value = 3.0
                        c.throttler.throttle.return_value = (DEFER, 100)
                        r = c.POST()
                        ok_(r.startswith('CrashID=bp-'))
                        ok_(r.endswith('140107\n'))
                        c.crash_storage.save_raw_crash.assert_called_with(
                          erc,
                          {'dump':'fake dump', 'aux_dump':'aux_dump contents'},
                          r[11:-1]
                        )
