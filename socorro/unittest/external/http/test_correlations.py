# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import shutil
import os
import tempfile

import mock
from nose.tools import eq_, ok_, assert_raises

from socorro.external.http import correlations
from socorro.lib.util import DotDict
from socorro.unittest.testbase import TestCase

SAMPLE_CORE_COUNTS = open(
    os.path.join(os.path.dirname(__file__),
                 'sample-core-counts.txt')
).read()
SAMPLE_CORE_COUNTS_WITH_HANGS = open(
    os.path.join(os.path.dirname(__file__),
                 'sample-core-counts-with-hangs.txt')
).read()


class Response(object):
    def __init__(self, content=None, status_code=200):
        self.content = content
        self.status_code = status_code


class TestCorrelations(TestCase):

    def setUp(self):
        super(TestCorrelations, self).setUp()
        self.temp_dirs = []

    def tearDown(self):
        super(TestCorrelations, self).tearDown()
        for temp_dir in self.temp_dirs:
            shutil.rmtree(temp_dir)

    def _get_model(self, overrides):
        new_temp_dir = tempfile.mkdtemp()
        self.temp_dirs.append(new_temp_dir)
        config_values = {
            'base_url': 'http://crashanalysis.com',
            'save_root': new_temp_dir,
            'save_download': True,
            'save_seconds': 1000,
        }
        config_values.update(overrides)
        cls = correlations.Correlations
        config = DotDict()
        config.logger = mock.Mock()
        config.http = DotDict()
        config.http.correlations = DotDict(config_values)
        return cls(config=config)

    @mock.patch('requests.get')
    def test_simple_download(self, rget):

        def mocked_get(url, **kwargs):
            if 'core-counts' in url:
                return Response(SAMPLE_CORE_COUNTS)
            raise NotImplementedError

        rget.side_effect = mocked_get

        model = self._get_model({
            'base_url': 'http://doesntmatter/',
            'save_download': False,
        })

        base_params = {
            'platform': 'Windows NT',
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '24.0a1',
        }
        signature = 'js::types::IdToTypeId(int)'
        result = model.get(**dict(base_params, signature=signature))

        # See sample-core-counts.txt why I chose these tests
        eq_(result['count'], 2551)
        eq_(result['reason'], 'EXCEPTION_ACCESS_VIOLATION_READ')
        eq_(len(result['load'].splitlines()), 17)

    @mock.patch('requests.get')
    def test_failing_download_no_error(self, rget):

        def mocked_get(url, **kwargs):
            return Response('', 404)

        rget.side_effect = mocked_get

        model = self._get_model({
            'base_url': 'http://doesntmatter/',
        })

        base_params = {
            'platform': 'Windows NT',
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '24.0a2',
        }
        signature = 'js::types::IdToTypeId(int)'
        result = model.get(**dict(base_params, signature=signature))
        eq_(result, None)

    @mock.patch('requests.get')
    def test_failing_download_should_not_cached(self, rget):

        calls = []

        def mocked_get(url, **kwargs):
            calls.append(url)
            # the first two calls should fail
            # (it's two because of the .txt and the .txt.gz attempt)
            if len(calls) < 3:
                return Response('', 404)
            else:
                return Response(SAMPLE_CORE_COUNTS)

        rget.side_effect = mocked_get

        model = self._get_model({
            'base_url': 'http://doesntmatter/',
            'save_download': True,
        })

        base_params = {
            'platform': 'Windows NT',
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '24.0a1',
        }
        signature = 'js::types::IdToTypeId(int)'
        result = model.get(**dict(base_params, signature=signature))
        eq_(result, None)
        # let's pretend we wait a while and try again, then it shouldn't
        # have cached the second time
        result = model.get(**dict(base_params, signature=signature))
        # See sample-core-counts.txt why I chose these tests
        eq_(result['count'], 2551)

    @mock.patch('requests.get')
    def test_failing_download_raised_error(self, rget):

        def mocked_get(url, **kwargs):
            return Response('Crap!', 500)

        rget.side_effect = mocked_get

        model = self._get_model({
            'base_url': 'http://doesntmatter/',
        })

        base_params = {
            'platform': 'Windows NT',
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '24.0a4',
        }
        signature = 'js::types::IdToTypeId(int)'
        params = dict(base_params, signature=signature)
        assert_raises(correlations.DownloadError, model.get, **params)

    @mock.patch('requests.get')
    def test_download_signature_last_in_platform(self, rget):
        """look for a signature that is last under that platform"""

        def mocked_get(url, **kwargs):
            if 'core-counts' in url:
                return Response(SAMPLE_CORE_COUNTS)
            raise NotImplementedError

        rget.side_effect = mocked_get

        model = self._get_model({
            'base_url': 'http://doesntmatter/',
            'save_download': False,
        })

        base_params = {
            'platform': 'Mac OS X',
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '24.0a1',
        }

        result = model.get(**dict(
            base_params,
            signature='JS_HasPropertyById(JSContext*, JSObject*, long, int*)',
        ))
        eq_(result['count'], 10)
        eq_(result['reason'], 'EXC_BAD_ACCESS / 0x0000000d')
        eq_(len(result['load'].splitlines()), 5)

    @mock.patch('requests.get')
    def test_download_signature_middle_in_platform(self, rget):
        """look for a signature that is last under that platform"""

        def mocked_get(url, **kwargs):
            if 'core-counts' in url:
                return Response(SAMPLE_CORE_COUNTS)
            raise NotImplementedError

        rget.side_effect = mocked_get

        model = self._get_model({
            'base_url': 'http://doesntmatter/',
            'save_download': False,
        })

        base_params = {
            'platform': 'Mac OS X',
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '24.0a1',
        }

        result = model.get(**dict(
            base_params,
            signature='js::CompartmentChecker::fail(JSCompartment*, '
                      'JSCompartment*)',
        ))
        eq_(result['count'], 11)
        eq_(
            result['reason'],
            'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS'
        )
        eq_(len(result['load'].splitlines()), 5)

    @mock.patch('requests.get')
    def test_download_with_unrecognized_signature(self, rget):

        def mocked_get(url, **kwargs):
            if 'core-counts' in url:
                return Response(SAMPLE_CORE_COUNTS)
            raise NotImplementedError

        rget.side_effect = mocked_get

        model = self._get_model({
            'base_url': 'http://doesntmatter/',
            'save_download': False,
        })

        base_params = {
            'platform': 'Windows NT',
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '24.0a1',
        }

        result = model.get(**dict(base_params, signature='OTHER'))
        ok_(not result['reason'])
        ok_(not result['count'])
        ok_(not result['load'])

    @mock.patch('requests.get')
    def test_valid_signature_but_wrong_platform(self, rget):

        def mocked_get(url, **kwargs):
            if 'core-counts' in url:
                return Response(SAMPLE_CORE_COUNTS)
            raise NotImplementedError

        rget.side_effect = mocked_get

        model = self._get_model({
            'base_url': 'http://doesntmatter/',
            'save_download': False,
        })

        base_params = {
            'platform': 'Windows NT',
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '24.0a1',
        }

        # try a "valid" signature that is under a different platform
        result = model.get(**dict(
            base_params,
            signature='JS_HasPropertyById(JSContext*, JSObject*, long, int*)',
        ))
        ok_(not result['reason'])
        ok_(not result['count'])
        ok_(not result['load'])

    @mock.patch('requests.get')
    def test_save_download(self, rget):

        calls = []

        def mocked_get(url, **kwargs):
            calls.append(url)
            if 'core-counts' in url:
                return Response(SAMPLE_CORE_COUNTS)
            raise NotImplementedError

        rget.side_effect = mocked_get

        tmp_directory = tempfile.mkdtemp()

        try:
            model = self._get_model({
                'base_url': 'http://doesntmatter/',
                'save_download': True,
                'save_root': tmp_directory,
            })

            params = {
                'platform': 'Windows NT',
                'product': 'Firefox',
                'report_type': 'core-counts',
                'version': '24.0a1',
                'signature': 'js::types::IdToTypeId(int)',
            }
            result = model.get(**params)
            assert len(calls) == 1
            eq_(result['count'], 2551)

            now = datetime.datetime.utcnow()
            yesterday = now - datetime.timedelta(days=1)
            yesterday_str = yesterday.strftime('%Y%m%d')
            save_directory = os.path.join(tmp_directory, yesterday_str)
            assert os.path.isdir(save_directory)
            filename, = os.listdir(save_directory)
            assert filename.endswith('.txt')

            content = open(os.path.join(save_directory, filename)).read()
            content = content.replace('2551', '3662')
            open(os.path.join(save_directory, filename), 'w').write(content)

            result = model.get(**params)
            assert len(calls) == 1
            eq_(result['count'], 3662)

        finally:
            shutil.rmtree(tmp_directory)


class TestCorrelationsSignatures(TestCase):

    @staticmethod
    def _get_model(overrides=None):
        config_values = {
            'base_url': 'http://crashanalysis.com',
            'save_root': '',
            'save_download': False,
            'save_seconds': 1000,
        }
        if overrides:
            config_values.update(overrides)
        cls = correlations.CorrelationsSignatures
        config = DotDict()
        config.logger = mock.Mock()
        config.http = DotDict()
        config.http.correlations = DotDict(config_values)
        return cls(config=config)

    @mock.patch('requests.get')
    def test_simple_download(self, rget):

        def mocked_get(url, **kwargs):
            if 'core-counts' in url:
                return Response(SAMPLE_CORE_COUNTS)
            raise NotImplementedError

        rget.side_effect = mocked_get

        model = self._get_model()

        params = {
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '24.0a1',
        }
        result = model.get(**dict(params, platforms=['Mac OS X', 'Linux']))
        assert result['total']
        eq_(result['total'], 9)
        # belongs to Mac OS X
        ok_(
            'JS_HasPropertyById(JSContext*, JSObject*, long, int*)'
            in result['hits']
        )
        # belongs to Linux
        ok_('js::types::IdToTypeId(long)' in result['hits'])
        # belongs to Windows NT
        ok_('js::types::IdToTypeId(int)' not in result['hits'])

    @mock.patch('requests.get')
    def test_no_signatures(self, rget):

        def mocked_get(url, **kwargs):
            if 'core-counts' in url:
                return Response(SAMPLE_CORE_COUNTS)
            raise NotImplementedError

        rget.side_effect = mocked_get

        model = self._get_model()

        params = {
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '24.0a3',
        }
        result = model.get(**dict(params, platforms=['OS/2']))
        eq_(result['total'], 0)

    @mock.patch('requests.get')
    def test_failing_download_no_error(self, rget):

        def mocked_get(url, **kwargs):
            return Response('', 404)

        rget.side_effect = mocked_get

        model = self._get_model()

        params = {
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '24.0a1',
        }
        result = model.get(**dict(params, platforms=['Mac OS X', 'Linux']))
        eq_(result, None)

    @mock.patch('requests.get')
    def test_empty_hang_signatures(self, rget):

        def mocked_get(url, **kwargs):
            if 'core-counts' in url and '32.0.2' in url:
                return Response(SAMPLE_CORE_COUNTS_WITH_HANGS)
            raise NotImplementedError

        rget.side_effect = mocked_get

        model = self._get_model()

        params = {
            'product': 'Firefox',
            'report_type': 'core-counts',
            'version': '32.0.2',
        }
        result = model.get(**dict(params, platforms=['Windows NT']))
        hits = result['hits']
        # know thy fixtures
        eq_(hits[0], '_PeekMessage')
        eq_(hits[1], 'base::MessagePumpForUI::ProcessNextWindowsMessage()')
        eq_(hits[2], 'hang')
        eq_(result['total'], 3)
