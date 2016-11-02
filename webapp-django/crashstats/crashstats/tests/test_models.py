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

        # CrashesPerAdu allows from_date and end_date as datetime.date
        # but it should also allow to automatically convert datetime.datetime
        # instances to datetime.date
        api = models.CrashesPerAdu()
        inp = {
            'product': 'XXX',
            'versions': ['XXX'],
            'from_date': datetime.datetime.utcnow(),
            'os': '',  # not required and empty
        }
        result = api.kwargs_to_params(inp)
        eq_(result['product'], inp['product'])
        eq_(result['versions'], inp['versions'])
        eq_(result['from_date'], datetime.date.today().strftime('%Y-%m-%d'))
        ok_('os' not in result)

        # The value `0` is a perfectly fine value and should be kept in the
        # parameters, and not ignored as a "falsy" value.
        api = models.CrashesByExploitability()
        inp = {
            'batch': 0,
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

    @mock.patch('requests.get')
    def test_crashes_per_adu(self, rget):
        model = models.CrashesPerAdu
        api = model()

        def mocked_get(url, params, **options):
            assert '/crashes/daily' in url

            ok_('from_date' in params)
            ok_('to_date' in params)

            # because we always use `from_date=week_ago`...
            eq_(params['from_date'], week_ago.strftime('%Y-%m-%d'))
            # and we also always use `to_date=today`...
            eq_(params['to_date'], today.strftime('%Y-%m-%d'))

            if (
                'date_range_type' in params and
                params['date_range_type'] == 'report' and
                'os' in params and
                params['os'] == 'Windows'
            ):
                return Response({
                    'hits': {
                        'WaterWolf:5.0a1': {
                            '2012-10-10': {
                                'product': 'WaterWolf',
                                'adu': 1500,
                                'throttle': 0.5,
                                'crash_hadu': 13.0,
                                'version': '5.0a1',
                                'report_count': 195,
                                'date': '2012-10-08'
                            },
                        },
                    },
                })
            elif (
                'separated_by' in params and
                params['separated_by'] == 'os' and
                'os' in params and
                params['os'] == 'Linux'
            ):
                return Response({
                    'hits': {
                        'WaterWolf:5.0a1:lin': {
                            '2012-10-08': {
                                'product': 'WaterWolf',
                                'adu': 1500,
                                'throttle': 1.0,
                                'crash_hadu': 13.0,
                                'version': '5.0a1',
                                'report_count': 195,
                                'date': '2012-10-08',
                                'os': 'Windows'
                            },
                        }
                    }
                })
            elif (
                'date_range_type' in params and
                params['date_range_type'] == 'build'
            ):
                return Response({
                    'hits': {
                        'WaterWolf:5.0a1': {
                            '2012-10-08': {
                                'product': 'NightTrain',
                                'adu': 4500,
                                'crash_hadu': 13.0,
                                'version': '5.0a1',
                                'report_count': 585,
                                'date': '2012-10-08'
                            },
                        },
                    },
                })
            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        week_ago = today - datetime.timedelta(days=7)

        response = api.get(
            product='WaterWolf',
            versions=['5.0a1'],
            from_date=week_ago,
            to_date=today,
            date_range_type='build'
        )

        hits = sorted(response['hits'], reverse=True)
        for count, product_version in enumerate(hits, start=1):
            for day in sorted(response['hits'][product_version]):
                product = response['hits'][product_version][day]['product']

        ok_(response['hits'])
        eq_(product, 'NightTrain')

        response = api.get(
            product='WaterWolf',
            versions=['5.0a1'],
            from_date=week_ago,
            to_date=today,
            os='Windows',
            date_range_type='report'
        )

        hits = sorted(response['hits'], reverse=True)
        for count, product_version in enumerate(hits, start=1):
            for day in sorted(response['hits'][product_version]):
                current_day = day

        ok_(response['hits'])
        eq_(current_day, '2012-10-10')

    def test_crashes_per_adu_parameter_type_error(self):
        model = models.CrashesPerAdu
        api = model()

        today = datetime.datetime.utcnow()

        assert_raises(
            models.ParameterTypeError,
            api.get,
            product='WaterWolf',
            versions=['5.0a1'],
            from_date='NOT A DATE',
            to_date=today,
            date_range_type='build'
        )

    @mock.patch('requests.get')
    def test_tcbs(self, rget):
        model = models.TCBS
        api = model()

        def mocked_get(**options):
            assert '/crashes/signatures' in options['url']
            # expect no os_name parameter encoded in the URL
            assert 'os' not in options['params']
            return Response({
                'crashes': [],
                'totalPercentage': 0,
                'start_date': '2012-05-10',
                'end_date': '2012-05-24',
                'totalNumberOfCrashes': 0,
            })

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        # test for valid arguments
        api.get(
            product='Thunderbird',
            version='12.0',
            crash_type='plugin',
            end_date=today,
            date_range_type='report',
            limit=336
        )

    @mock.patch('requests.get')
    def test_tcbs_with_analyze_model_fetches_on(self, rget):
        # doesn't actually matter so much which model we're executing
        model = models.TCBS
        api = model()

        def mocked_get(**options):
            return Response({
                'crashes': [],
                'totalPercentage': 0,
                'start_date': '2012-05-10',
                'end_date': '2012-05-24',
                'totalNumberOfCrashes': 0,
            })

        rget.side_effect = mocked_get

        # before this shouldn't cache anything
        assert not cache.get('all_urls')
        with self.settings(ANALYZE_MODEL_FETCHES=True):
            api.get(
                product='Thunderbird',
                version='12.0',
                crash_type='plugin',
                end_date=datetime.datetime.utcnow(),
                date_range_type='report',
                limit=336
            )
        ok_(cache.get('all_urls'))

    def test_tcbs_parameter_type_error(self):
        model = models.TCBS
        api = model()
        today = datetime.datetime.utcnow()
        # test for valid arguments
        assert_raises(
            models.ParameterTypeError,
            api.get,
            product='Thunderbird',
            version='12.0',
            crash_type='plugin',
            end_date='CLEARLY-NOT-A-DATE',
            date_range_type='report',
            limit=336
        )

        assert_raises(
            models.ParameterTypeError,
            api.get,
            product='Thunderbird',
            version='12.0',
            crash_type='plugin',
            end_date=today,
            date_range_type='report',
            limit='NOT AN INT'
        )

    @mock.patch('requests.get')
    def test_tcbs_parameter_type_forgiving(self, rget):
        model = models.TCBS
        api = model()
        today = datetime.datetime.utcnow()

        def mocked_get(url, params, **options):
            assert '/crashes/signatures' in url
            # Expect no os_name parameter encoded in the URL.
            # Note that we pass `end_date=today` below,
            # but this gets converted to a datetime.date.
            ok_(today.strftime('%Y-%m-%d') in params['end_date'])
            ok_('os' not in params)

            return Response({
                'crashes': [],
                'totalPercentage': 0,
                'start_date': '2012-05-10',
                'end_date': '2012-05-24',
                'totalNumberOfCrashes': 0,
            })

        rget.side_effect = mocked_get
        # test for valid arguments
        api.get(
            product=u'Thunderbird',
            version='12.0',
            crash_type='plugin',
            end_date=today,  # is not a date
            date_range_type='report',
            limit='336'  # can be converted to an int
        )

    @mock.patch('requests.get')
    def test_tcbs_with_os_name(self, rget):
        model = models.TCBS
        api = model()

        def mocked_get(url, params, **options):
            assert '/crashes/signatures' in url
            ok_('os' in params)
            ok_('Win95' in params['os'])
            return Response({
                'crashes': [],
                'totalPercentage': 0,
                'start_date': '2012-05-10',
                'end_date': '2012-05-24',
                'totalNumberOfCrashes': 0,
            })

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        # test for valid arguments
        api.get(
            product='Thunderbird',
            version='12.0',
            crash_type='plugin',
            end_date=today,
            date_range_type='report',
            limit=336,
            os='Win95',
        )

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

    @mock.patch('requests.get')
    def test_signature_trend(self, rget):
        model = models.SignatureTrend
        api = model()

        def mocked_get(url, params, **options):
            assert 'crashes/signature_history' in url, url
            return Response({
                'hits': [],
                'total': 0,
            })

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        lastweek = today - datetime.timedelta(days=7)
        r = api.get(
            product='Thunderbird',
            version='12.0',
            signature='Pickle::ReadBytes',
            end_date=today,
            start_date=lastweek
        )
        eq_(r['total'], 0)

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

    @mock.patch('requests.get')
    def test_exploitable_crashes(self, rget):
        model = models.CrashesByExploitability
        api = model()

        def mocked_get(**options):
            assert '/crashes/exploitability' in options['url']
            return Response([
                {
                    'signature': 'FakeSignature',
                    'report_date': '2013-06-06',
                    'null_count': 0,
                    'none_count': 1,
                    'low_count': 2,
                    'medium_count': 3,
                    'high_count': 4
                }
            ])

        rget.side_effect = mocked_get
        r = api.get(batch=250, page=1)
        eq_(r[0]['signature'], 'FakeSignature')
        eq_(r[0]['report_date'], '2013-06-06')
        eq_(r[0]['null_count'], 0)
        eq_(r[0]['none_count'], 1)
        eq_(r[0]['low_count'], 2)
        eq_(r[0]['medium_count'], 3)
        eq_(r[0]['high_count'], 4)

    @mock.patch('requests.get')
    def test_exploitable_crashes_parameter_type_errors(self, rget):
        model = models.CrashesByExploitability
        api = model()

        def mocked_get(**options):
            assert '/crashes/exploitability' in options['url']
            return Response([
                {
                    'signature': 'FakeSignature',
                    'report_date': '2013-06-06',
                    'null_count': 0,
                    'none_count': 1,
                    'low_count': 2,
                    'medium_count': 3,
                    'high_count': 4
                }
            ])

        rget.side_effect = mocked_get
        assert_raises(
            models.ParameterTypeError,
            api.get,
            batch='xxx',
            page=1
        )
        assert_raises(
            models.ParameterTypeError,
            api.get,
            batch=250,
            page='xxx'
        )

        # but this should work
        api.get(batch='250', page='1')

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
    def test_fields(self, rget):
        model = models.Field
        api = model()

        def mocked_get(url, params, **options):
            assert '/field' in url

            ok_('name' in params)
            eq_(params['name'], 'my-field')

            return Response({
                'name': 'my-field',
                'product': 'WaterWolf',
                'transforms': {
                    'rule1': 'some notes about that rule',
                },
            })

        rget.side_effect = mocked_get
        r = api.get(name='my-field')
        eq_(r['product'], 'WaterWolf')
        eq_(r['name'], 'my-field')
        eq_(r['transforms'], {u'rule1': u'some notes about that rule'})

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
