# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import hashlib
import StringIO
import gzip

import mock
from nose.tools import eq_, ok_
from datetime import datetime
from contextlib import closing

from configman.dotdict import DotDict

from socorro.collector.wsgi_breakpad_collector import (
    BreakpadCollector,
    BreakpadCollector2015
)
from socorro.collector.throttler import ACCEPT, IGNORE, DEFER
from socorro.unittest.testbase import TestCase


class ObjectWithValue(object):
    def __init__(self, v):
        self.value = v


class TestWSGIBreakpadCollector(TestCase):

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
        form = DotDict()
        form.ProductName = 'FireSquid'
        form.Version = '99'
        form.dump = 'fake dump'
        form.some_field = '\x0023'
        form.some_other_field = ObjectWithValue('XYZ')

        class BreakpadCollectorWithMyForm(config.collector.collector_class):
            def _form_as_mapping(self):
                return form

        c = BreakpadCollectorWithMyForm(config)

        rc, dmp = c._get_raw_crash_from_form()
        eq_(rc.ProductName, 'FireSquid')
        eq_(rc.Version, '99')
        eq_(rc.some_field, '23')
        eq_(rc.some_other_field, 'XYZ')

    @mock.patch('socorro.collector.wsgi_breakpad_collector.time')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now')
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
    def test_POST(self, mocked_web, mocked_webapi, mocked_utc_now, mocked_time):
        config = self.get_standard_config()
        c = BreakpadCollector(config)
        rawform = DotDict()
        rawform.ProductName = '\x00FireSquid'
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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
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
        rawform[u'\u0000ProductName'] = 'FireSquid'
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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
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
        rawform.uuid = '332d798f-3cx\x0042-47a5-843f-a0f892140107'

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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
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
        rawform.dump_checksums = "this is poised to overwrite and cause trouble"

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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
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
        rawform.Version = '99\x00'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.aux_dump = DotDict({'value': 'aux_dump contents', 'file': 'silliness'})
        rawform[u'some_field\u0000'] = '23'
        rawform[u'some_\u0000other_field'] = ObjectWithValue('XYZ')
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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web.ctx')
    def test_POST_with_gzip(
        self,
        mocked_web_ctx,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
        config = self.get_standard_config()
        c = BreakpadCollector(config)
        form = """
--socorro1234567
Content-Disposition: form-data; name="ProductName"

FireSquid
--socorro1234567
Content-Disposition: form-data; name="Version"

99
--socorro1234567
Content-Disposition: form-data; name="some_field"

23
--socorro1234567
Content-Disposition: form-data; name="some_other_field"

XYZ
--socorro1234567
Content-Disposition: form-data; name="dump"; filename="dump"
Content-Type: application/octet-stream

fake dump
--socorro1234567
Content-Disposition: form-data; name="aux_dump"; filename="aux_dump"
Content-Type: application/octet-stream

aux_dump contents
"""

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
        erc.type_tag = 'bp'
        erc = dict(erc)

        with closing(StringIO.StringIO()) as s:
            g = gzip.GzipFile(fileobj=s, mode='w')
            g.write(form)
            g.close()
            gzipped_form = s.getvalue()

        mocked_webapi.data.return_value = gzipped_form
        mocked_web_ctx.configure_mock(
            env={
                'HTTP_CONTENT_ENCODING': 'gzip',
                'CONTENT_ENCODING': 'gzip',
                'CONTENT_TYPE':
                    'multipart/form-data; boundary="socorro1234567"',
                'REQUEST_METHOD': 'POST'
            }
        )

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

    def test_no_x00_character(self):
        config = self.get_standard_config()
        c = BreakpadCollector(config)

        eq_(c._no_x00_character('\x00hello'), 'hello')
        eq_(c._no_x00_character(u'\u0000bye'), 'bye')
        eq_(c._no_x00_character(u'\u0000\x00bye'), 'bye')


class TestWSGIBreakpadCollector2015(TestCase):

    def get_standard_config(self):
        config = DotDict()

        config.logger = mock.MagicMock()

        config.throttler = mock.MagicMock()

        config.collector_class = BreakpadCollector2015
        config.dump_id_prefix = 'bp-'
        config.dump_field = 'dump'
        config.accept_submitted_crash_id = False
        config.accept_submitted_legacy_processing = False
        config.checksum_method = hashlib.md5

        config.storage = DotDict()
        config.storage.crashstorage_class = mock.MagicMock()

        config.throttler = DotDict()
        config.throttler.throttler_class = mock.MagicMock()

        return config

    def test_setup(self):
        config = self.get_standard_config()
        c = BreakpadCollector2015(config)
        eq_(c.config, config)
        eq_(c.logger, config.logger)
        eq_(c.throttler, config.throttler.throttler_class.return_value)
        eq_(c.crash_storage, config.storage.crashstorage_class.return_value)
        eq_(c.dump_id_prefix, 'bp-')
        eq_(c.dump_field, 'dump')

    def test_make_raw_crash(self):
        config = self.get_standard_config()
        form = DotDict()
        form.ProductName = 'FireSquid'
        form.Version = '99'
        form.dump = 'fake dump'
        form.some_field = '\x0023'
        form.some_other_field = ObjectWithValue('XYZ')

        class BreakpadCollectorWithMyForm(config.collector_class):
            def _form_as_mapping(self):
                return form

        c = BreakpadCollectorWithMyForm(config)

        rc, dmp = c._get_raw_crash_from_form()
        eq_(rc.ProductName, 'FireSquid')
        eq_(rc.Version, '99')
        eq_(rc.some_field, '23')
        eq_(rc.some_other_field, 'XYZ')

    @mock.patch('socorro.collector.wsgi_breakpad_collector.time')
    @mock.patch('socorro.collector.wsgi_breakpad_collector.utc_now')
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
    def test_POST(self, mocked_web, mocked_webapi, mocked_utc_now, mocked_time):
        config = self.get_standard_config()
        c = BreakpadCollector2015(config)
        rawform = DotDict()
        rawform.ProductName = '\x00FireSquid'
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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
    def test_POST_reject_browser_with_hangid(
        self,
        mocked_web,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
        config = self.get_standard_config()
        c = BreakpadCollector2015(config)
        rawform = DotDict()
        rawform[u'\u0000ProductName'] = 'FireSquid'
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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
    def test_POST_with_existing_crash_id(
        self,
        mocked_web,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
        config = self.get_standard_config()
        c = BreakpadCollector2015(config)
        rawform = DotDict()
        rawform.ProductName = 'FireSquid'
        rawform.Version = '99'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.aux_dump = DotDict({'value': 'aux_dump contents', 'file': 'silliness'})
        rawform.some_field = '23'
        rawform.some_other_field = ObjectWithValue('XYZ')
        rawform.uuid = '332d798f-3cx\x0042-47a5-843f-a0f892140107'

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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
    def test_POST_with_existing_crash_id_and_use_it(
        self,
        mocked_web,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
        config = self.get_standard_config()
        config.accept_submitted_crash_id = True
        c = BreakpadCollector2015(config)

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
        rawform.dump_checksums = "this is poised to overwrite and cause trouble"

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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
    def test_POST_with_existing_legacy_processing(
        self,
        mocked_web,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
        config = self.get_standard_config()
        c = BreakpadCollector2015(config)
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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
    def test_POST_with_existing_legacy_processing_and_use_it(
        self,
        mocked_web,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
        config = self.get_standard_config()
        config.accept_submitted_crash_id = True
        config.accept_submitted_legacy_processing = True
        c = BreakpadCollector2015(config)

        rawform = DotDict()
        rawform.ProductName = 'FireSquid'
        rawform.Version = '99\x00'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.aux_dump = DotDict({'value': 'aux_dump contents', 'file': 'silliness'})
        rawform[u'some_field\u0000'] = '23'
        rawform[u'some_\u0000other_field'] = ObjectWithValue('XYZ')
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
        erc.type_tag = 'bp'
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
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web.ctx')
    def test_POST_with_gzip(
        self,
        mocked_web_ctx,
        mocked_webapi,
        mocked_utc_now,
        mocked_time
    ):
        config = self.get_standard_config()
        c = BreakpadCollector2015(config)
        form = """
--socorro1234567
Content-Disposition: form-data; name="ProductName"

FireSquid
--socorro1234567
Content-Disposition: form-data; name="Version"

99
--socorro1234567
Content-Disposition: form-data; name="some_field"

23
--socorro1234567
Content-Disposition: form-data; name="some_other_field"

XYZ
--socorro1234567
Content-Disposition: form-data; name="dump"; filename="dump"
Content-Type: application/octet-stream

fake dump
--socorro1234567
Content-Disposition: form-data; name="aux_dump"; filename="aux_dump"
Content-Type: application/octet-stream

aux_dump contents
"""

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
        erc.type_tag = 'bp'
        erc = dict(erc)

        with closing(StringIO.StringIO()) as s:
            g = gzip.GzipFile(fileobj=s, mode='w')
            g.write(form)
            g.close()
            gzipped_form = s.getvalue()

        mocked_webapi.data.return_value = gzipped_form
        mocked_web_ctx.configure_mock(
            env={
                'HTTP_CONTENT_ENCODING': 'gzip',
                'CONTENT_ENCODING': 'gzip',
                'CONTENT_TYPE':
                    'multipart/form-data; boundary="socorro1234567"',
                'REQUEST_METHOD': 'POST'
            }
        )

        mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
        mocked_time.time.return_value = 3.0
        c.throttler.throttle.return_value = (ACCEPT, 100)

        # the call to be tested
        r = c.POST()

        # this is what should have happened
        ok_(r.startswith('CrashID=bp-'))
        ok_(r.endswith('120504\n'))
        erc['uuid'] = r[11:-1]
        c.crash_storage.save_raw_crash.assert_called_with(
            erc,
            {'dump':'fake dump', 'aux_dump':'aux_dump contents'},
            r[11:-1]
        )

    def test_no_x00_character(self):
        config = self.get_standard_config()
        c = BreakpadCollector2015(config)

        eq_(c._no_x00_character('\x00hello'), 'hello')
        eq_(c._no_x00_character(u'\u0000bye'), 'bye')
        eq_(c._no_x00_character(u'\u0000\x00bye'), 'bye')
