import json
import datetime
import random
import urlparse

import mock
import requests
from nose.tools import eq_, ok_, assert_raises

from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

from crashstats.base.tests.testbase import DjangoTestCase, TestCase
from crashstats.crashstats import models


class Response(object):
    def __init__(self, content=None, status_code=200):
        if not isinstance(content, basestring):
            content = json.dumps(content)
        self.content = content.strip()
        self.status_code = status_code

    @property
    def text(self):
        # similar to content but with the right encoding
        return unicode(self.content, 'utf-8')


class TestExceptions(TestCase):

    def test_BadStatusCodeError(self):
        try:
            raise models.BadStatusCodeError(500, 'some message')
        except models.BadStatusCodeError as exp:
            ok_('500: some message' in str(exp))
            eq_(exp.status, 500)


class TestModels(DjangoTestCase):

    def setUp(self):
        super(TestModels, self).setUp()
        # thanks to crashstats.settings.test
        assert settings.CACHE_MIDDLEWARE
        cache.clear()

    def tearDown(self):
        super(TestModels, self).tearDown()

        # We use a memoization technique on the SocorroCommon so that we
        # can get the same implementation class instance repeatedly under
        # the same request. This is great for low-level performance but
        # it makes it impossible to test classes that are imported only
        # once like they are in unit test running.
        models.SocorroCommon.clear_implementations_cache()

    def test_kwargs_to_params_basics(self):
        """every model instance has a kwargs_to_params method which
        converts raw keyword arguments (a dict basically) to a cleaned up
        dict where every value has been type checked or filtered.
        """
        api = models.Correlations()
        assert_raises(
            models.RequiredParameterError,
            api.kwargs_to_params,
            {}
        )
        inp = {
            'report_type': 'XXX',
            'product': 'XXX',
            'version': 'XXX',
            'signature': 'XXX',
            'platform': 'XXX',
        }
        result = api.kwargs_to_params(inp)
        # no interesting conversion or checks here
        eq_(result, inp)

    @mock.patch('requests.get')
    def test_bugzilla_api(self, rget):
        model = models.BugzillaBugInfo

        api = model()

        def mocked_get(url, **options):
            assert url.startswith(models.BugzillaAPI.base_url)
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

        rget.side_effect = mocked_get
        info = api.get('123456789')
        eq_(info['bugs'], [{
            'status': 'NEW',
            'resolution': '',
            'id': 123456789,
            'summary': 'Some summary'
        }])

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

        rget.side_effect = new_mocked_get
        info = api.get('123456789')
        eq_(info['bugs'], [{
            'status': 'NEW',
            'resolution': '',
            'id': 123456789,
            'summary': 'Some summary'
        }])

    def test_processed_crash(self):
        model = models.ProcessedCrash
        api = model()

        def mocked_get(**params):
            ok_('datatype' in params)
            eq_(params['datatype'], 'processed')

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
        ok_(r['product'])

    def test_unredacted_crash(self):
        model = models.UnredactedCrash
        api = model()

        def mocked_get(**params):
            ok_('datatype' in params)
            eq_(params['datatype'], 'unredacted')

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
        ok_(r['product'])
        ok_(r['exploitability'])

    def test_bugs(self):
        model = models.Bugs
        api = model()

        def mocked_get(**options):
            assert options == {'signatures': ['Pickle::ReadBytes']}
            return {'hits': ['123456789']}

        models.Bugs.implementation().get.side_effect = mocked_get

        r = api.get(signatures='Pickle::ReadBytes')
        ok_(r['hits'])

    def test_bugs_called_without_signatures(self):
        model = models.Bugs
        api = model()
        assert_raises(models.RequiredParameterError, api.get)

    def test_signatures_by_bugs(self):
        model = models.SignaturesByBugs
        api = model()

        def mocked_get(**options):
            assert options == {'bug_ids': ['123456789']}
            return {'hits': {'signatures': 'Pickle::ReadBytes'}}

        models.SignaturesByBugs.implementation().get.side_effect = mocked_get

        r = api.get(bug_ids='123456789')
        ok_(r['hits'])

    def test_sigs_by_bugs_called_without_bug_ids(self):
        model = models.SignaturesByBugs
        api = model()

        assert_raises(models.RequiredParameterError, api.get)

    def test_signature_first_date(self):
        api = models.SignatureFirstDate()

        def mocked_get(**options):
            return {
                'hits': [],
                'total': 0
            }

        models.SignatureFirstDate.implementation().get.side_effect = mocked_get
        r = api.get(
            signatures=['Pickle::ReadBytes', 'FakeSignature'],
        )
        eq_(r['total'], 0)

    def test_signature_first_date_get_dates(self):
        api = models.SignatureFirstDate()

        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        tomorrow_tomorrow = tomorrow + datetime.timedelta(days=1)

        def mocked_get(**kwargs):
            signatures = kwargs['signatures']
            # This mocking function really makes sure that only what is
            # expected to be called for is called for.
            # Basically, the first time it expects to be asked
            # about 'Sig 1' and 'Sig 2'.
            # The second time it expect to only be asked about 'Sig 3'.
            # Anything else will raise a NotImplementedError.
            if sorted(signatures) == ['Sig 1', 'Sig 2']:
                return {
                    'hits': [
                        {
                            'signature': 'Sig 1',
                            'first_build': '201601010101',
                            'first_date': now,
                        },
                        {
                            'signature': 'Sig 2',
                            'first_build': '201602020202',
                            'first_date': tomorrow,
                        }
                    ],
                    'total': 2
                }
            elif sorted(signatures) == ['Sig 3']:
                return {
                    'hits': [
                        {
                            'signature': 'Sig 3',
                            'first_build': '201603030303',
                            'first_date': tomorrow_tomorrow,
                        }
                    ],
                    'total': 1
                }
            raise NotImplementedError(signatures)

        models.SignatureFirstDate.implementation().get.side_effect = mocked_get
        r = api.get_dates(['Sig 1', 'Sig 2'])
        eq_(
            r,
            {
                'Sig 1': {
                    'first_build': '201601010101',
                    'first_date': now,
                },
                'Sig 2': {
                    'first_build': '201602020202',
                    'first_date': tomorrow,
                },
            }
        )
        r = api.get_dates(['Sig 2', 'Sig 3'])
        eq_(
            r,
            {
                'Sig 2': {
                    'first_build': '201602020202',
                    'first_date': tomorrow,
                },
                'Sig 3': {
                    'first_build': '201603030303',
                    'first_date': tomorrow_tomorrow,
                },

            }
        )

    def test_status(self):
        def mocked_get(**options):
            return {
                'breakpad_revision': '1035',
                'socorro_revision': (
                    '017d7b3f7042ce76bc80949ae55b41d1e915ab62'
                ),
            }

        models.Status.implementation().get.side_effect = mocked_get

        response = models.Status().get('3')
        ok_(response['breakpad_revision'])
        ok_(response['socorro_revision'])

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
        eq_(r['Vendor'], 'Mozilla')
        ok_('Email' in r)  # no filtering at this level

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
        eq_(r, '\xe0')

        r = api.get(crash_id='some-crash-id', format='raw', name='other')
        eq_(r, '\xe0\xe0')

    @mock.patch('requests.put')
    def test_put_featured_versions(self, rput):
        model = models.ReleasesFeatured
        api = model()

        def mocked_put(url, **options):
            assert '/releases/featured/' in url
            data = options['data']
            eq_(data['WaterWolf'], '18.0,19.0')
            eq_(data['NightTrain'], '1,2')
            return Response(True)

        rput.side_effect = mocked_put
        r = api.put(**{'WaterWolf': ['18.0', '19.0'],
                       'NightTrain': ['1', '2']})
        eq_(r, True)

    @mock.patch('requests.post')
    def test_create_release(self, rpost):
        model = models.Releases
        api = model()

        def mocked_post(url, **options):
            assert '/releases/release/' in url
            return Response(True)

        rpost.side_effect = mocked_post
        now = datetime.datetime.utcnow()
        r = api.post(**{
            'product': 'Firefox',
            'version': '1.0',
            'update_channel': 'beta',
            'build_id': now.strftime('%Y%m%d%H%M'),
            'platform': 'Windows',
            'beta_number': '0',
            'release_channel': 'Beta',
            'throttle': '1'
        })
        eq_(r, True)

    @mock.patch('requests.get')
    def test_correlations(self, rget):
        model = models.Correlations
        api = model()

        def mocked_get(url, params, **options):
            assert '/correlations' in url

            ok_('report_type' in params)
            eq_(params['report_type'], 'core-counts')

            return Response({
                'reason': 'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS',
                'count': 13,
                'load': '36% (4/11) vs.  26% (47/180) amd64 with 2 cores',
            })

        rget.side_effect = mocked_get
        r = api.get(report_type='core-counts',
                    product='WaterWolf',
                    version='1.0a1',
                    platform='Windows NT',
                    signature='FakeSignature')
        eq_(r['reason'], 'EXC_BAD_ACCESS / KERN_INVALID_ADDRESS')

    @mock.patch('requests.get')
    def test_correlations_signatures(self, rget):
        model = models.CorrelationsSignatures
        api = model()

        def mocked_get(url, params, **options):
            assert '/correlations/signatures' in url

            ok_('report_type' in params)
            eq_(params['report_type'], 'core-counts')

            return Response({
                'hits': [
                    'FakeSignature1',
                    'FakeSignature2'
                ],
                'total': 2,
            })

        rget.side_effect = mocked_get
        r = api.get(report_type='core-counts',
                    product='WaterWolf',
                    version='1.0a1',
                    platforms=['Windows NT', 'Linux'])
        eq_(r['total'], 2)
        r = api.get(report_type='core-counts',
                    product='WaterWolf',
                    version='1.0a1')
        eq_(r['total'], 2)

    @mock.patch('requests.get')
    def test_adu_by_signature(self, rget):
        model = models.AduBySignature
        api = model()

        def mocked_get(**options):
            ok_('product_name' in options)
            eq_(options['product_name'], 'WaterWolf')

            ok_('signature' in options)
            eq_(options['signature'], 'FakeSignature1')

            ok_('channel' in options)
            eq_(options['channel'], 'nightly')

            return {
                'hits': [
                    {
                        'build_date': '2014-04-01',
                        'os_name': 'Windows',
                        'buildid': '20140401000000',
                        'adu_count': 1,
                        'crash_count': 1,
                        'adu_date': '2014-04-01',
                        'signature': 'FakeSignature1',
                        'channel': 'nightly'},
                    {
                        'build_date': '2014-04-01',
                        'os_name': 'Windows',
                        'buildid': '20140401000001',
                        'adu_count': 2,
                        'crash_count': 2,
                        'adu_date': '2014-04-01',
                        'signature': 'FakeSignature2',
                        'channel': 'nightly'
                    },
                ],
                'total': 2,
            }

        models.AduBySignature.implementation().get.side_effect = mocked_get

        r = api.get(
            product_name='WaterWolf',
            signature='FakeSignature1',
            channel='nightly',
        )
        eq_(r['total'], 2)

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
        eq_(len(r), 2)
        assert 'Windows' in settings.DISPLAY_OS_NAMES
        eq_(r[0], {'code': 'win', 'name': 'Windows', 'display': True})
        assert 'Unknown' not in settings.DISPLAY_OS_NAMES
        eq_(r[1], {'code': 'unk', 'name': 'Unknown', 'display': False})

    def test_adi(self):
        model = models.ADI
        api = model()

        def mocked_get(**options):

            ok_('product' in options)
            eq_(options['product'], 'WaterWolf')

            ok_('versions' in options)
            eq_(options['versions'], ['2.0'])

            ok_('start_date' in options)
            ok_('end_date' in options)

            return {
                'hits': [
                    {

                        'build_type': 'aurora',
                        'adi_count': 12327L,
                        'version': '2.0',
                        'date': datetime.date(2015, 8, 12),

                    },
                    {
                        'build_type': 'release',
                        'adi_count': 4L,
                        'version': '2.0',
                        'date': datetime.date(2016, 8, 12),

                    }
                ],
                'total': 2
            }

        models.ADI.implementation().get.side_effect = mocked_get

        r = api.get(
            product='WaterWolf',
            versions=['2.0'],
            platforms=['Windows', 'Linux'],
            start_date=datetime.date(2015, 8, 12),
            end_date=datetime.date(2015, 8, 13),
        )
        eq_(r['total'], 2)

    def test_graphics_devices(self):
        api = models.GraphicsDevices()

        def mocked_get(**options):
            return {
                'hits': [
                    {
                        'vendor_hex': 'vhex2',
                        'vendor_name': 'V 2',
                        'adapter_hex': 'ahex2',
                        'adapter_name': 'A 2',
                    },
                    {
                        'vendor_hex': 'vhex1',
                        'vendor_name': 'V 1',
                        'adapter_hex': 'ahex1',
                        'adapter_name': 'A 1',
                    },
                ],
                'total': 2
            }

        models.GraphicsDevices.implementation().get.side_effect = (
            mocked_get
        )

        r = api.get(
            vendor_hex=['vhex1', 'vhex2'],
            adapter_hex=['ahex1', 'ahex2'],
        )
        eq_(r['total'], 2)
        eq_(
            r['hits'][0],
            {
                'vendor_hex': 'vhex2',
                'vendor_name': 'V 2',
                'adapter_hex': 'ahex2',
                'adapter_name': 'A 2',
            }
        )

    def test_graphics_devices_get_pairs(self):
        """The GraphicsDevices.get_pairs() is an abstraction of
        GraphicsDevices.get() on steroids. The input is similar as
        GraphicsDevices.get() but instead it returns a dict where
        each key is a (adapter hex, vendor hex) tuple and each key is
        (adapter name, vendor name) tuple.
        Internally it does some smart caching.
        """
        api = models.GraphicsDevices()

        params_called = []

        def mocked_get(**params):
            params_called.append(params)

            if 'vhex3' in params['vendor_hex']:
                return {
                    'hits': [
                        {
                            'vendor_hex': 'vhex3',
                            'vendor_name': 'V 3',
                            'adapter_hex': 'ahex3',
                            'adapter_name': 'A 3',
                        },
                    ],
                    'total': 1
                }
            else:
                return {
                    'hits': [
                        {
                            'vendor_hex': 'vhex2',
                            'vendor_name': 'V 2',
                            'adapter_hex': 'ahex2',
                            'adapter_name': 'A 2',
                        },
                        {
                            'vendor_hex': 'vhex1',
                            'vendor_name': 'V 1',
                            'adapter_hex': 'ahex1',
                            'adapter_name': 'A 1',
                        },
                    ],
                    'total': 2
                }

        models.GraphicsDevices.implementation().get.side_effect = (
            mocked_get
        )

        r = api.get_pairs(
            ['ahex1', 'ahex2'],
            ['vhex1', 'vhex2'],
        )
        eq_(
            r,
            {
                ('ahex1', 'vhex1'): ('A 1', 'V 1'),
                ('ahex2', 'vhex2'): ('A 2', 'V 2'),
            }
        )

        r = api.get_pairs(
            ['ahex2', 'ahex3'],
            ['vhex2', 'vhex3'],
        )
        assert len(r) == 2
        eq_(
            r,
            {
                ('ahex2', 'vhex2'): ('A 2', 'V 2'),
                ('ahex3', 'vhex3'): ('A 3', 'V 3'),
            }
        )

        # In the second call to `api.get_pairs()` we repeated the
        # (ahex2, vhex2) combo, so that second time, we could benefit from
        # caching and only need to query for the (ahex3, vhex3) combo.
        assert len(params_called) == 2
        eq_(
            params_called[0],
            {
                'adapter_hex': set(['ahex1', 'ahex2']),
                'vendor_hex': set(['vhex2', 'vhex1']),
            }
        )
        eq_(
            params_called[1],
            {
                'adapter_hex': set(['ahex3']),
                'vendor_hex': set(['vhex3']),
            }
        )

    @mock.patch('requests.get')
    def test_massive_querystring_caching(self, rget):
        # doesn't actually matter so much what API model we use
        # see https://bugzilla.mozilla.org/show_bug.cgi?id=803696
        model = models.BugzillaBugInfo
        api = model()

        def mocked_get(url, **options):
            assert url.startswith(models.BugzillaAPI.base_url)
            return Response({
                'bugs': [{
                    'id': 123456789,
                    'status': 'NEW',
                    'resolution': '',
                    'summary': 'Some Summary',
                }],
            })

        rget.side_effect = mocked_get
        bugnumbers = [str(random.randint(10000, 100000)) for __ in range(100)]
        info = api.get(bugnumbers)
        ok_(info)

    @mock.patch('crashstats.crashstats.models.time')
    @mock.patch('requests.get')
    def test_retry_on_connectionerror_success(self, rget, mocked_time):
        sleeps = []

        def mocked_sleeper(seconds):
            sleeps.append(seconds)

        mocked_time.sleep = mocked_sleeper

        # doesn't really matter which api we use
        model = models.BugzillaBugInfo
        api = model()

        calls = []

        def mocked_get(url, params, **options):
            calls.append(url)
            if len(calls) < 3:
                raise requests.ConnectionError('unable to connect')
            return Response({
                'bugs': [{
                    'id': 123456789,
                    'status': 'NEW',
                    'resolution': '',
                    'summary': 'Some Summary',
                }],
            })

        rget.side_effect = mocked_get
        info = api.get(['987654'])
        ok_(info['bugs'])

        eq_(len(calls), 3)  # had to attempt 3 times
        eq_(len(sleeps), 2)  # had to sleep 2 times

    @mock.patch('crashstats.crashstats.models.time')
    @mock.patch('requests.get')
    def test_retry_on_connectionerror_failing(self, rget, mocked_time):
        sleeps = []

        def mocked_sleeper(seconds):
            sleeps.append(seconds)

        mocked_time.sleep = mocked_sleeper

        # doesn't really matter which api we use
        model = models.BugzillaBugInfo
        api = model()

        calls = []

        def mocked_get(url, params, **options):
            calls.append(url)
            raise requests.ConnectionError('unable to connect')

        rget.side_effect = mocked_get
        assert_raises(
            requests.ConnectionError,
            api.get,
            ['987654'],
        )
        ok_(len(calls) > 3)  # had to attempt more than 3 times
        ok_(len(sleeps) > 2)  # had to sleep more than 2 times

    def test_Reprocessing(self):
        api = models.Reprocessing()

        def mocked_reprocess(crash_ids):
            if crash_ids == 'some-crash-id':
                return True
            elif crash_ids == 'bad-crash-id':
                return
            raise NotImplementedError(crash_ids)

        models.Reprocessing.implementation().reprocess = mocked_reprocess
        ok_(api.post(crash_ids='some-crash-id'))
        # Note that it doesn't raise an error if
        # the ReprocessingOneRabbitMQCrashStore choses NOT to queue it.
        ok_(not api.post(crash_ids='bad-crash-id'))

    def test_Priorityjob(self):
        api = models.Priorityjob()

        def mocked_process(crash_ids):
            if crash_ids == 'some-crash-id':
                return True
            elif crash_ids == 'bad-crash-id':
                return
            raise NotImplementedError(crash_ids)

        models.Priorityjob.implementation().process = mocked_process
        ok_(api.post(crash_ids='some-crash-id'))
        # Note that it doesn't raise an error if
        # the PriorityjobRabbitMQCrashStore choses NOT to queue it.
        ok_(not api.post(crash_ids='bad-crash-id'))
