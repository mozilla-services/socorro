import json
import os
import shutil
import tempfile
import datetime
import time
import random
import mock
import requests
from nose.tools import eq_, ok_

from django.test import TestCase
from django.core.cache import cache
from django.conf import settings

from crashstats.crashstats import models


class Response(object):
    def __init__(self, content=None, status_code=200):
        self.content = content
        self.status_code = status_code


class TestModels(TestCase):

    def setUp(self):
        super(TestModels, self).setUp()
        # thanks to settings_test.py
        assert settings.CACHE_MIDDLEWARE
        assert not settings.CACHE_MIDDLEWARE_FILES
        cache.clear()

    def tearDown(self):
        super(TestModels, self).tearDown()

    def test_kwargs_to_params_basics(self):
        """every model instance has a kwargs_to_params method which
        converts raw keyword arguments (a dict basically) to a cleaned up
        dict where every value has been type checked or filtered.
        """
        api = models.Correlations()
        self.assertRaises(
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

        # SignatureURLs requires certain things to be datetime.datetime
        api = models.SignatureURLs()
        inp = {
            'products': 'XXX',
            'signature': 'XXX',
            'start_date': datetime.date.today(),
            'end_date': datetime.datetime.today(),
        }
        self.assertRaises(
            models.ParameterTypeError,
            api.kwargs_to_params,
            inp
        )

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

    def test_kwargs_to_params_exceptions(self):
        """the method kwargs_to_params() can take extra care of some special
        cases"""
        # CrashesCountByDay takes a `signature` and a `start_date`
        api = models.CrashesCountByDay()
        now = datetime.datetime.utcnow()
        result = api.kwargs_to_params({
            'signature': 'X / Y + Z',
            'start_date': now
        })
        eq_(result['signature'], 'X / Y + Z')
        eq_(result['start_date'], now.isoformat())

        # CrashesFrequency takes a list of some parameters,
        # they get joined with a `+`
        api = models.CrashesFrequency()
        result = api.kwargs_to_params({
            'signature': 'XXX',
            'versions': [1, 2],
        })
        eq_(result['versions'], [1, 2])

    @mock.patch('requests.get')
    def test_middleware_url_building(self, rget):
        model = models.Search
        api = model()

        def mocked_get(url, params, **options):
            assert '/search/signatures' in url

            ok_('for' in params)
            ok_('products' in params)
            ok_('versions' in params)
            ok_('build_ids' in params)
            ok_('from' in params)
            ok_('reasons' in params)
            ok_('search_mode' in params)

            eq_(params['for'], 'sig with / and + and &')
            eq_(params['products'], ['WaterWolf', 'NightTrain'])
            eq_(params['from'], '2000-01-01T01:01:00')

            return Response('{"hits": [], "total": 0}')

        rget.side_effect = mocked_get
        api.get(
            terms='sig with / and + and &',
            products=['WaterWolf', 'NightTrain'],
            versions=['WaterWolf:11.1', 'NightTrain:42.0a1'],
            build_ids=1234567890,
            start_date=datetime.datetime(2000, 1, 1, 1, 1),
            reasons='some\nreason\0',
            search_mode='unsafe/search/mode'
        )

    @mock.patch('requests.get')
    def test_bugzilla_api(self, rget):
        model = models.BugzillaBugInfo

        api = model()

        def mocked_get(**options):
            assert options['url'].startswith(models.BugzillaAPI.base_url)
            return Response('{"bugs": [{"product": "mozilla.org"}]}')

        rget.side_effect = mocked_get
        info = api.get('747237', 'product')
        eq_(info['bugs'], [{u'product': u'mozilla.org'}])

        # prove that it's cached by default
        def new_mocked_get(**options):
            return Response('{"bugs": [{"product": "DIFFERENT"}]}')

        rget.side_effect = new_mocked_get
        info = api.get('747237', 'product')
        eq_(info['bugs'], [{u'product': u'mozilla.org'}])

        info = api.get('747238', 'product')
        eq_(info['bugs'], [{u'product': u'DIFFERENT'}])

    @mock.patch('requests.get')
    def test_current_versions(self, rget):
        model = models.CurrentVersions
        api = model()

        def mocked_get(**options):
            assert '/products' in options['url']
            return Response("""
                {"hits": {
                   "SeaMonkey": [{
                     "product": "SeaMonkey",
                     "throttle": "100.00",
                     "end_date": "2012-05-10 00:00:00",
                     "start_date": "2012-03-08 00:00:00",
                     "featured": true,
                     "version": "2.1.3pre",
                     "release": "Beta",
                     "id": 922}]
                  },
                  "products": ["SeaMonkey"]
                }
              """)

        rget.side_effect = mocked_get
        info = api.get()
        ok_(isinstance(info, list))
        ok_(isinstance(info[0], dict))
        eq_(info[0]['product'], 'SeaMonkey')

    @mock.patch('requests.get')
    def test_products_versions(self, rget):
        model = models.ProductsVersions
        api = model()

        def mocked_get(**options):
            assert '/products' in options['url']
            return Response("""
                {"hits": {
                   "WaterWolf": [{
                     "product": "WaterWolf",
                     "throttle": "100.00",
                     "end_date": "2012-05-10 00:00:00",
                     "start_date": "2012-03-08 00:00:00",
                     "featured": true,
                     "version": "2.1.3pre",
                     "release": "Beta",
                     "id": 922}]
                  },
                  "products": ["WaterWolf"]
                }
            """)

        rget.side_effect = mocked_get
        info = api.get()
        self.assertTrue(isinstance(info, dict))
        self.assertTrue('WaterWolf' in info)
        self.assertTrue(isinstance(info['WaterWolf'], list))
        self.assertEqual(info['WaterWolf'][0]['product'], 'WaterWolf')

    @mock.patch('requests.get')
    def test_current_products(self, rget):
        api = models.CurrentProducts()

        def mocked_get(url, params, **options):
            assert '/products' in url

            if 'versions' in params and params['versions'] == 'WaterWolf:2.1':
                return Response("""
                {
                  "hits": [
                    {
                        "is_featured": true,
                        "throttle": 1.0,
                        "end_date": "string",
                        "start_date": "integer",
                        "build_type": "string",
                        "product": "WaterWolf",
                        "version": "15.0.1",
                        "has_builds": true
                    }],
                    "total": "1"
                }
                """)

            else:
                return Response("""
                {
                  "hits": [
                    {
                        "sort": "1",
                        "default_version": "15.0.1",
                        "release_name": "firefox",
                        "rapid_release_version": "5.0",
                        "product_name": "NightTrain"
                    }],
                    "total": "1"
                }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        info = api.get()
        eq_(info['hits'][0]['product_name'], 'NightTrain')

        info = api.get(versions='WaterWolf:2.1')
        ok_('has_builds' in info['hits'][0])

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
                return Response("""
                    {
                      "hits": {
                        "WaterWolf:5.0a1": {
                          "2012-10-10": {
                            "product": "WaterWolf",
                            "adu": 1500,
                            "throttle": 0.5,
                            "crash_hadu": 13.0,
                            "version": "5.0a1",
                            "report_count": 195,
                            "date": "2012-10-08"
                          }
                        }
                      }
                    }
                    """)
            elif (
                'separated_by' in params and
                params['separated_by'] == 'os' and
                'os' in params and
                params['os'] == 'Linux'
            ):
                return Response("""
                    {
                      "hits": {
                        "WaterWolf:5.0a1:lin": {
                          "2012-10-08": {
                            "product": "WaterWolf",
                            "adu": 1500,
                            "throttle": 1.0,
                            "crash_hadu": 13.0,
                            "version": "5.0a1",
                            "report_count": 195,
                            "date": "2012-10-08",
                            "os": "Windows"
                          }
                        }
                      }
                    }
                    """)
            elif (
                'date_range_type' in params and
                params['date_range_type'] == 'build'
            ):
                return Response("""
                    {
                      "hits": {
                        "WaterWolf:5.0a1": {
                          "2012-10-08": {
                            "product": "NightTrain",
                            "adu": 4500,
                            "crash_hadu": 13.0,
                            "version": "5.0a1",
                            "report_count": 585,
                            "date": "2012-10-08"
                          }
                        }
                      }
                    }
                    """)
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

        response = api.get(
            product='WaterWolf',
            versions=['5.0a1'],
            from_date=week_ago,
            to_date=today,
            os='Linux',
            form_selection='by_os',
            separated_by='os',
            date_range_type='report'
        )

        for product in response['hits']:
            operating_system = product.split(":")[2]

        ok_('product_versions' not in response)
        ok_(response['hits'])
        eq_(operating_system, 'lin')

    def test_crashes_per_adu_parameter_type_error(self):
        model = models.CrashesPerAdu
        api = model()

        today = datetime.datetime.utcnow()

        self.assertRaises(
            models.ParameterTypeError,
            api.get,
            product='WaterWolf',
            versions=['5.0a1'],
            from_date='NOT A DATE',
            to_date=today,
            date_range_type='build'
        )

    @mock.patch('requests.get')
    def test_crashtrends(self, rget):
        api = models.CrashTrends()

        def mocked_get(url, params, **options):
            ok_('product' in params)

            if params['product'] == 'WaterWolf':
                return Response("""
                    {
                      "crashtrends": [{
                        "build_date": "2012-10-10",
                        "version_string": "5.0a1",
                        "product_version_id": 1,
                        "days_out": 6,
                        "report_count": 144,
                        "report_date": "2012-10-04",
                        "product_name": "WaterWolf"
                      },
                      {
                        "build_date": "2012-10-06",
                        "version_string": "5.0a1",
                        "product_version_id": 1,
                        "days_out": 2,
                        "report_count": 162,
                        "report_date": "2012-10-08",
                        "product_name": "WaterWolf"
                      },
                      {
                        "build_date": "2012-09-29",
                        "version_string": "5.0a1",
                        "product_version_id": 1,
                        "days_out": 5,
                        "report_count": 144,
                        "report_date": "2012-10-04",
                        "product_name": "WaterWolf"
                      }]
                    }
                    """)

            if params['product'] == 'NightTrain':
                return Response("""
                    {
                      "crashtrends": [{
                        "build_date": "2012-10-10",
                        "version_string": "5.0a1",
                        "product_version_id": 1,
                        "days_out": 6,
                        "report_count": 144,
                        "report_date": "2012-10-04",
                        "product_name": "NightTrain"
                      }]
                    }
                    """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        today = datetime.datetime.utcnow()
        week_ago = today - datetime.timedelta(days=7)
        response = api.get(
            start_date=today,
            end_date=week_ago,
            product='WaterWolf',
            version='5.0a1'
        )
        ok_('crashtrends' in response)

        response = api.get(
            start_date=today,
            end_date=week_ago,
            product='NightTrain',
            version='5.0a1'
        )
        for report in response['crashtrends']:
            product = report['product_name']

        eq_(product, 'NightTrain')

    @mock.patch('requests.get')
    def test_tcbs(self, rget):
        model = models.TCBS
        api = model()

        def mocked_get(**options):
            assert '/crashes/signatures' in options['url']
            # expect no os_name parameter encoded in the URL
            assert 'os' not in options['params']
            return Response("""
               {"crashes": [],
                "totalPercentage": 0,
                "start_date": "2012-05-10",
                "end_date": "2012-05-24",
                "totalNumberOfCrashes": 0}
              """)

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

    def test_tcbs_parameter_type_error(self):
        model = models.TCBS
        api = model()
        today = datetime.datetime.utcnow()
        # test for valid arguments
        self.assertRaises(
            models.ParameterTypeError,
            api.get,
            product='Thunderbird',
            version='12.0',
            crash_type='plugin',
            end_date='CLEARLY-NOT-A-DATE',
            date_range_type='report',
            limit=336
        )

        self.assertRaises(
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

            return Response("""
               {"crashes": [],
                "totalPercentage": 0,
                "start_date": "2012-05-10",
                "end_date": "2012-05-24",
                "totalNumberOfCrashes": 0}
              """)

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
            return Response("""
               {"crashes": [],
                "totalPercentage": 0,
                "start_date": "2012-05-10",
                "end_date": "2012-05-24",
                "totalNumberOfCrashes": 0}
              """)

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

    @mock.patch('requests.get')
    def test_report_list(self, rget):
        model = models.ReportList
        api = model()
        today = datetime.datetime.utcnow()

        def mocked_get(url, params, **options):
            assert '/report/list' in url

            ok_('from' in params)
            ok_(today.strftime('%Y-%m-%dT%H:%M:%S') in params['from'])

            return Response("""
                {
          "hits": [
            {
              "product": "Fennec",
              "os_name": "Linux",
              "uuid": "5e30f10f-cd5d-4b13-9dbc-1d1e62120524",
              "many_others": "snipped out"
            }],
          "total": 333
          }
              """)

        rget.side_effect = mocked_get

        # Missing signature param
        self.assertRaises(
            models.RequiredParameterError,
            api.get,
            products='Fennec',
            start_day=today,
            result_number=250,
            result_offset=0,
            start_date=today,
            end_date=today,
        )

        # Missing signature param
        self.assertRaises(
            models.RequiredParameterError,
            api.get,
            signature='Pickle::ReadBytes',
            products='Fennec',
            start_day=today,
            result_number=250,
            result_offset=0,
        )

        r = api.get(
            signature='Pickle::ReadBytes',
            products='Fennec',
            start_day=today,
            result_number=250,
            result_offset=0,
            start_date=today,
            end_date=today,
        )
        ok_(r['total'])
        ok_(r['hits'])

    def test_report_list_parameter_type_error(self):
        model = models.ReportList
        api = model()

        today = datetime.date.today()
        # start_date and end_date are datetime.date instances,
        # not datetime.datetime
        self.assertRaises(
            models.RequiredParameterError,
            api.get,
            products='Fennec',
            start_day=today,
            result_number=250,
            result_offset=0,
            start_date=today,
            end_date=today,
        )

    @mock.patch('requests.get')
    def test_comments_by_signature(self, rget):
        model = models.CommentsBySignature
        api = model()

        def mocked_get(url, params, **options):
            assert '/crashes/comments' in url, url

            ok_('products' in params)
            ok_('WaterWolf' in params['products'])

            ok_('versions' in params)
            ok_('WaterWolf:19.0a1' in params['versions'])

            ok_('build_ids' in params)
            ok_('1234567890' in params['build_ids'])

            ok_('reasons' in params)
            ok_('SEG/FAULT' in params['reasons'])

            return Response("""
            {"hits": [
                  {
                  "date_processed": "2000-01-01T00:00:01",
                  "uuid": "1234abcd",
                  "user_comment": "hello guys!",
                  "email": "hello@example.com"
                }],
              "total": 1
              }
            """)

        rget.side_effect = mocked_get
        r = api.get(
            signature='mysig',
            products=['WaterWolf'],
            versions=['WaterWolf:19.0a1'],
            build_ids='1234567890',
            reasons='SEG/FAULT'
        )
        ok_(r['hits'])
        ok_(r['total'])

    @mock.patch('requests.get')
    def test_processed_crash(self, rget):
        model = models.ProcessedCrash
        api = model()

        def mocked_get(url, params, **options):
            assert '/crash_data' in url
            ok_('datatype' in params)
            eq_(params['datatype'], 'processed')

            return Response("""
            {
              "product": "WaterWolf",
              "uuid": "7c44ade2-fdeb-4d6c-830a-07d302120525",
              "version": "13.0",
              "build": "20120501201020",
              "ReleaseChannel": "beta",
              "os_name": "Windows NT",
              "date_processed": "2012-05-25 11:35:57",
              "success": true,
              "signature": "CLocalEndpointEnumerator::OnMediaNotific",
              "addons": [
                [
                  "testpilot@labs.mozilla.com",
                  "1.2.1"
                ],
                [
                  "{972ce4c6-7e08-4474-a285-3208198ce6fd}",
                  "13.0"
                ]
              ]
            }
            """)

        rget.side_effect = mocked_get
        r = api.get(crash_id='7c44ade2-fdeb-4d6c-830a-07d302120525')
        ok_(r['product'])

    @mock.patch('requests.get')
    def test_unredacted_crash(self, rget):
        model = models.UnredactedCrash
        api = model()

        def mocked_get(url, params, **options):
            assert '/crash_data' in url
            ok_('datatype' in params)
            eq_(params['datatype'], 'unredacted')

            return Response("""
            {
              "product": "WaterWolf",
              "uuid": "7c44ade2-fdeb-4d6c-830a-07d302120525",
              "version": "13.0",
              "build": "20120501201020",
              "ReleaseChannel": "beta",
              "os_name": "Windows NT",
              "date_processed": "2012-05-25 11:35:57",
              "success": true,
              "signature": "CLocalEndpointEnumerator::OnMediaNotific",
              "exploitability": "Sensitive stuff",
              "addons": [
                [
                  "testpilot@labs.mozilla.com",
                  "1.2.1"
                ],
                [
                  "{972ce4c6-7e08-4474-a285-3208198ce6fd}",
                  "13.0"
                ]
              ]
            }
            """)

        rget.side_effect = mocked_get
        r = api.get(crash_id='7c44ade2-fdeb-4d6c-830a-07d302120525')
        ok_(r['product'])
        ok_(r['exploitability'])

    @mock.patch('requests.get')
    def test_search(self, rget):
        model = models.Search
        api = model()

        def mocked_get(**options):
            assert 'search/signatures' in options['url'], options['url']
            return Response("""
            {"hits": [
                  {
                  "count": 586,
                  "signature": "nsASDOMWindowEnumerator::GetNext()",
                  "numcontent": 0,
                  "is_windows": 586,
                  "is_linux": 0,
                  "numplugin": 0,
                  "is_mac": 0,
                  "numhang": 0
                }],
              "total": 123
              }
            """)

        rget.side_effect = mocked_get
        r = api.get()
        ok_(r['hits'])
        ok_(r['total'])

        now = datetime.datetime.utcnow()
        lastweek = now - datetime.timedelta(days=7)
        r = api.get(
            products=['WaterWolf'],
            versions=['WaterWolf:1.0a1'],
            start_date=lastweek,
            end_date=now
        )
        ok_(r['hits'])
        ok_(r['total'])

    @mock.patch('requests.post')
    def test_bugs(self, rpost):
        model = models.Bugs
        api = model()

        def mocked_post(**options):
            assert '/bugs/' in options['url'], options['url']
            assert options['data'] == {'signatures': 'Pickle::ReadBytes'}
            return Response('{"hits": ["123456789"]}')

        rpost.side_effect = mocked_post
        r = api.get(signatures='Pickle::ReadBytes')
        ok_(r['hits'])

    def test_bugs_called_without_signatures(self):
        model = models.Bugs
        api = model()

        self.assertRaises(ValueError, api.get)

    @mock.patch('requests.post')
    def test_bugs_no_caching(self, rpost):
        model = models.Bugs
        api = model()

        calls = []  # anything mutable

        def mocked_post(**options):
            calls.append(options['data'])
            assert '/bugs/' in options['url'], options['url']
            assert options['data'] == {'signatures': 'Pickle::ReadBytes'}
            return Response('{"hits": ["123456789"]}')

        rpost.side_effect = mocked_post
        r = api.get(signatures='Pickle::ReadBytes')
        eq_(r['hits'], [u'123456789'])

        # Change the response

        def mocked_post_v2(**options):
            calls.append(options['data'])
            assert '/bugs/' in options['url'], options['url']
            assert options['data'] == {'signatures': 'Pickle::ReadBytes'}
            return Response('{"hits": ["987654310"]}')

        rpost.side_effect = mocked_post_v2
        r = api.get(signatures='Pickle::ReadBytes')
        eq_(len(calls), 2)
        eq_(r['hits'], [u'987654310'])

    @mock.patch('requests.post')
    def test_signatures_by_bugs(self, rpost):
        model = models.SignaturesByBugs
        api = model()

        def mocked_post(**options):
            assert '/bugs/' in options['url'], options['url']
            assert options['data'] == {'bug_ids': '123456789'}
            return Response('{"hits": {"signatures": "Pickle::ReadBytes"}}')

        rpost.side_effect = mocked_post
        r = api.get(bug_ids='123456789')
        ok_(r['hits'])

    def test_sigs_by_bugs_called_without_bug_ids(self):
        model = models.SignaturesByBugs
        api = model()

        self.assertRaises(ValueError, api.get)

    @mock.patch('requests.post')
    def test_sigs_by_bugs_no_caching(self, rpost):
        model = models.SignaturesByBugs
        api = model()

        calls = []  # anything mutable

        def mocked_post(**options):
            calls.append(options['data'])
            assert '/bugs/' in options['url'], options['url']
            assert options['data'] == {'bug_ids': '123456789'}
            return Response('{"hits": {"signatures": ["Pickle::ReadBytes"]}}')

        rpost.side_effect = mocked_post
        r = api.get(bug_ids='123456789')
        eq_(r['hits'], {'signatures': ['Pickle::ReadBytes']})

        # Change the response

        def mocked_post_v2(**options):
            calls.append(options['data'])
            assert '/bugs/' in options['url'], options['url']
            assert options['data'] == {'bug_ids': '987654310'}
            return Response('{"hits": {"signatures": ["Pickle::ReadBytes"]}}')

        rpost.side_effect = mocked_post_v2
        r = api.get(bug_ids='987654310')
        eq_(len(calls), 2)
        eq_(r['hits'], {u'signatures': ["Pickle::ReadBytes"]})

    @mock.patch('requests.get')
    def test_signature_trend(self, rget):
        model = models.SignatureTrend
        api = model()

        def mocked_get(url, params, **options):
            assert 'crashes/signature_history' in url, url
            return Response("""
            {
                "hits": [],
                "total": 0
            }
            """)

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

    @mock.patch('requests.get')
    def test_signature_summary(self, rget):
        model = models.SignatureSummary
        api = model()

        def mocked_get(**options):
            assert 'signaturesummary' in options['url'], options['url']
            return Response("""
            [
              {
                "version_string": "12.0",
                "percentage": "48.440",
                "report_count": 52311,
                "product_name": "WaterWolf"
              },
              {
                "version_string": "13.0b4",
                "percentage": "9.244",
                "report_count": 9983,
                "product_name": "WaterWolf"
              }
            ]
            """)

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        yesterday = today - datetime.timedelta(days=10)
        r = api.get(
            report_type='products',
            signature='Pickle::ReadBytes',
            start_date=yesterday,
            end_date=today,
            versions='WaterWolf:19.0',
        )
        ok_(r[0]['version_string'])
        r = api.get(
            report_type='products',
            signature='Pickle::ReadBytes',
            start_date=yesterday,
            end_date=today,
        )
        ok_(r[0]['version_string'])

    @mock.patch('requests.get')
    def test_status(self, rget):
        def mocked_get(**options):
            assert 'status' in options['url'], options['url']
            return Response("""
                {
                    "breakpad_revision": "1035",
                    "hits": [
                        {
                            "date_oldest_job_queued":
                                "2012-09-28T20:39:33+00:00",
                            "date_recently_completed":
                                "2012-09-28T20:40:00+00:00",
                            "processors_count": 1,
                            "avg_wait_sec": 16.407,
                            "waiting_job_count": 56,
                            "date_created": "2012-09-28T20:40:02+00:00",
                            "id": 410655,
                            "avg_process_sec": 0.914149
                        },
                        {
                            "date_oldest_job_queued":
                                "2012-09-28T20:34:33+00:00",
                            "date_recently_completed":
                                "2012-09-28T20:35:00+00:00",
                            "processors_count": 1,
                            "avg_wait_sec": 13.8293,
                            "waiting_job_count": 48,
                            "date_created": "2012-09-28T20:35:01+00:00",
                            "id": 410654,
                            "avg_process_sec": 1.24177
                        },
                        {
                            "date_oldest_job_queued":
                                "2012-09-28T20:29:32+00:00",
                            "date_recently_completed":
                                "2012-09-28T20:30:01+00:00",
                            "processors_count": 1,
                            "avg_wait_sec": 14.8803,
                            "waiting_job_count": 1,
                            "date_created": "2012-09-28T20:30:01+00:00",
                            "id": 410653,
                            "avg_process_sec": 1.19637
                        }
                    ],
                    "total": 12,
                    "socorro_revision":
                        "017d7b3f7042ce76bc80949ae55b41d1e915ab62"
                }
            """)

        rget.side_effect = mocked_get

        response = models.Status().get('3')
        ok_(response['hits'])

    @mock.patch('requests.get')
    def test_daily_builds(self, rget):
        model = models.DailyBuilds
        api = model()

        def mocked_get(**options):
            assert '/product' in options['url']
            return Response("""
                [
                  {
                    "product": "SeaMonkey",
                    "repository": "dev",
                    "buildid": 20120625000007,
                    "beta_number": null,
                    "platform": "Mac OS X",
                    "version": "5.0a1",
                    "date": "2012-06-25",
                    "build_type": "Nightly"
                  },
                  {
                    "product": "SeaMonkey",
                    "repository": "dev",
                    "buildid": 20120625000007,
                    "beta_number": null,
                    "platform": "Windows",
                    "version": "5.0a1",
                    "date": "2012-06-25",
                    "build_type": "Nightly"
                  }
                ]
            """)

        rget.side_effect = mocked_get
        r = api.get(product='SeaMonkey')
        eq_(r[0]['product'], 'SeaMonkey')
        ok_(r[0]['date'])
        ok_(r[0]['version'])

    @mock.patch('requests.get')
    def test_paireduuid_crashes(self, rget):
        model = models.CrashPairsByCrashId
        api = model()

        def mocked_get(**options):
            assert '/crashes/paireduuid' in options['url']
            return Response("""
                {
                    "hits": [
                        {
                            "uuid": "e8820616-1462-49b6-9784-e99a32120201"
                        }
                    ],
                    "total": 1
                }
            """)

        rget.side_effect = mocked_get
        r = api.get(uuid='1234', hang_id='4321')
        eq_(r['hits'][0]['uuid'], 'e8820616-1462-49b6-9784-e99a32120201')

    @mock.patch('requests.get')
    def test_exploitable_crashes(self, rget):
        model = models.CrashesByExploitability
        api = model()

        def mocked_get(**options):
            assert '/crashes/exploitability' in options['url']
            return Response("""
                [
                  {
                    "signature": "FakeSignature",
                    "report_date": "2013-06-06",
                    "null_count": 0,
                    "none_count": 1,
                    "low_count": 2,
                    "medium_count": 3,
                    "high_count": 4
                  }
                ]
            """)

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
            return Response("""
                [
                  {
                    "signature": "FakeSignature",
                    "report_date": "2013-06-06",
                    "null_count": 0,
                    "none_count": 1,
                    "low_count": 2,
                    "medium_count": 3,
                    "high_count": 4
                  }
                ]
            """)

        rget.side_effect = mocked_get
        self.assertRaises(
            models.ParameterTypeError,
            api.get,
            batch='xxx',
            page=1
        )
        self.assertRaises(
            models.ParameterTypeError,
            api.get,
            batch=250,
            page='xxx'
        )

        # but this should work
        api.get(batch='250', page='1')

    @mock.patch('requests.get')
    def test_raw_crash(self, rget):
        model = models.RawCrash
        api = model()

        def mocked_get(url, params, **options):
            assert '/crash_data/' in url
            return Response("""
                {
                  "InstallTime": "1339289895",
                  "FramePoisonSize": "4096",
                  "Theme": "classic/1.0",
                  "Version": "5.0a1",
                  "Email": "socorro-123@restmail.net",
                  "Vendor": "Mozilla"
                  }
            """)

        rget.side_effect = mocked_get
        r = api.get(crash_id='some-crash-id')
        eq_(r['Vendor'], 'Mozilla')

    @mock.patch('requests.put')
    def test_put_featured_versions(self, rput):
        model = models.ReleasesFeatured
        api = model()

        def mocked_put(url, **options):
            assert '/releases/featured/' in url
            data = options['data']
            eq_(data['WaterWolf'], '18.0,19.0')
            eq_(data['NightTrain'], '1,2')
            return Response("true")

        rput.side_effect = mocked_put
        r = api.put(**{'WaterWolf': ['18.0', '19.0'],
                       'NightTrain': ['1', '2']})
        eq_(r, True)

    @mock.patch('requests.get')
    def test_correlations(self, rget):
        model = models.Correlations
        api = model()

        def mocked_get(url, params, **options):
            assert '/correlations' in url

            ok_('report_type' in params)
            eq_(params['report_type'], 'core-counts')

            return Response("""
            {
                "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                "count": 13,
                "load": "36% (4/11) vs.  26% (47/180) amd64 with 2 cores"
            }
        """)

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

            return Response("""
            {
                "hits": ["FakeSignature1",
                         "FakeSignature2"],
                "total": 2
            }
        """)

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

            return Response("""
            {
                "name": "my-field",
                "product": "WaterWolf",
                "transforms": {
                    "rule1": "some notes about that rule"
                }
            }
        """)

        rget.side_effect = mocked_get
        r = api.get(name='my-field')
        eq_(r['product'], 'WaterWolf')
        eq_(r['name'], 'my-field')
        eq_(r['transforms'], {u'rule1': u'some notes about that rule'})

    @mock.patch('requests.get')
    def test_skiplist_get(self, rget):
        model = models.SkipList
        api = model()

        def mocked_get(url, params, **options):
            assert '/skiplist/' in url
            return Response("""
            {
                "hits": [
                    {"category": "prefix", "rule": "Bar"},
                    {"category": "prefix", "rule": "Foo"},
                    {"category": "suffix", "rule": "Bar"},
                    {"category": "suffix", "rule": "Foo"}
                ],
                "total": 4
            }
            """)

        rget.side_effect = mocked_get

        r = api.get()
        expect = {
            'hits': [
                {'category': 'prefix', 'rule': 'Bar'},
                {'category': 'prefix', 'rule': 'Foo'},
                {'category': 'suffix', 'rule': 'Bar'},
                {'category': 'suffix', 'rule': 'Foo'}
            ],
            'total': 4
        }
        eq_(r, expect)

    @mock.patch('requests.post')
    def test_skiplist_post(self, rpost):
        model = models.SkipList
        api = model()

        def mocked_post(url, **options):
            assert '/skiplist/' in url, url
            ok_(options['data'].get('category'))
            ok_(options['data'].get('rule'))
            return Response("true")

        rpost.side_effect = mocked_post
        r = api.post(category='suffix', rule='Foo')
        eq_(r, True)

    @mock.patch('requests.delete')
    def test_skiplist_delete(self, rdelete):
        model = models.SkipList
        api = model()

        def mocked_delete(url, params, **options):
            assert '/skiplist' in url, url

            ok_('category' in params)
            eq_(params['category'], 'suffix')

            ok_('rule' in params)
            eq_(params['rule'], 'Foo')

            return Response("true")

        rdelete.side_effect = mocked_delete
        r = api.delete(category='suffix', rule='Foo')
        eq_(r, True)


class TestModelsWithFileCaching(TestCase):

    def setUp(self):
        super(TestModelsWithFileCaching, self).setUp()
        self.tempdir = tempfile.mkdtemp()
        # Using CACHE_MIDDLEWARE_FILES is mainly for debugging but good to test
        self._cache_middleware = settings.CACHE_MIDDLEWARE
        self._cache_middleware_files = settings.CACHE_MIDDLEWARE_FILES
        settings.CACHE_MIDDLEWARE = True
        settings.CACHE_MIDDLEWARE_FILES = self.tempdir
        cache.clear()

    def tearDown(self):
        super(TestModelsWithFileCaching, self).tearDown()
        settings.CACHE_MIDDLEWARE = self._cache_middleware
        settings.CACHE_MIDDLEWARE_FILES = self._cache_middleware_files
        if os.path.isdir(self.tempdir):
            shutil.rmtree(self.tempdir)

    @mock.patch('requests.get')
    def test_bugzilla_api_to_file(self, rget):
        model = models.BugzillaBugInfo

        api = model()

        def mocked_get(**options):
            assert options['url'].startswith(models.BugzillaAPI.base_url)
            return Response('{"bugs": [{"product": "mozilla.org"}]}')

        rget.side_effect = mocked_get
        info = api.get('747237', 'product')
        eq_(info['bugs'], [{u'product': u'mozilla.org'}])

        # prove that it's cached by default
        def new_mocked_get(**options):
            return Response('{"bugs": [{"product": "DIFFERENT"}]}')

        rget.side_effect = new_mocked_get
        info = api.get('747237', 'product')
        eq_(info['bugs'], [{u'product': u'mozilla.org'}])

        info = api.get('747238', 'product')
        eq_(info['bugs'], [{u'product': u'DIFFERENT'}])

    def _get_cached_file(self, in_):
        files = []
        for f in os.listdir(in_):
            path = os.path.join(in_, f)
            if os.path.isdir(path):
                files.extend(self._get_cached_file(path))
            else:
                files.append(path)
        return files

    @mock.patch('crashstats.crashstats.models.time.time')
    @mock.patch('requests.get')
    def test_get_current_version_cache_invalidation(self, rget, mocked_time):
        def mocked_get(**options):
            assert '/products/' in options['url']
            return Response("""
                {"hits": {
                   "SeaMonkey": [{
                     "product": "SeaMonkey",
                     "throttle": "100.00",
                     "end_date": "2012-05-10 00:00:00",
                     "start_date": "2012-03-08 00:00:00",
                     "featured": true,
                     "version": "2.1.3pre",
                     "release": "Beta",
                     "id": 922}]
                  },
                  "products": ["SeaMonkey"]
                }
              """)
        rget.side_effect = mocked_get

        assert not self._get_cached_file(self.tempdir)

        # the first time, we rely on the mocket request.get
        model = models.CurrentVersions
        api = model()
        info = api.get()
        eq_(info[0]['product'], 'SeaMonkey')

        json_file = self._get_cached_file(self.tempdir)[0]
        assert 'hits' in json.loads(open(json_file).read())

        # if we now loose the memcache/locmem
        from django.core.cache import cache
        cache.clear()

        info = api.get()
        eq_(info[0]['product'], 'SeaMonkey')

        now = time.time()
        extra = models.CurrentVersions.cache_seconds

        def my_time():
            return now + extra

        # now we're going to mess with the modification time so that
        # the cache file gets wiped
        rget.side_effect = mocked_get

        mocked_time.side_effect = my_time
        info = api.get()
        eq_(info[0]['product'], 'SeaMonkey')

    @mock.patch('requests.get')
    def test_signature_urls(self, rget):
        model = models.SignatureURLs
        api = model()

        def mocked_get(url, params, **options):
            assert '/signatureurls' in url
            ok_('versions' in params)
            ok_('WaterWolf:1.0' in params['versions'])

            return Response("""{
                "hits": [{"url": "http://farm.ville", "crash_count":123}],
                "total": 1
            }
            """)

        rget.side_effect = mocked_get
        today = datetime.datetime.utcnow()
        response = api.get(
            signature='FakeSignature',
            products=['WaterWolf'],
            versions=['WaterWolf:1.0'],
            start_date=today - datetime.timedelta(days=1),
            end_date=today,
        )
        eq_(response['total'], 1)
        eq_(response['hits'][0], {'url': 'http://farm.ville',
                                  'crash_count': 123})

    @mock.patch('requests.get')
    def test_massive_querystring_caching(self, rget):
        # doesn't actually matter so much what API model we use
        # see https://bugzilla.mozilla.org/show_bug.cgi?id=803696
        model = models.BugzillaBugInfo
        api = model()

        def mocked_get(**options):
            assert options['url'].startswith(models.BugzillaAPI.base_url)
            return Response('{"bugs": [{"product": "mozilla.org"}]}')

        rget.side_effect = mocked_get
        bugnumbers = [str(random.randint(10000, 100000)) for __ in range(100)]
        info = api.get(bugnumbers, 'product')
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
            return Response('{"bugs": [{"product": "mozilla.org"}]}')

        rget.side_effect = mocked_get
        info = api.get(['987654'], 'product')
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
        self.assertRaises(
            requests.ConnectionError,
            api.get,
            ['987654'],
            'product'
        )
        ok_(len(calls) > 3)  # had to attempt more than 3 times
        ok_(len(sleeps) > 2)  # had to sleep more than 2 times
