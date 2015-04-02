# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import hashlib

import mock
from nose.tools import eq_, ok_
from datetime import datetime

from configman.dotdict import DotDict

from socorro.collector.wsgi_breakpad_collector import BreakpadCollector
from socorro.collector.throttler import ACCEPT, IGNORE, DEFER
from socorro.unittest.testbase import TestCase


class ObjectWithValue(object):
    def __init__(self, v):
        self.value = v


class TestCollectorApp(TestCase):

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
        config.collector.checksum_method = hashlib.md5
        config.collector.reject_crash_on_rahukaalam = False

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

    @mock.patch('socorro.collector.wsgi_breakpad_collector.time')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web')
    def test_POST(self, mocked_web, mocked_webapi, mocked_utc_now, mocked_time):
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
        erc.dump_checksums = {
            'dump': '2036fd064f93a0d086cf236c5f0fd8d4',
            'aux_dump': 'aa2e5bf71df8a4730446b2551d29cb3a',
        }
        erc = dict(erc)

        mocked_web.input.return_value = form
        mocked_webapi.rawinput.return_value = rawform
        mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
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

    @mock.patch('socorro.collector.wsgi_breakpad_collector.time')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web')
    def test_POST_reject_browser_with_hangid(
        self,
        mocked_web,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
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

        mocked_webapi.rawinput.return_value = rawform
        mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
        mocked_time.time.return_value = 3.0
        c.throttler.throttle.return_value = (IGNORE, None)
        r = c.POST()
        eq_(r, "Unsupported=1\n")
        ok_(not
            c.crash_storage.save_raw_crash.call_count
        )

    @mock.patch('socorro.collector.wsgi_breakpad_collector.time')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web')
    def test_POST_with_existing_crash_id(
        self,
        mocked_web,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
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
        erc.dump_checksums = {
            'dump': '2036fd064f93a0d086cf236c5f0fd8d4',
            'aux_dump': 'aa2e5bf71df8a4730446b2551d29cb3a',
        }
        erc = dict(erc)

        mocked_web.input.return_value = form
        mocked_webapi.rawinput.return_value = rawform
        mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
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

    @mock.patch('socorro.collector.wsgi_breakpad_collector.time')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web')
    def test_POST_with_existing_crash_id_and_use_it(
        self,
        mocked_web,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
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
        erc.dump_checksums = {
            'dump': '2036fd064f93a0d086cf236c5f0fd8d4',
            'aux_dump': 'aa2e5bf71df8a4730446b2551d29cb3a',
        }
        erc = dict(erc)

        mocked_web.input.return_value = form
        mocked_webapi.rawinput.return_value = rawform
        mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
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

    @mock.patch('socorro.collector.wsgi_breakpad_collector.time')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web')
    def test_POST_with_existing_legacy_processing(
        self,
        mocked_web,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
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
        erc.dump_checksums = {
            'dump': '2036fd064f93a0d086cf236c5f0fd8d4',
            'aux_dump': 'aa2e5bf71df8a4730446b2551d29cb3a',
        }
        erc = dict(erc)

        mocked_web.input.return_value = form
        mocked_webapi.rawinput.return_value = rawform
        mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
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

    @mock.patch('socorro.collector.wsgi_breakpad_collector.time')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.web')
    def test_POST_with_existing_legacy_processing_and_use_it(
        self,
        mocked_web,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
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
        erc.dump_checksums = {
            'dump': '2036fd064f93a0d086cf236c5f0fd8d4',
            'aux_dump': 'aa2e5bf71df8a4730446b2551d29cb3a',
        }
        erc = dict(erc)

        mocked_web.input.return_value = form
        mocked_webapi.rawinput.return_value = rawform
        mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
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
