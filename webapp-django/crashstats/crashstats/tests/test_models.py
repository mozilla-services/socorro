import json
import random
import urlparse
from past.builtins import basestring

import mock
import pytest
from six import text_type

from django.core.cache import cache
from django.conf import settings
from django.utils import dateparse

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.crashstats import models
from socorro.lib import BadArgumentError


class Response(object):
    def __init__(self, content=None, status_code=200):
        self.raw = content
        if not isinstance(content, basestring):
            content = json.dumps(content)
        self.content = content.strip()
        self.status_code = status_code

    @property
    def text(self):
        # similar to content but with the right encoding
        return text_type(self.content, 'utf-8')

    def json(self):
        return self.raw


class TestGraphicsDevices(DjangoTestCase):
    def setUp(self):
        super(TestGraphicsDevices, self).setUp()
        # thanks to crashstats.settings.test
        assert settings.CACHE_IMPLEMENTATION_FETCHES
        cache.clear()

    def tearDown(self):
        super(TestGraphicsDevices, self).tearDown()

    def test_get_pairs(self):
        """Test get_pairs() works correctly

        The GraphicsDevice.get_pairs() lets you expand a bunch of (vendor, adapter)
        pairs at the same time. It's more performant since it does a single query.

        """
        models.GraphicsDevice.objects.create(
            vendor_hex='vhex3',
            vendor_name='V 3',
            adapter_hex='ahex3',
            adapter_name='A 3'
        )
        models.GraphicsDevice.objects.create(
            vendor_hex='vhex2',
            vendor_name='V 2',
            adapter_hex='ahex2',
            adapter_name='A 2',
        )
        models.GraphicsDevice.objects.create(
            vendor_hex='vhex1',
            vendor_name='V 1',
            adapter_hex='ahex1',
            adapter_name='A 1',
        )

        r = models.GraphicsDevice.objects.get_pairs(
            ['vhex1', 'vhex2'],
            ['ahex1', 'ahex2'],
        )
        expected = {
            ('vhex1', 'ahex1'): ('V 1', 'A 1'),
            ('vhex2', 'ahex2'): ('V 2', 'A 2'),
        }
        assert r == expected

        r = models.GraphicsDevice.objects.get_pairs(
            ['vhex2', 'vhex3'],
            ['ahex2', 'ahex3'],
        )
        assert len(r) == 2
        expected = {
            ('vhex2', 'ahex2'): ('V 2', 'A 2'),
            ('vhex3', 'ahex3'): ('V 3', 'A 3'),
        }
        assert r == expected


class TestSignatureFirstDate(DjangoTestCase):
    def setUp(self):
        super(TestSignatureFirstDate, self).setUp()
        # thanks to crashstats.settings.test
        assert settings.CACHE_IMPLEMENTATION_FETCHES
        cache.clear()

    def tearDown(self):
        super(TestSignatureFirstDate, self).tearDown()

    def test_get_one(self):
        some_date = dateparse.parse_datetime('2018-10-06T00:22:58.074859+00:00')

        models.Signature.objects.create(
            signature='OOM | Small',
            first_build='20180920131237',
            first_date=some_date
        )
        models.Signature.objects.create(
            signature='OOM | Large',
            first_build='20180920131237',
            first_date=some_date
        )

        api = models.SignatureFirstDate()

        resp = api.get(signatures='OOM | Small')
        assert resp['total'] == 1
        assert resp['hits'] == [
            {
                'first_build': '20180920131237',
                'first_date': '2018-10-06T00:22:58.074859+00:00',
                'signature': 'OOM | Small'
            }
        ]

    def test_get_two(self):
        some_date = dateparse.parse_datetime('2018-10-06T00:22:58.074859+00:00')

        models.Signature.objects.create(
            signature='OOM | Small',
            first_build='20180920131237',
            first_date=some_date
        )
        models.Signature.objects.create(
            signature='OOM | Large',
            first_build='20180920131237',
            first_date=some_date
        )

        api = models.SignatureFirstDate()

        resp = api.get(signatures=['OOM | Small', 'OOM | Large'])
        assert resp['total'] == 2
        assert resp['hits'] == [
            {
                'first_build': '20180920131237',
                'first_date': '2018-10-06T00:22:58.074859+00:00',
                'signature': 'OOM | Small'
            },
            {
                'first_build': '20180920131237',
                'first_date': '2018-10-06T00:22:58.074859+00:00',
                'signature': 'OOM | Large'
            }
        ]


class TestModels(DjangoTestCase):

    def setUp(self):
        super(TestModels, self).setUp()
        # thanks to crashstats.settings.test
        assert settings.CACHE_IMPLEMENTATION_FETCHES
        cache.clear()

    def tearDown(self):
        super(TestModels, self).tearDown()

    @mock.patch('requests.Session')
    def test_bugzilla_api(self, rsession):
        model = models.BugzillaBugInfo

        api = model()

        def mocked_get(url, **options):
            assert url.startswith(settings.BZAPI_BASE_URL)
            parsed = urlparse.urlparse(url)
            query = urlparse.parse_qs(parsed.query)
            assert query['include_fields'] == ['summary,status,id,resolution']
            return Response({
                'bugs': [
                    {
                        'status': 'NEW',
                        'resolution': '',
                        'id': 123456789,
                        'summary': 'Some summary'
                    },
                ]
            })

        rsession().get.side_effect = mocked_get
        info = api.get('123456789')
        expected = [{
            'status': 'NEW',
            'resolution': '',
            'id': 123456789,
            'summary': 'Some summary'
        }]
        assert info['bugs'] == expected

        # prove that it's cached
        def new_mocked_get(**options):
            return Response({
                'bugs': [
                    {
                        'status': 'RESOLVED',
                        'resolution': '',
                        'id': 123456789,
                        'summary': 'Some summary'
                    },
                ]
            })

        rsession().get.side_effect = new_mocked_get
        info = api.get('123456789')
        expected = [{
            'status': 'NEW',
            'resolution': '',
            'id': 123456789,
            'summary': 'Some summary'
        }]
        assert info['bugs'] == expected

    @mock.patch('requests.Session')
    def test_bugzilla_api_bad_status_code(self, rsession):
        model = models.BugzillaBugInfo

        api = model()

        def mocked_get(url, **options):
            return Response("I'm a teapot", status_code=418)

        rsession().get.side_effect = mocked_get
        with pytest.raises(models.BugzillaRestHTTPUnexpectedError):
            api.get('123456789')

    def test_processed_crash(self):
        model = models.ProcessedCrash
        api = model()

        def mocked_get(**params):
            assert 'datatype' in params
            assert params['datatype'] == 'processed'

            return {
                'product': 'WaterWolf',
                'uuid': '7c44ade2-fdeb-4d6c-830a-07d302120525',
                'version': '13.0',
                'build': '20120501201020',
                'ReleaseChannel': 'beta',
                'os_name': 'Windows NT',
                'date_processed': '2012-05-25 11:35:57',
                'success': True,
                'signature': 'CLocalEndpointEnumerator::OnMediaNotific',
                'addons': [
                    [
                        'testpilot@labs.mozilla.com',
                        '1.2.1'
                    ],
                    [
                        '{972ce4c6-7e08-4474-a285-3208198ce6fd}',
                        '13.0'
                    ]
                ]
            }

        model.implementation().get.side_effect = mocked_get
        r = api.get(crash_id='7c44ade2-fdeb-4d6c-830a-07d302120525')
        assert r['product']

    def test_unredacted_crash(self):
        model = models.UnredactedCrash
        api = model()

        def mocked_get(**params):
            assert 'datatype' in params
            assert params['datatype'] == 'unredacted'

            return {
                'product': 'WaterWolf',
                'uuid': '7c44ade2-fdeb-4d6c-830a-07d302120525',
                'version': '13.0',
                'build': '20120501201020',
                'ReleaseChannel': 'beta',
                'os_name': 'Windows NT',
                'date_processed': '2012-05-25 11:35:57',
                'success': True,
                'signature': 'CLocalEndpointEnumerator::OnMediaNotific',
                'exploitability': 'Sensitive stuff',
                'addons': [
                    [
                        'testpilot@labs.mozilla.com',
                        '1.2.1',
                    ],
                    [
                        '{972ce4c6-7e08-4474-a285-3208198ce6fd}',
                        '13.0',
                    ]
                ],
            }

        model.implementation().get.side_effect = mocked_get

        r = api.get(crash_id='7c44ade2-fdeb-4d6c-830a-07d302120525')
        assert r['product']
        assert r['exploitability']

    def test_bugs(self):
        model = models.Bugs
        api = model()

        def mocked_get(**options):
            assert options == {'signatures': ['Pickle::ReadBytes']}
            return {'hits': ['123456789']}

        models.Bugs.implementation().get.side_effect = mocked_get

        r = api.get(signatures='Pickle::ReadBytes')
        assert r['hits']

    def test_bugs_called_without_signatures(self):
        model = models.Bugs
        api = model()

        with pytest.raises(models.RequiredParameterError):
            api.get()

    def test_signatures_by_bugs(self):
        model = models.SignaturesByBugs
        api = model()

        def mocked_get(**options):
            assert options == {'bug_ids': ['123456789']}
            return {'hits': {'signatures': 'Pickle::ReadBytes'}}

        models.SignaturesByBugs.implementation().get.side_effect = mocked_get

        r = api.get(bug_ids='123456789')
        assert r['hits']

    def test_sigs_by_bugs_called_without_bug_ids(self):
        model = models.SignaturesByBugs
        api = model()

        with pytest.raises(models.RequiredParameterError):
            api.get()

    def test_raw_crash(self):
        model = models.RawCrash
        api = model()

        def mocked_get(**params):
            return {
                'InstallTime': '1339289895',
                'FramePoisonSize': '4096',
                'Theme': 'classic/1.0',
                'Version': '5.0a1',
                'Email': 'socorro-123@restmail.net',
                'Vendor': 'Mozilla',
            }

        model.implementation().get.side_effect = mocked_get
        r = api.get(crash_id='some-crash-id')
        assert r['Vendor'] == 'Mozilla'
        assert 'Email' in r  # no filtering at this level

    def test_raw_crash_invalid_id(self):
        # NOTE(alexisdeschamps): this undoes the mocking of the implementation so we can test
        # the implementation code.
        models.RawCrash.implementation = self._mockeries[models.RawCrash]
        model = models.RawCrash
        api = model()

        with pytest.raises(BadArgumentError):
            api.get(crash_id='821fcd0c-d925-4900-85b6-687250180607docker/as_me.sh')

    def test_raw_crash_raw_data(self):

        model = models.RawCrash
        api = model()

        mocked_calls = []

        def mocked_get(**params):
            mocked_calls.append(params)
            assert params['datatype'] == 'raw'
            if params.get('name') == 'other':
                return '\xe0\xe0'
            else:
                return '\xe0'

        model.implementation().get.side_effect = mocked_get

        r = api.get(crash_id='some-crash-id', format='raw')
        assert r == '\xe0'

        r = api.get(crash_id='some-crash-id', format='raw', name='other')
        assert r == '\xe0\xe0'

    def test_platforms(self):
        api = models.Platforms()

        def mocked_get(**options):
            return {
                'hits': [
                    {
                        'code': 'win',
                        'name': 'Windows'
                    },
                    {
                        'code': 'unk',
                        'name': 'Unknown'
                    }
                ],
                'total': 2
            }

        models.Platforms.implementation().get.side_effect = mocked_get

        r = api.get()
        assert len(r) == 2
        assert 'Windows' in settings.DISPLAY_OS_NAMES
        assert r[0] == {'code': 'win', 'name': 'Windows', 'display': True}
        assert 'Unknown' not in settings.DISPLAY_OS_NAMES
        assert r[1] == {'code': 'unk', 'name': 'Unknown', 'display': False}

    @mock.patch('requests.Session')
    def test_massive_querystring_caching(self, rsession):
        # doesn't actually matter so much what API model we use
        # see https://bugzilla.mozilla.org/show_bug.cgi?id=803696
        model = models.BugzillaBugInfo
        api = model()

        def mocked_get(url, **options):
            assert url.startswith(settings.BZAPI_BASE_URL)
            return Response({
                'bugs': [{
                    'id': 123456789,
                    'status': 'NEW',
                    'resolution': '',
                    'summary': 'Some Summary',
                }],
            })

        rsession().get.side_effect = mocked_get
        bugnumbers = [str(random.randint(10000, 100000)) for __ in range(100)]
        info = api.get(bugnumbers)
        assert info

    def test_Reprocessing(self):
        api = models.Reprocessing()

        def mocked_reprocess(crash_ids):
            if crash_ids == 'some-crash-id':
                return True
            elif crash_ids == 'bad-crash-id':
                return
            raise NotImplementedError(crash_ids)

        models.Reprocessing.implementation().reprocess = mocked_reprocess
        assert api.post(crash_ids='some-crash-id')
        # Note that it doesn't raise an error if
        # the ReprocessingOneRabbitMQCrashStore choses NOT to queue it.
        assert not api.post(crash_ids='bad-crash-id')

    def test_Priorityjob(self):
        api = models.Priorityjob()

        def mocked_process(crash_ids):
            if crash_ids == 'some-crash-id':
                return True
            elif crash_ids == 'bad-crash-id':
                return
            raise NotImplementedError(crash_ids)

        models.Priorityjob.implementation().process = mocked_process
        assert api.post(crash_ids='some-crash-id')
        # Note that it doesn't raise an error if
        # the PriorityjobRabbitMQCrashStore choses NOT to queue it.
        assert not api.post(crash_ids='bad-crash-id')

    def test_CrontabberState(self):
        api = models.CrontabberState()

        def mocked_get(*args, **kwargs):
            return {
                'state': {
                    'missing-symbols': {
                        'next_run': '2017-11-14T01:45:36.563151+00:00',
                        'depends_on': [],
                        'last_run': '2017-11-14T01:40:36.563151+00:00',
                        'last_success': '2017-11-06T02:30:11.567874+00:00',
                        'error_count': 506,
                        'last_error': {
                            'traceback': 'TRACEBACK HERE',
                            'type': '<class \'boto.exception.S3ResponseError\'>',
                            'value': 'EXCEPTION VALUE HERE'
                        },
                        'ongoing': None,
                        'first_run': '2016-06-22T17:55:05.196209+00:00'
                    },
                }
            }
        models.CrontabberState.implementation().get.side_effect = (
            mocked_get
        )

        resp = api.get()

        # Verify that the response redacts the last_error.traceback and
        # last_error.value and otherwise maintains the expected shape
        expected_resp = {
            'state': {
                'missing-symbols': {
                    'next_run': '2017-11-14T01:45:36.563151+00:00',
                    'depends_on': [],
                    'last_run': '2017-11-14T01:40:36.563151+00:00',
                    'last_success': '2017-11-06T02:30:11.567874+00:00',
                    'error_count': 506,
                    'last_error': {
                        'traceback': 'See error logging system.',
                        'type': '<class \'boto.exception.S3ResponseError\'>',
                        'value': 'See error logging system.'
                    },
                    'ongoing': None,
                    'first_run': '2016-06-22T17:55:05.196209+00:00'
                },
            }
        }
        assert resp == expected_resp
