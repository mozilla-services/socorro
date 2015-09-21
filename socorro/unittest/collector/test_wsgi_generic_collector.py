# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import hashlib
import StringIO
import gzip
import web

import mock
from nose.tools import eq_, ok_
from datetime import datetime
from contextlib import closing

from configman.dotdict import DotDict

from socorro.collector.wsgi_generic_collector import GenericCollector
from socorro.unittest.testbase import TestCase


class ObjectWithValue(object):
    def __init__(self, v):
        self.value = v


class TestCollectorApp(TestCase):

    def get_standard_config(self):
        config = DotDict()

        config.logger = mock.MagicMock()

        config.collector_class = GenericCollector
        config.type_tag = 'XXX-'
        config.accept_submitted_crash_id = False
        config.checksum_method = mock.Mock()
        config.checksum_method.return_value.hexdigest.return_value = 'a_hash'

        config.storage = DotDict()
        config.storage.crashstorage_class = mock.MagicMock()

        return config

    def test_setup(self):
        config = self.get_standard_config()
        c = GenericCollector(config)
        eq_(c.config, config)
        eq_(c.logger, config.logger)
        eq_(c.crash_storage, config.storage.crashstorage_class.return_value)
        eq_(c.type_tag, 'XXX-')

    def test_make_raw_crash(self):
        config = self.get_standard_config()
        form = DotDict()
        form.ProductName = 'FireSquid'
        form.Version = '99'
        form.dump = 'fake dump'
        form.some_field = '\x0023'
        form.some_other_field = ObjectWithValue('XYZ')

        class GenericCollectorWithMyForm(config.collector_class):
            def _form_as_mapping(self):
                return form

        c = GenericCollectorWithMyForm(config)

        rc, dmp = c._get_raw_crash_from_form()
        eq_(rc.ProductName, 'FireSquid')
        eq_(rc.Version, '99')
        eq_(rc.some_field, '23')
        eq_(rc.some_other_field, 'XYZ')

    @mock.patch('socorro.collector.wsgi_generic_collector.time')
    @mock.patch('socorro.collector.wsgi_generic_collector.utc_now')
    @mock.patch('socorro.collector.wsgi_generic_collector.web.webapi')
    @mock.patch('socorro.collector.wsgi_generic_collector.web')
    def test_POST(self, mocked_web, mocked_webapi, mocked_utc_now, mocked_time):
        config = self.get_standard_config()
        c = GenericCollector(config)
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
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc.type_tag = 'XXX-'
        erc.dump_checksums = {
            'dump': 'a_hash',
            'aux_dump': 'a_hash',
        }
        erc = dict(erc)

        mocked_web.input.return_value = form
        mocked_webapi.rawinput.return_value = rawform
        mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
        mocked_time.time.return_value = 3.0
        r = c.POST()
        ok_(r.startswith('CrashID=XXX-'))
        ok_(r.endswith('120504\n'))
        erc['crash_id'] = r[12:-1]
        c.crash_storage.save_raw_crash.assert_called_with(
            erc,
            {'dump':'fake dump', 'aux_dump':'aux_dump contents'},
            r[12:-1]
        )

    @mock.patch('socorro.collector.wsgi_generic_collector.time')
    @mock.patch('socorro.collector.wsgi_generic_collector.utc_now')
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
        c = GenericCollector(config)
        rawform = DotDict()
        rawform.ProductName = 'FireSquid'
        rawform.Version = '99'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.aux_dump = DotDict({'value': 'aux_dump contents', 'file': 'silliness'})
        rawform.some_field = '23'
        rawform.some_other_field = ObjectWithValue('XYZ')
        rawform.crash_id = '332d798f-3cx\x0042-47a5-843f-a0f892140107'

        form = DotDict(rawform)
        form.dump = rawform.dump.value

        erc = DotDict()
        erc.ProductName = 'FireSquid'
        erc.Version = '99'
        erc.some_field = '23'
        erc.some_other_field = 'XYZ'
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc.type_tag = 'XXX-'
        erc.dump_checksums = {
            'dump': 'a_hash',
            'aux_dump': 'a_hash',
        }
        erc = dict(erc)

        mocked_web.input.return_value = form
        mocked_webapi.rawinput.return_value = rawform
        mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
        mocked_time.time.return_value = 3.0
        r = c.POST()
        ok_(r.startswith('CrashID=XXX-'))
        ok_(r.endswith('120504\n'))
        erc['crash_id'] = r[12:-1]
        c.crash_storage.save_raw_crash.assert_called_with(
            erc,
            {'dump':'fake dump', 'aux_dump':'aux_dump contents'},
            r[12:-1]
        )

    @mock.patch('socorro.collector.wsgi_generic_collector.time')
    @mock.patch('socorro.collector.wsgi_generic_collector.utc_now')
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
        c = GenericCollector(config)

        rawform = DotDict()
        rawform.ProductName = 'FireSquid'
        rawform.Version = '99'
        rawform.dump = DotDict({'value': 'fake dump', 'file': 'faked file'})
        rawform.aux_dump = DotDict({'value': 'aux_dump contents', 'file': 'silliness'})
        rawform.some_field = '23'
        rawform.some_other_field = ObjectWithValue('XYZ')
        rawform.crash_id = '332d798f-3c42-47a5-843f-a0f892140107'

        form = DotDict(rawform)
        form.dump = rawform.dump.value

        erc = DotDict()
        erc.ProductName = 'FireSquid'
        erc.Version = '99'
        erc.some_field = '23'
        erc.some_other_field = 'XYZ'
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc.crash_id = '332d798f-3c42-47a5-843f-a0f892140107'
        erc.type_tag = 'XXX-'
        erc.dump_checksums = {
            'dump': 'a_hash',
            'aux_dump': 'a_hash',
        }
        erc = dict(erc)

        mocked_web.input.return_value = form
        mocked_webapi.rawinput.return_value = rawform
        mocked_utc_now.return_value = datetime(2012, 5, 4, 15, 10)
        mocked_time.time.return_value = 3.0
        r = c.POST()
        ok_(r.startswith('CrashID=XXX-'))
        ok_(r.endswith('140107\n'))
        c.crash_storage.save_raw_crash.assert_called_with(
            erc,
            {'dump':'fake dump', 'aux_dump':'aux_dump contents'},
            r[12:-1]
        )

    @mock.patch('socorro.collector.wsgi_generic_collector.time')
    @mock.patch('socorro.collector.wsgi_generic_collector.utc_now')
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
        c = GenericCollector(config)
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
        erc.timestamp = 3.0
        erc.submitted_timestamp = '2012-05-04T15:10:00'
        erc.type_tag = 'XXX-'
        erc.dump_checksums = {
            'dump': 'a_hash',
            'aux_dump': 'a_hash',
        }
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
        r = c.POST()
        ok_(r.startswith('CrashID=XXX-'))
        print r
        ok_(r.endswith('120504\n'))
        erc['crash_id'] = r[12:-1]
        c.crash_storage.save_raw_crash.assert_called_with(
            erc,
            {'dump':'fake dump', 'aux_dump':'aux_dump contents'},
            r[12:-1]
        )

    def test_no_x00_character(self):
        config = self.get_standard_config()
        c = GenericCollector(config)

        eq_(c._no_x00_character('\x00hello'), 'hello')
        eq_(c._no_x00_character(u'\u0000bye'), 'bye')
        eq_(c._no_x00_character(u'\u0000\x00bye'), 'bye')
