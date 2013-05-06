import re
import csv
import json
from cStringIO import StringIO
import mock
import datetime
from nose.tools import eq_, ok_
from django.test import TestCase
from django.test.utils import override_settings
from django.test.client import RequestFactory
from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.models import User
from crashstats.crashstats import models


class Response(object):
    def __init__(self, content=None, status_code=200):
        self.content = content
        self.status_code = status_code


class RobotsTestViews(TestCase):

    @override_settings(ENGAGE_ROBOTS=True)
    def test_robots_txt(self):
        url = '/robots.txt'
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/plain')
        ok_('Allow: /' in response.content)

    @override_settings(ENGAGE_ROBOTS=False)
    def test_robots_txt_disengage(self):
        url = '/robots.txt'
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/plain')
        ok_('Disallow: /' in response.content)


class BaseTestViews(TestCase):

    @mock.patch('requests.get')
    def setUp(self, rget):
        super(BaseTestViews, self).setUp()

        # checking settings.CACHES isn't as safe as `cache.__class__`
        if 'LocMemCache' not in cache.__class__.__name__:
            raise ImproperlyConfigured(
                'The tests requires that you use LocMemCache when running'
            )

        # we do this here so that the current/versions thing
        # is cached since that's going to be called later
        # in every view more or less
        def mocked_get(url, **options):
            now = datetime.datetime.utcnow()
            now = now.replace(microsecond=0).isoformat()
            if 'products/' in url:
                return Response("""
                    {"products": [
                       "Firefox",
                       "Thunderbird",
                       "Camino"
                     ],
                     "hits": {
                      "Firefox": [
                       {"product": "Firefox",
                        "throttle": "100.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08T00:00:00",
                        "featured": true,
                        "version": "19.0",
                        "release": "Beta",
                        "id": 922},
                       {"product": "Firefox",
                        "throttle": "100.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08T00:00:00",
                        "featured": true,
                        "version": "18.0",
                        "release": "Stable",
                        "id": 920},
                       {"product": "Firefox",
                        "throttle": "100.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08T00:00:00",
                        "featured": true,
                        "version": "20.0",
                        "release": "Nightly",
                        "id": 923}
                      ],
                      "Thunderbird":[
                        {"product": "Thunderbird",
                        "throttle": "100.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08T00:00:00",
                        "featured": true,
                        "version": "18.0",
                        "release": "Aurora",
                        "id": 924},
                       {"product": "Thunderbird",
                        "throttle": "100.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08T00:00:00",
                        "featured": true,
                        "version": "19.0",
                        "release": "Nightly",
                        "id": 925}
                     ],
                     "Camino": [
                       {"product": "Camino",
                        "throttle": "99.00",
                        "end_date": "%(end_date)s",
                        "start_date": "2012-03-08T00:00:00",
                        "featured": true,
                        "version": "9.5",
                        "release": "Alpha",
                        "id": 921}
                     ]
                   }
                 }
                      """ % {'end_date': now})
            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        from crashstats.crashstats.models import CurrentVersions
        api = CurrentVersions()
        api.get()

    def tearDown(self):
        super(BaseTestViews, self).tearDown()
        cache.clear()


class TestViews(BaseTestViews):

    @mock.patch('requests.get')
    def test_handler500(self, rget):
        root_urlconf = __import__(
            settings.ROOT_URLCONF,
            globals(),
            locals(),
            ['urls'],
            -1
        )
        # ...so that we can access the 'handler500' defined in there
        par, end = root_urlconf.handler500.rsplit('.', 1)
        # ...which is an importable reference to the real handler500 function
        views = __import__(par, globals(), locals(), [end], -1)
        # ...and finally we have the handler500 function at hand
        handler500 = getattr(views, end)

        # to make a mock call to the django view functions you need a request
        fake_request = RequestFactory().request(**{'wsgi.input': None})
        # Need a fake user for the persona bits on crashstats_base
        fake_request.user = {}
        fake_request.user['is_active'] = False

        # the reason for first causing an exception to be raised is because
        # the handler500 function is only called by django when an exception
        # has been raised which means sys.exc_info() is something.
        try:
            raise NameError('sloppy code')
        except NameError:
            # do this inside a frame that has a sys.exc_info()
            response = handler500(fake_request)
            eq_(response.status_code, 500)
            ok_('Internal Server Error' in response.content)
            ok_('id="products_select"' not in response.content)

    def test_handler404(self):
        url = reverse('crashstats.home', args=('Unknown',))
        response = self.client.get(url)
        eq_(response.status_code, 404)
        ok_('Page not Found' in response.content)
        ok_('id="products_select"' not in response.content)

    def test_homepage_redirect(self):
        response = self.client.get('/')
        eq_(response.status_code, 302)
        destination = reverse('crashstats.home',
                              args=[settings.DEFAULT_PRODUCT])
        ok_(destination in response['Location'])

    def test_legacy_query_redirect(self):
        response = self.client.get('/query/query?foo=bar')
        redirect_code = settings.PERMANENT_LEGACY_REDIRECTS and 301 or 302
        eq_(response.status_code, redirect_code)
        ok_(reverse('crashstats.query') + '?foo=bar' in response['Location'])

    @mock.patch('requests.get')
    def test_buginfo(self, rget):
        url = reverse('crashstats.buginfo')

        def mocked_get(url, **options):
            if 'bug?id=' in url:
                return Response('{"bugs": [{"product": "allizom.org"}]}')

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 400)

        response = self.client.get(url, {'bug_ids': '123,456'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'include_fields': 'product'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'bug_ids': ' 123, 456 ',
                                         'include_fields': ' product'})
        eq_(response.status_code, 200)

        struct = json.loads(response.content)
        ok_(struct['bugs'])
        eq_(struct['bugs'][0]['product'], 'allizom.org')

    @mock.patch('requests.get')
    def test_home(self, rget):
        url = reverse('crashstats.home', args=('Firefox',))

        def mocked_get(url, **options):
            if 'products' in url and not 'version' in url:
                return Response("""
                    {
                        "products": [
                            "Firefox"
                        ],
                        "hits": {
                            "Firefox": [{
                            "featured": true,
                            "throttle": 100.0,
                            "end_date": "2012-11-27",
                            "product": "Firefox",
                            "release": "Nightly",
                            "version": "19.0",
                            "has_builds": true,
                            "start_date": "2012-09-25"
                            }]
                        },
                        "total": 1
                    }
                """)
            elif 'products' in url:
                return Response("""
                    {
                        "hits": [{
                            "is_featured": true,
                            "throttle": 100.0,
                            "end_date": "2012-11-27",
                            "product": "Firefox",
                            "build_type": "Nightly",
                            "version": "19.0",
                            "has_builds": true,
                            "start_date": "2012-09-25"
                        }],
                        "total": 1
                    }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 200)

        # Testing with unknown product
        url = reverse('crashstats.home', args=('InternetExplorer',))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        # Testing with unknown version for product
        url = reverse('crashstats.home', args=('Firefox', '99'))
        response = self.client.get(url)
        eq_(response.status_code, 404)

         # Testing with valid version for product
        url = reverse('crashstats.home', args=('Firefox', '19.0'))
        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_frontpage_json(self, rget):
        url = reverse('crashstats.frontpage_json')

        def mocked_get(url, **options):
            if 'crashes/daily' in url:
                return Response("""
                    {
                      "hits": {
                        "Firefox:19.0": {
                          "2012-10-08": {
                            "product": "Firefox",
                            "adu": 30000,
                            "crash_hadu": 71.099999999999994,
                            "version": "19.0",
                            "report_count": 2133,
                            "date": "2012-10-08"
                          },
                          "2012-10-02": {
                            "product": "Firefox",
                            "adu": 30000,
                            "crash_hadu": 77.299999999999997,
                            "version": "19.0",
                            "report_count": 2319,
                            "date": "2012-10-02"
                         }
                        }
                      }
                    }
                    """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {'product': 'Firefox'})
        eq_(response.status_code, 200)

        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        ok_(struct['product_versions'])
        eq_(struct['count'], 1)

    @mock.patch('requests.get')
    def test_frontpage_json_bad_request(self, rget):
        url = reverse('crashstats.frontpage_json')

        def mocked_get(url, **options):
            assert 'crashes/daily' in url, url
            if 'product/Firefox' in url:
                return Response("""
                    {
                      "hits": {
                        "Firefox:19.0": {
                          "2012-10-08": {
                            "product": "Firefox",
                            "adu": 30000,
                            "crash_hadu": 71.099999999999994,
                            "version": "19.0",
                            "report_count": 2133,
                            "date": "2012-10-08"
                          },
                          "2012-10-02": {
                            "product": "Firefox",
                            "adu": 30000,
                            "crash_hadu": 77.299999999999997,
                            "version": "19.0",
                            "report_count": 2319,
                            "date": "2012-10-02"
                         }
                        }
                      }
                    }
                    """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {'product': 'Neverheardof'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'versions': '999.1'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'Firefox',
            'versions': '99.9'  # mismatch
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'Firefox',
            'versions': '19.0'
        })
        eq_(response.status_code, 200)

        response = self.client.get(url, {
            'product': 'Firefox',
            'duration': 'xxx'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'Firefox',
            'duration': '-100'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'Firefox',
            'duration': '10'
        })
        eq_(response.status_code, 200)

        response = self.client.get(url, {
            'product': 'Firefox',
            'date_range_type': 'junk'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'product': 'Firefox',
            'date_range_type': 'build'
        })
        eq_(response.status_code, 200)

        response = self.client.get(url, {
            'product': 'Firefox',
            'date_range_type': 'report'
        })
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_products_list(self, rget):
        url = reverse('crashstats.products_list')

        def mocked_get(url, **options):
            if 'products' in url:
                return Response("""
                {
                  "products": [
                    "Firefox",
                    "Fennec"
                  ],
                  "hits": [
                    {
                        "sort": "1",
                        "default_version": "15.0.1",
                        "release_name": "firefox",
                        "rapid_release_version": "5.0",
                        "product_name": "Firefox"
                    },
                    {
                        "sort": "3",
                        "default_version": "10.0.6esr",
                        "release_name": "mobile",
                        "rapid_release_version": "5.0",
                        "product_name": "Fennec"
                    }],
                    "total": "2"
                }
                """)

        rget.side_effect = mocked_get

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @mock.patch('requests.get')
    def test_crash_trends(self, rget):
        url = reverse('crashstats.crash_trends', args=('Firefox',))
        unkown_product_url = reverse('crashstats.crash_trends',
                                     args=('NotKnown',))

        def mocked_get(**options):
            if 'products' in options['url']:
                return Response("""
                    {
                        "products": ["WaterWolf"],
                        "hits": [
                            {
                                "product": "WaterWolf",
                                "version": "5.0a1",
                                "release": "Release",
                                "throttle": 10.0
                            }
                        ],
                        "total": "1"
                    }
                    """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Nightly Crash Trends For Firefox' in response.content)

        response = self.client.get(unkown_product_url)
        eq_(response.status_code, 404)

    @mock.patch('requests.get')
    def test_crashtrends_versions_json(self, rget):
        url = reverse('crashstats.crashtrends_versions_json')

        def mocked_get(**options):
            if 'products' in options['url']:
                return Response("""
                    {
                      "hits": [
                        {
                            "sort": "1",
                            "default_version": "5.0a1",
                            "release_name": "waterwolf",
                            "rapid_release_version": "5.0",
                            "product_name": "WaterWolf"
                        }],
                        "total": "1"
                    }
                    """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {'product': 'Firefox'})
        ok_('application/json' in response['content-type'])
        eq_(response.status_code, 200)
        ok_(response.content, ['20.0'])

        response = self.client.get(url, {'product': 'Thunderbird'})
        eq_(response.status_code, 200)
        ok_(response.content, ['18.0', '19.0'])

        response = self.client.get(url, {'product': 'Unknown'})
        ok_(response.content, [])

    @mock.patch('requests.get')
    def test_crashtrends_json(self, rget):
        url = reverse('crashstats.crashtrends_json')

        def mocked_get(url, **options):
            ok_('/start_date/2012-10-01/' in url)
            ok_('/end_date/2012-10-10/' in url)
            if 'crashtrends/' in url:
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

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {
            'product': 'Firefox',
            'version': '20.0',
            'start_date': '2012-10-01',
            'end_date': '2012-10-10'
        })
        ok_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        eq_(struct['total'], 2)

        # Test with product that does not have a nightly
        response = self.client.get(url, {
            'product': 'Camino',
            'version': '9.5',
            'start_date': '2012-10-01',
            'end_date': '2012-10-10'
        })
        ok_(response.status_code, 400)
        ok_('text/html' in response['content-type'])
        ok_('Camino is not one of the available choices' in response.content)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_topcrasher(self, rget, rpost):
        # first without a version
        no_version_url = reverse('crashstats.topcrasher',
                                 args=('Firefox',))
        url = reverse('crashstats.topcrasher',
                      args=('Firefox', '19.0'))
        has_builds_url = reverse('crashstats.topcrasher',
                                 args=('Firefox', '19.0', 'build'))
        response = self.client.get(no_version_url)
        ok_(url in response['Location'])

        def mocked_post(**options):
            assert '/bugs/' in options['url'], options['url']
            return Response("""
               {"hits": [{"id": "123456789",
                          "signature": "Something"}]}
            """)

        def mocked_get(url, **options):
            if 'crashes/signatures' in url:
                return Response(u"""
                   {"crashes": [
                     {
                      "count": 188,
                      "mac_count": 66,
                      "content_count": 0,
                      "first_report": "2012-06-21",
                      "startup_percent": 0.0,
                      "currentRank": 0,
                      "previousRank": 1,
                      "first_report_exact": "2012-06-21T21:28:08",
                      "versions":
                          "2.0, 2.1, 3.0a2, 3.0b2, 3.1b1, 4.0a1, 4.0a2, 5.0a1",
                      "percentOfTotal": 0.24258064516128999,
                      "win_count": 56,
                      "changeInPercentOfTotal": 0.011139597126354983,
                      "linux_count": 66,
                      "hang_count": 0,
                      "signature": "FakeSignature1 \u7684 Japanese",
                      "versions_count": 8,
                      "changeInRank": 1,
                      "plugin_count": 0,
                      "previousPercentOfTotal": 0.23144104803493501
                    }
                   ],
                    "totalPercentage": 0,
                    "start_date": "2012-05-10",
                    "end_date": "2012-05-24",
                    "totalNumberOfCrashes": 0}
                """)

            if 'products/versions' in url:
                return Response("""
                {
                  "hits": [
                    {
                        "is_featured": true,
                        "throttle": 1.0,
                        "end_date": "string",
                        "start_date": "integer",
                        "build_type": "string",
                        "product": "Firefox",
                        "version": "19.0",
                        "has_builds": true
                    }],
                    "total": "1"
                }
                """)
            raise NotImplementedError(url)

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('By Crash Date' in response.content)

        response = self.client.get(has_builds_url)
        eq_(response.status_code, 200)
        ok_('By Build Date' in response.content)

        # also, render the CSV
        response = self.client.get(url, {'format': 'csv'})
        eq_(response.status_code, 200)
        ok_('text/csv' in response['Content-Type'])
        # know your fixtures :)
        ok_('Firefox' in response['Content-Disposition'])
        ok_('19.0' in response['Content-Disposition'])
        # we should be able unpack it
        reader = csv.reader(StringIO(response.content))
        line1, line2 = reader
        eq_(line1[0], 'Rank')
        # bytestring when exported as CSV with UTF-8 encoding
        eq_(line2[4], 'FakeSignature1 \xe7\x9a\x84 Japanese')

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_topcrasher_without_any_signatures(self, rget, rpost):
        # first without a version
        no_version_url = reverse('crashstats.topcrasher',
                                 args=('Firefox',))
        url = reverse('crashstats.topcrasher',
                      args=('Firefox', '19.0'))
        has_builds_url = reverse('crashstats.topcrasher',
                                 args=('Firefox', '19.0', 'build'))
        response = self.client.get(no_version_url)
        ok_(url in response['Location'])

        def mocked_post(**options):
            assert '/bugs/' in options['url'], options['url']
            return Response("""
               {"hits": [{"id": "123456789",
                          "signature": "Something"}]}
            """)

        def mocked_get(url, **options):
            if 'crashes/signatures' in url:
                return Response(u"""
                   {"crashes": [],
                    "totalPercentage": 0,
                    "start_date": "2012-05-10",
                    "end_date": "2012-05-24",
                    "totalNumberOfCrashes": 0}
                """)

            if 'products/versions' in url:
                return Response("""
                {
                  "hits": [
                    {
                        "is_featured": true,
                        "throttle": 1.0,
                        "end_date": "string",
                        "start_date": "integer",
                        "build_type": "string",
                        "product": "Firefox",
                        "version": "19.0",
                        "has_builds": true
                    }],
                    "total": "1"
                }
                """)
            raise NotImplementedError(url)

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('By Crash Date' in response.content)

        response = self.client.get(has_builds_url)
        eq_(response.status_code, 200)
        ok_('By Build Date' in response.content)

        # also, render the CSV
        response = self.client.get(url, {'format': 'csv'})
        eq_(response.status_code, 200)
        ok_('text/csv' in response['Content-Type'])
        # know your fixtures :)
        ok_('Firefox' in response['Content-Disposition'])
        ok_('19.0' in response['Content-Disposition'])
        #
        # no signatures, the CSV is empty apart from the header
        eq_(len(response.content.splitlines()), 1)
        reader = csv.reader(StringIO(response.content))
        line1, = reader
        eq_(line1[0], 'Rank')

    @mock.patch('requests.get')
    def test_daily(self, rget):
        url = reverse('crashstats.daily')

        def mocked_get(url, **options):
            if 'products' in url:
                return Response("""
                    {
                        "products": [
                            "Firefox",
                            "Thunderbird"
                        ],
                        "hits": {
                            "Firefox": [{
                                "featured": true,
                                "throttle": 100.0,
                                "end_date": "2012-11-27",
                                "product": "Firefox",
                                "release": "Nightly",
                                "version": "19.0",
                                "has_builds": true,
                                "start_date": "2012-09-25"
                            }],
                            "Thunderbird": [{
                                "featured": true,
                                "throttle": 100.0,
                                "end_date": "2012-11-27",
                                "product": "Thunderbird",
                                "release": "Nightly",
                                "version": "18.0",
                                "has_builds": true,
                                "start_date": "2012-09-25"
                            }]
                        },
                        "total": 2
                    }
                """)
            if 'crashes' in url:
                # This list needs to match the versions as done in the common
                # fixtures set up in setUp() above.
                return Response("""
                       {
                         "hits": {
                           "Firefox:20.0": {
                             "2012-09-23": {
                               "adu": 80388,
                               "crash_hadu": 12.279,
                               "date": "2012-08-23",
                               "product": "Firefox",
                               "report_count": 9871,
                               "throttle": 0.1,
                               "version": "20.0"
                             }
                           },
                           "Firefox:19.0": {
                             "2012-08-23": {
                               "adu": 80388,
                               "crash_hadu": 12.279,
                               "date": "2012-08-23",
                               "product": "Firefox",
                               "report_count": 9871,
                               "throttle": 0.1,
                               "version": "19.0"
                             }
                           },
                           "Firefox:18.0": {
                             "2012-08-13": {
                               "adu": 80388,
                               "crash_hadu": 12.279,
                               "date": "2012-08-23",
                               "product": "Firefox",
                               "report_count": 9871,
                               "throttle": 0.1,
                               "version": "18.0"
                             }
                           }
                         }
                       }

                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        response = self.client.get(url, {
            'p': 'Firefox',
            'v': ['20.0', '19.0']
        })
        eq_(response.status_code, 200)
        # XXX any basic tests with can do on response.content?

        # check that the CSV version is working too
        response = self.client.get(url, {
            'p': 'Firefox',
            'v': ['20.0', '19.0'],
            'format': 'csv'
        })
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/csv')

        # also, I should be able to read it
        reader = csv.reader(response)
        # because response is an iterator that will return a blank line first
        # we skip till the next time
        rows = list(reader)[1:]
        ok_(rows)
        head_row = rows[0]
        eq_(head_row[0], 'Date')
        eq_(head_row[1:], [
            'Firefox 20.0 Crashes',
            'Firefox 20.0 ADU',
            'Firefox 20.0 Throttle',
            'Firefox 20.0 Ratio',
            'Firefox 19.0 Crashes',
            'Firefox 19.0 ADU',
            'Firefox 19.0 Throttle',
            'Firefox 19.0 Ratio'
            ])
        first_row = rows[1]
        eq_(first_row[0], '2012-09-23')

    @mock.patch('crashstats.crashstats.models.Platforms')
    @mock.patch('requests.get')
    def test_daily_by_os(self, rget, platforms_get):
        url = reverse('crashstats.daily')

        def mocked_get(url, **options):
            if 'products' in url:
                return Response("""
                    {
                        "products": [
                            "Firefox",
                            "Thunderbird"
                        ],
                        "hits": {
                            "Firefox": [{
                                "featured": true,
                                "throttle": 100.0,
                                "end_date": "2012-11-27",
                                "product": "Firefox",
                                "release": "Nightly",
                                "version": "19.0",
                                "has_builds": true,
                                "start_date": "2012-09-25"
                            }],
                            "Thunderbird": [{
                                "featured": true,
                                "throttle": 100.0,
                                "end_date": "2012-11-27",
                                "product": "Thunderbird",
                                "release": "Nightly",
                                "version": "18.0",
                                "has_builds": true,
                                "start_date": "2012-09-25"
                            }]
                        },
                        "total": 2
                    }
                """)
            if 'crashes' in url:
                assert '/separated_by/os' in url, url
                assert '/os/Windows%2BAmiga' in url, url  # %2B is a +
                # This list needs to match the versions as done in the common
                # fixtures set up in setUp() above.
                return Response("""
                       {
                         "hits": {
                           "Firefox:20.0:win": {
                             "2012-09-23": {
                               "os": "Windows",
                               "adu": 80388,
                               "crash_hadu": 12.279,
                               "date": "2012-08-23",
                               "product": "Firefox",
                               "report_count": 9871,
                               "throttle": 0.1,
                               "version": "20.0"
                             }
                           },
                           "Firefox:20.0:ami": {
                             "2012-09-23": {
                               "os": "Amiga",
                               "adu": 7377,
                               "crash_hadu": 12.279,
                               "date": "2012-08-23",
                               "product": "Firefox",
                               "report_count": 871,
                               "throttle": 0.1,
                               "version": "20.0"
                             }
                           }
                         }
                       }

                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        def mocked_platforms_get():
            return [
                {'code': 'win', 'name': 'Windows'},
                {'code': 'ami', 'name': 'Amiga'},
            ]
        platforms_get().get.side_effect = mocked_platforms_get

        response = self.client.get(url, {
            'p': 'Firefox',
            'v': '20.0',
            'form_selection': 'by_os'
        })
        eq_(response.status_code, 200)
        # XXX any basic tests with can do on response.content?

        # check that the CSV version is working too
        response = self.client.get(url, {
            'p': 'Firefox',
            'v': '20.0',
            'format': 'csv',
            'form_selection': 'by_os'
        })
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/csv')

        # also, we should be able to read it
        reader = csv.reader(response)
        # because response is an iterator that will return a blank line first
        # we skip till the next time
        rows = list(reader)[1:]
        head_row = rows[0]
        first_row = rows[1]
        eq_(head_row[0], 'Date')
        eq_(head_row[1:], [
            'Firefox 20.0 on Windows Crashes',
            'Firefox 20.0 on Windows ADU',
            'Firefox 20.0 on Windows Throttle',
            'Firefox 20.0 on Windows Ratio',
            'Firefox 20.0 on Amiga Crashes',
            'Firefox 20.0 on Amiga ADU',
            'Firefox 20.0 on Amiga Throttle',
            'Firefox 20.0 on Amiga Ratio'
            ])
        eq_(first_row[0], '2012-09-23')

    def test_daily_legacy_redirect(self):
        url = reverse('crashstats.daily')
        response = self.client.get(url + '?p=Firefox&v[]=Something')
        eq_(response.status_code, 301)
        ok_('p=Firefox' in response['Location'].split('?')[1])
        ok_('v=Something' in response['Location'].split('?')[1])

        response = self.client.get(url + '?p=Firefox&os[]=Something&os[]=Else')
        eq_(response.status_code, 301)
        ok_('p=Firefox' in response['Location'].split('?')[1])
        ok_('os=Something' in response['Location'].split('?')[1])
        ok_('os=Else' in response['Location'].split('?')[1])

    @mock.patch('requests.get')
    def test_daily_with_bad_input(self, rget):
        url = reverse('crashstats.daily')

        def mocked_get(url, **options):
            if 'products' in url:
                return Response("""
                    {
                        "products": [
                            "Firefox",
                            "Thunderbird"
                        ],
                        "hits": {
                            "Firefox": [{
                                "featured": true,
                                "throttle": 100.0,
                                "end_date": "2012-11-27",
                                "product": "Firefox",
                                "release": "Nightly",
                                "version": "19.0",
                                "has_builds": true,
                                "start_date": "2012-09-25"
                            }],
                            "Thunderbird": [{
                                "featured": true,
                                "throttle": 100.0,
                                "end_date": "2012-11-27",
                                "product": "Thunderbird",
                                "release": "Nightly",
                                "version": "18.0",
                                "has_builds": true,
                                "start_date": "2012-09-25"
                            }]
                        },
                        "total": 2
                    }
                """)
            if 'crashes' in url:
                # This list needs to match the versions as done in the common
                # fixtures set up in setUp() above.
                return Response("""
                       {
                         "hits": {}
                       }

                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        response = self.client.get(url, {
            'p': 'Firefox',
            'start_date': u' \x00'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'p': 'Firefox',
            'date_range_type': 'any old crap'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'p': 'Firefox',
            'hang_type': 'any old crap'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'p': 'Firefox',
            'format': 'csv',
        })
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/csv')

        # last sanity check
        response = self.client.get(url, {
            'p': 'Firefox',
        })
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_builds(self, rget):
        url = reverse('crashstats.builds', args=('Firefox',))
        rss_url = reverse('crashstats.buildsrss', args=('Firefox',))

        def mocked_get(url, **options):
            if 'products/builds/product' in url:
                # Note that the last one isn't build_type==Nightly
                return Response("""
                    [
                      {
                        "product": "Firefox",
                        "repository": "dev",
                        "buildid": 20120625000001,
                        "beta_number": null,
                        "platform": "Mac OS X",
                        "version": "19.0",
                        "date": "2012-06-25",
                        "build_type": "Nightly"
                      },
                      {
                        "product": "Firefox",
                        "repository": "dev",
                        "buildid": 20120625000002,
                        "beta_number": null,
                        "platform": "Windows",
                        "version": "19.0",
                        "date": "2012-06-25",
                        "build_type": "Nightly"
                      },
                      {
                        "product": "Firefox",
                        "repository": "dev",
                        "buildid": 20120625000003,
                        "beta_number": null,
                        "platform": "BeOS",
                        "version": "5.0a1",
                        "date": "2012-06-25",
                        "build_type": "Beta"
                      }
                    ]
                """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('20120625000001' in response.content)
        ok_('20120625000002' in response.content)
        # the not, build_type==Nightly
        ok_('20120625000003' not in response.content)

        rss_response = self.client.get(rss_url)
        self.assertEquals(rss_response.status_code, 200)
        self.assertEquals(rss_response['Content-Type'],
                          'application/rss+xml; charset=utf-8')
        ok_('20120625000001' in rss_response.content)
        ok_('20120625000002' in rss_response.content)
        # the not, build_type==Nightly
        ok_('20120625000003' not in rss_response.content)

    @mock.patch('requests.get')
    def test_builds_by_old_version(self, rget):
        url = reverse('crashstats.builds', args=('Firefox', '18.0'))

        def mocked_get(url, **options):
            if 'products/builds/product' in url and 'version/18.0' in url:
                return Response("""
                    [
                      {
                        "product": "Firefox",
                        "repository": "dev",
                        "buildid": 20120625000007,
                        "beta_number": null,
                        "platform": "Mac OS X",
                        "version": "5.0a1",
                        "date": "2012-06-25",
                        "build_type": "Nightly"
                      },
                      {
                        "product": "Firefox",
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
            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        response = self.client.get(url)
        eq_(response.status_code, 200)
        header = response.content.split('<h2')[1].split('</h2>')[0]
        ok_('18.0' in header)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_query(self, rget, rpost):

        def mocked_post(**options):
            assert 'bugs' in options['url'], options['url']
            return Response("""
                {"hits": [
                    {
                    "id": "123456",
                    "signature": "nsASDOMWindowEnumerator::GetNext()"
                    }
                 ],
                 "total": 1
                }
            """)

        def mocked_get(url, **options):
            assert 'search/signatures' in url
            if 'products/Firefox' in url:
                return Response("""{
                    "hits": [
                    {
                      "count": 586,
                      "signature": "nsASDOMWindowEnumerator::GetNext()",
                      "numcontent": 0,
                      "is_windows": 586,
                      "is_linux": 0,
                      "numplugin": 56,
                      "is_mac": 0,
                      "numhang": 0
                    },
                    {
                      "count": 13,
                      "signature": "mySignatureIsCool",
                      "numcontent": 0,
                      "is_windows": 10,
                      "is_linux": 2,
                      "numplugin": 0,
                      "is_mac": 1,
                      "numhang": 0
                    },
                    {
                      "count": 2,
                      "signature": "mineIsCoolerThanYours",
                      "numcontent": 0,
                      "is_windows": 0,
                      "is_linux": 0,
                      "numplugin": 0,
                      "is_mac": 2,
                      "numhang": 2
                    },
                    {
                      "count": 2,
                      "signature": null,
                      "numcontent": 0,
                      "is_windows": 0,
                      "is_linux": 0,
                      "numplugin": 0,
                      "is_mac": 2,
                      "numhang": 2
                    }
                    ],
                    "total": 4
                } """)
            elif 'products/Thunderbird' in url:
                return Response('{"hits": [], "total": 0}')
            elif 'products/Camino' in url:
                self.assertTrue('plugin_search_mode/is_exactly' in url)
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
                  "total": 1
                  }
                """)
            else:
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
                  "total": 1
                  }
                """)

            raise NotImplementedError(url)

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get
        url = reverse('crashstats.query')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<h2>Query Results</h2>' not in response.content)
        ok_('table id="signatureList"' not in response.content)

        # Verify that the passed product is selected in search form
        response = self.client.get(url, {'product': 'Thunderbird'})
        eq_(response.status_code, 200)
        ok_('<h2>Query Results</h2>' not in response.content)
        ok_('table id="signatureList"' not in response.content)
        ok_('value="Thunderbird" selected' in response.content)

        # Verify that the passed version is selected in nav
        response = self.client.get(url, {
            'product': 'Thunderbird',
            'version': 'Thunderbird:18.0'
        })
        eq_(response.status_code, 200)
        ok_('<h2>Query Results</h2>' not in response.content)
        ok_('table id="signatureList"' not in response.content)
        # Because versions in the search form only gets set on DOM ready,
        # we here ensure that the version was passed and set by checking
        # that the correct version is selected in the versions drop-down.
        ok_('option value="18.0" selected' in response.content)

        response = self.client.get(url, {
            'product': 'Firefox',
            'date': '2012-01-01'
        })
        eq_(response.status_code, 200)
        ok_('<h2>Query Results</h2>' in response.content)
        ok_('table id="signatureList"' in response.content)
        ok_('nsASDOMWindowEnumerator::GetNext()' in response.content)
        ok_('mySignatureIsCool' in response.content)
        ok_('mineIsCoolerThanYours' in response.content)
        ok_('(null signature)' in response.content)

        # Test that the default value for query_type is 'contains'
        ok_('<option value="contains" selected' in response.content)

        # Test with empty results
        response = self.client.get(url, {
            'product': 'Thunderbird',
            'date': '2012-01-01'
        })
        eq_(response.status_code, 200)
        ok_('<h2>Query Results</h2>' in response.content)
        ok_('The maximum query date' not in response.content)
        ok_('table id="signatureList"' not in response.content)
        ok_('Results within' in response.content)
        ok_('No results were found' in response.content)

        response = self.client.get(url, {'query': 'nsASDOMWindowEnumerator'})
        eq_(response.status_code, 200)
        ok_('<h2>Query Results</h2>' in response.content)
        ok_('table id="signatureList"' in response.content)
        ok_('nsASDOMWindowEnumerator::GetNext()' in response.content)
        ok_('123456' in response.content)

        # Test that the signature parameter is used as default value
        response = self.client.get(url, {'signature': 'myFunctionIsCool'})
        eq_(response.status_code, 200)
        ok_('<h2>Query Results</h2>' not in response.content)
        ok_('table id="signatures-list"' not in response.content)
        ok_('value="myFunctionIsCool"' in response.content)

        # Test a simple search containing a ooid
        ooid = '1234abcd-ef56-7890-ab12-abcdef123456'
        response = self.client.get(url, {
            'query': ooid,
            'query_type': 'simple'
        })
        eq_(response.status_code, 302)
        ok_(ooid in response['Location'])

        # Test that null bytes break the page cleanly
        response = self.client.get(url, {'date': u' \x00'})
        eq_(response.status_code, 400)
        ok_('<h2>Query Results</h2>' not in response.content)
        ok_('Enter a valid date/time' in response.content)

        # Test an out-of-range date range
        response = self.client.get(url, {
            'query': 'js::',
            'range_unit': 'weeks',
            'range_value': 9
        })
        eq_(response.status_code, 200)
        ok_('The maximum query date' in response.content)
        ok_('name="range_value" value="%s"' % settings.QUERY_RANGE_DEFAULT_DAYS
            in response.content)
        ok_('value="days" selected' in response.content)

        # Test that do_query forces the query
        response = self.client.get(url, {
            'do_query': 1,
            'product': 'Firefox'
        })
        eq_(response.status_code, 200)
        ok_('<h2>Query Results</h2>' in response.content)
        ok_('table id="signatureList"' in response.content)
        ok_('nsASDOMWindowEnumerator::GetNext()' in response.content)

        # Test that old query types are changed
        response = self.client.get(url, {
            'do_query': 1,
            'product': 'Camino',
            'plugin_query_type': 'exact'
        })
        eq_(response.status_code, 200)
        ok_('<h2>Query Results</h2>' in response.content)
        ok_('table id="signatureList"' in response.content)
        ok_('nsASDOMWindowEnumerator::GetNext()' in response.content)

        # Test defaut date
        expected = datetime.datetime.utcnow()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(expected.strftime('%m/%d/%Y %H:00:00') in response.content)

        # Test passed date
        response = self.client.get(url, {
            'date': '11/27/2085 10:10:10'
        })
        eq_(response.status_code, 200)
        ok_('11/27/2085 10:10:10' in response.content)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_query_summary(self, rget, rpost):

        def mocked_post(**options):
            return Response('{"hits": [], "total": 0}')

        def mocked_get(url, **options):
            return Response('{"hits": [], "total": 0}')

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get
        url = reverse('crashstats.query')

        response = self.client.get(url, {
            'query': 'test',
            'query_type': 'contains'
        })
        eq_(response.status_code, 200)
        ok_('Results within' in response.content)
        ok_("crash signature contains 'test'" in response.content)
        ok_('the crashing process was of any type' in response.content)

        response = self.client.get(url, {
            'query': 'test',
            'query_type': 'is_exactly',
            'build_id': '1234567890',
            'product': ['Firefox', 'Thunderbird'],
            'version': ['Firefox:18.0'],
            'platform': ['mac'],
            'process_type': 'plugin',
            'plugin_query_type': 'starts_with',
            'plugin_query_field': 'filename',
            'plugin_query': 'lib'
        })
        eq_(response.status_code, 200)
        ok_('Results within' in response.content)
        ok_("crash signature is exactly 'test'" in response.content)
        ok_('product is one of Firefox, Thunderbird' in response.content)
        ok_('version is one of Firefox:18.0' in response.content)
        ok_('platform is one of Mac OS X' in response.content)
        ok_('for build 1234567890' in response.content)
        ok_('the crashing process was a plugin' in response.content)
        ok_('and its filename starts with lib' in response.content)

    @mock.patch('requests.get')
    def test_plot_signature(self, rget):
        def mocked_get(url, **options):
            if 'topcrash/sig/trend' in url:
                return Response("""
                {
                  "signature": "Pickle::ReadBytes",
                  "start_date": "2012-04-19T08:00:00+00:00",
                  "end_date": "2012-05-31T00:00:00+00:00",
                  "signatureHistory": []
                }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        # missing signature
        url = reverse('crashstats.plot_signature',
                      args=('Firefox', '19.0',
                            '2011-12-01', '2011-12-02', ''))
        response = self.client.get(url)
        eq_(response.status_code, 400)

        # invalid start date
        url = reverse('crashstats.plot_signature',
                      args=('Firefox', '19.0',
                            '2012-02-33', '2012-12-01',
                            'Read::Bytes'))
        response = self.client.get(url)
        eq_(response.status_code, 400)

        # invalid end date
        url = reverse('crashstats.plot_signature',
                      args=('Firefox', '19.0',
                            '2012-02-28', '2012-13-01',
                            'Read::Bytes'))
        response = self.client.get(url)
        eq_(response.status_code, 400)

        # valid dates
        url = reverse('crashstats.plot_signature',
                      args=('Firefox', '19.0',
                            '2011-12-01', '2011-12-02',
                            'Read::Bytes'))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        ok_(struct['signature'])

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_topchangers(self, rget, rpost):
        url = reverse('crashstats.topchangers',
                      args=('Firefox', '19.0'))

        bad_url = reverse('crashstats.topchangers',
                          args=('Camino', '19.0'))

        bad_url2 = reverse('crashstats.topchangers',
                           args=('Firefox', '19.999'))

        url_wo_version = reverse('crashstats.topchangers',
                                 args=('Firefox',))

        def mocked_post(**options):
            assert 'by/signatures' in options['url'], options['url']
            return Response("""
               {"bug_associations": [{"bug_id": "123456789",
                                      "signature": "Something"}]}
            """)

        def mocked_get(url, **options):
            if 'crashes/signatures' in url:
                return Response("""
                   {"crashes": [
                     {
                      "count": 188,
                      "mac_count": 66,
                      "content_count": 0,
                      "first_report": "2012-06-21",
                      "startup_percent": 0.0,
                      "currentRank": 0,
                      "previousRank": 1,
                      "first_report_exact": "2012-06-21T21:28:08",
                      "versions":
                          "2.0, 2.1, 3.0a2, 3.0b2, 3.1b1, 4.0a1, 4.0a2, 5.0a1",
                      "percentOfTotal": 0.24258064516128999,
                      "win_count": 56,
                      "changeInPercentOfTotal": 0.011139597126354983,
                      "linux_count": 66,
                      "hang_count": 0,
                      "signature": "FakeSignature1",
                      "versions_count": 8,
                      "changeInRank": 0,
                      "plugin_count": 0,
                      "previousPercentOfTotal": 0.23144104803493501
                    }
                   ],
                    "totalPercentage": 0,
                    "start_date": "2012-05-10",
                    "end_date": "2012-05-24",
                    "totalNumberOfCrashes": 0}
                """)
            raise NotImplementedError(url)

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get

        response = self.client.get(url_wo_version)
        eq_(response.status_code, 200)

        # invalid version for the product name
        response = self.client.get(bad_url)
        eq_(response.status_code, 404)

        # invalid version for the product name
        response = self.client.get(bad_url2)
        eq_(response.status_code, 404)

        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_signature_summary(self, rget):
        def mocked_get(url, **options):
            if 'signaturesummary' in url:
                return Response("""
                [
                  {
                    "version_string": "12.0",
                    "percentage": "48.440",
                    "report_count": 52311,
                    "product_name": "Firefox",
                    "category": "XXX"
                  },
                  {
                    "version_string": "13.0b4",
                    "percentage": "9.244",
                    "report_count": 9983,
                    "product_name": "Firefox",
                    "category": "YYY"
                  }
                ]
                """)

            raise NotImplementedError(url)

        url = reverse('crashstats.signature_summary')

        rget.side_effect = mocked_get

        response = self.client.get(url, {'range_value': '1',
                                         'signature': 'sig'})
        eq_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        ok_(struct['architectures'])
        ok_(struct['flashVersions'])
        ok_(struct['percentageByOs'])
        ok_(struct['processTypes'])
        ok_(struct['productVersions'])
        ok_(struct['uptimeRange'])

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

        url = reverse('crashstats.status')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_('017d7b3f7042ce76bc80949ae55b41d1e915ab62' in response.content)
        ok_('1035' in response.content)
        ok_('Sep 28 2012 20:30:01' in response.content)

    @mock.patch('requests.get')
    def test_status_json(self, rget):
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

        url = reverse('crashstats.status_json')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_(response.content.strip().startswith('{'))
        ok_('017d7b3f7042ce76bc80949ae55b41d1e915ab62' in response.content)
        ok_('1035' in response.content)
        ok_('2012-09-28T20:30:01+00:00' in response.content)
        ok_('application/json' in response['Content-Type'])
        eq_('*', response['Access-Control-Allow-Origin'])

    @mock.patch('requests.get')
    def test_crontabber_state(self, rget):
        def mocked_get(**options):
            assert 'crontabber_state' in options['url'], options['url']
            return Response("""
        {
            "state": {
              "slow-one": {
                "next_run": "2013-02-19 01:16:00.893834",
                "first_run": "2012-11-05 23:27:07.316347",
                "last_error": {
                  "traceback": "error error error",
                  "type": "<class 'sluggish.jobs.InternalError'>",
                  "value": "Have already run this for 2012-12-24 23:27"
                },
                "last_run": "2013-02-09 00:16:00.893834",
                "last_success": "2012-12-24 22:27:07.316893",
                "error_count": 6,
                "depends_on": []
              },
              "slow-two": {
                "next_run": "2012-11-12 19:39:59.521605",
                "first_run": "2012-11-05 23:27:17.341879",
                "last_error": {},
                "last_run": "2012-11-12 18:39:59.521605",
                "last_success": "2012-11-12 18:27:17.341895",
                "error_count": 0,
                "depends_on": ["slow-one"]
              },
              "slow-zero": {
                "next_run": "2012-11-12 19:39:59.521605",
                "first_run": "2012-11-05 23:27:17.341879",
                "last_error": {},
                "last_run": "2012-11-12 18:39:59.521605",
                "last_success": "2012-11-12 18:27:17.341895",
                "error_count": 0,
                "depends_on": []
              }

            },
            "last_updated": "2000-01-01T00:00:00+00:00"
        }
        """)

        rget.side_effect = mocked_get

        url = reverse('crashstats.crontabber_state')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_('2000-01-01T00:00:00+00:00' in response.content)
        ok_('1/01/2000 00:00 UTC' in response.content)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_report_index(self, rget, rpost):
        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod"
        comment0 = "This is a comment"
        email0 = "some@emailaddress.com"
        url0 = "someaddress.com"
        email1 = "some@otheremailaddress.com"

        def mocked_get(url, **options):
            if '/crash_data/' in url and '/datatype/meta/' in url:
                return Response("""
                {
                  "InstallTime": "1339289895",
                  "FramePoisonSize": "4096",
                  "Theme": "classic/1.0",
                  "Version": "5.0a1",
                  "Email": "%s",
                  "Vendor": "Mozilla",
                  "URL": "%s"
                }
                """ % (email0, url0))
            if 'crashes/comments' in url:
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "%s",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "%s",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
              """ % (comment0, email1))

            if '/crash_data/' in url and '/datatype/processed' in url:
                return Response("""
                {
                  "client_crash_date": "2012-06-11T06:08:45",
                  "dump": "%s",
                  "signature": "FakeSignature1",
                  "user_comments": null,
                  "uptime": 14693,
                  "release_channel": "nightly",
                  "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
                  "flash_version": "[blank]",
                  "hangid": null,
                  "distributor_version": null,
                  "truncated": true,
                  "process_type": null,
                  "id": 383569625,
                  "os_version": "10.6.8 10K549",
                  "version": "5.0a1",
                  "build": "20120609030536",
                  "ReleaseChannel": "nightly",
                  "addons_checked": null,
                  "product": "WaterWolf",
                  "os_name": "Mac OS X",
                  "last_crash": 371342,
                  "date_processed": "2012-06-11T06:08:44",
                  "cpu_name": "amd64",
                  "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                  "address": "0x8",
                  "completeddatetime": "2012-06-11T06:08:57",
                  "success": true
                }
                """ % dump)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        def mocked_post(url, **options):
            if '/bugs/' in url:
                return Response("""
                   {"hits": [{"id": "123456789",
                              "signature": "Something"}]}
                """)
            raise NotImplementedError(url)

        rpost.side_effect = mocked_post

        url = reverse('crashstats.report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('FakeSignature1' in response.content)
        ok_('11cb72f5-eb28-41e1-a8e4-849982120611' in response.content)
        ok_(comment0 in response.content)
        ok_(email0 not in response.content)
        ok_(email1 not in response.content)
        ok_(url0 not in response.content)

        # the email address will appear if we log in
        User.objects.create_user('test', 'test@mozilla.com', 'secret')
        assert self.client.login(username='test', password='secret')
        response = self.client.get(url)
        ok_(email0 in response.content)
        ok_(email1 in response.content)
        ok_(url0 in response.content)
        eq_(response.status_code, 200)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_report_index_with_hangid_in_raw_data(self, rget, rpost):
        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod"
        comment0 = "This is a comment"
        email0 = "some@emailaddress.com"
        url0 = "someaddress.com"
        email1 = "some@otheremailaddress.com"

        def mocked_get(url, **options):
            if '/crash_data/' in url and '/datatype/meta/' in url:
                return Response("""
                {
                  "InstallTime": "1339289895",
                  "FramePoisonSize": "4096",
                  "Theme": "classic/1.0",
                  "Version": "5.0a1",
                  "Email": "%s",
                  "Vendor": "Mozilla",
                  "URL": "%s",
                  "HangID": "123456789"
                }
                """ % (email0, url0))
            if '/crashes/paireduuid/' in url:
                return Response("""
                {
                  "hits": [{
                      "uuid": "e8820616-1462-49b6-9784-e99a32120201"
                  }],
                  "total": 1
                }
                """)
            if 'crashes/comments' in url:
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "%s",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "%s",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
              """ % (comment0, email1))

            if '/crash_data/' in url and '/datatype/processed' in url:
                return Response("""
                {
                  "client_crash_date": "2012-06-11T06:08:45",
                  "dump": "%s",
                  "signature": "FakeSignature1",
                  "user_comments": null,
                  "uptime": 14693,
                  "release_channel": "nightly",
                  "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
                  "flash_version": "[blank]",
                  "hangid": null,
                  "distributor_version": null,
                  "truncated": true,
                  "process_type": null,
                  "id": 383569625,
                  "os_version": "10.6.8 10K549",
                  "version": "5.0a1",
                  "build": "20120609030536",
                  "ReleaseChannel": "nightly",
                  "addons_checked": null,
                  "product": "WaterWolf",
                  "os_name": "Mac OS X",
                  "last_crash": 371342,
                  "date_processed": "2012-06-11T06:08:44",
                  "cpu_name": "amd64",
                  "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                  "address": "0x8",
                  "completeddatetime": "2012-06-11T06:08:57",
                  "success": true
                }
                """ % dump)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        def mocked_post(url, **options):
            if '/bugs/' in url:
                return Response("""
                   {"hits": [{"id": "123456789",
                              "signature": "Something"}]}
                """)
            raise NotImplementedError(url)

        rpost.side_effect = mocked_post

        url = reverse('crashstats.report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        ok_('Hang Minidump' in response.content)
        # the HangID in the fixture above
        ok_('123456789' in response.content)

    @mock.patch('requests.get')
    def test_report_index_not_found(self, rget):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_get(url, **options):
            if '/datatype/processed/' in url:
                raise models.BadStatusCodeError(404)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats.report_index',
                      args=[crash_id])
        response = self.client.get(url)

        eq_(response.status_code, 200)
        ok_("We couldn't find" in response.content)

    @mock.patch('requests.get')
    def test_report_index_pending(self, rget):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_get(url, **options):
            if '/datatype/processed/' in url:
                raise models.BadStatusCodeError(408)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats.report_index',
                      args=[crash_id])
        response = self.client.get(url)

        eq_(response.status_code, 200)
        ok_('Fetching this archived report' in response.content)

    @mock.patch('requests.get')
    def test_report_index_too_old(self, rget):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_get(url, **options):
            if '/datatype/processed/' in url:
                raise models.BadStatusCodeError(410)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats.report_index',
                      args=[crash_id])
        response = self.client.get(url)

        eq_(response.status_code, 200)
        ok_('This archived report has expired' in response.content)

    @mock.patch('requests.get')
    def test_report_pending_json(self, rget):
        crash_id = '11cb72f5-eb28-41e1-a8e4-849982120611'

        def mocked_get(url, **options):
            if '/datatype/processed/' in url:
                raise models.BadStatusCodeError(408)

            raise NotImplementedError(url)

        url = reverse('crashstats.report_pending',
                      args=[crash_id])
        response = self.client.get(url)

        expected = {
            'status': 'error',
            'status_message': ('The report for %s'
                               ' is not available yet.' % crash_id),
            'url_redirect': ''
        }

        eq_(response.status_code, 200)
        eq_(expected, json.loads(response.content))

    def test_report_index_and_pending_missing_crash_id(self):
        url = reverse('crashstats.report_index', args=[''])
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('crashstats.report_pending', args=[''])
        response = self.client.get(url)
        eq_(response.status_code, 404)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_report_list(self, rget, rpost):

        def mocked_post(url, **options):
            if '/bugs/' in url:
                return Response("""
                   {"hits": [{"id": "123456789",
                              "signature": "Something"}]}
                """)
            raise NotImplementedError(url)

        rpost.side_effect = mocked_post

        def mocked_get(url, **options):
            if 'report/list/' in url:
                return Response("""
                {
                  "hits": [
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Linux",
                      "uuid": "441017f4-e006-4eea-8451-dc20e0120905",
                      "cpu_info": "...",
                      "url": "http://example.com/116",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "browser",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120901000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    },
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Mac OS X",
                      "uuid": "e491c551-be0d-b0fb-c69e-107380120905",
                      "cpu_info": "...",
                      "url": "http://example.com/60053",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "content",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120822000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    }
                    ],
                    "total": 2
                    }
                """)
            if '/crashes/comments/' in url:
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "I LOVE CHEESE",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "bob@uncle.com",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats.report_list')
        response = self.client.get(url)
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 'xxx'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {'signature': 'sig'})
        eq_(response.status_code, 200)

        response = self.client.get(url, {
            'signature': 'sig',
            'range_value': 3
        })
        eq_(response.status_code, 200)

        ok_('0xdeadbeef' in response.content)
        ok_('I LOVE CHEESE' in response.content)
        ok_('bob@uncle.com' not in response.content)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_report_index_redirect_by_prefix(self, rget, rpost):

        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod"
        comment0 = "This is a comment"
        email0 = "some@emailaddress.com"
        url0 = "someaddress.com"
        email1 = "some@otheremailaddress.com"

        def mocked_get(url, **options):
            if '/crash_data/' in url and '/datatype/meta/' in url:
                return Response("""
                {
                  "InstallTime": "1339289895",
                  "FramePoisonSize": "4096",
                  "Theme": "classic/1.0",
                  "Version": "5.0a1",
                  "Email": "%s",
                  "Vendor": "Mozilla",
                  "URL": "%s"
                }
                """ % (email0, url0))
            if 'crashes/comments' in url:
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "%s",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "%s",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
              """ % (comment0, email1))

            if '/crash_data/' in url and '/datatype/processed' in url:
                return Response("""
                {
                  "client_crash_date": "2012-06-11T06:08:45",
                  "dump": "%s",
                  "signature": "FakeSignature1",
                  "user_comments": null,
                  "uptime": 14693,
                  "release_channel": "nightly",
                  "uuid": "11cb72f5-eb28-41e1-a8e4-849982120611",
                  "flash_version": "[blank]",
                  "hangid": null,
                  "distributor_version": null,
                  "truncated": true,
                  "process_type": null,
                  "id": 383569625,
                  "os_version": "10.6.8 10K549",
                  "version": "5.0a1",
                  "build": "20120609030536",
                  "ReleaseChannel": "nightly",
                  "addons_checked": null,
                  "product": "WaterWolf",
                  "os_name": "Mac OS X",
                  "last_crash": 371342,
                  "date_processed": "2012-06-11T06:08:44",
                  "cpu_name": "amd64",
                  "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                  "address": "0x8",
                  "completeddatetime": "2012-06-11T06:08:57",
                  "success": true
                }
                """ % dump)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        def mocked_post(url, **options):
            if '/bugs/' in url:
                return Response("""
                   {"hits": [{"id": "123456789",
                              "signature": "Something"}]}
                """)
            raise NotImplementedError(url)

        rpost.side_effect = mocked_post

        crash_id = (
            settings.CRASH_ID_PREFIX + '11cb72f5-eb28-41e1-a8e4-849982120611'
        )
        assert len(crash_id) > 36
        url = reverse('crashstats.report_index', args=[crash_id])
        response = self.client.get(url)
        eq_(response.status_code, 302)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_report_list_with_no_data(self, rget, rpost):

        def mocked_post(url, **options):
            if '/bugs/' in url:
                return Response("""
                   {"hits": [{"id": "123456789",
                              "signature": "Something"}]}
                """)
            raise NotImplementedError(url)

        rpost.side_effect = mocked_post

        def mocked_get(url, **options):
            if 'report/list/' in url:
                return Response("""
                {
                  "hits": [],
                  "total": 0
                }
                """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats.report_list')
        response = self.client.get(url, {'signature': 'sig'})
        eq_(response.status_code, 200)
        # it sucks to depend on the output like this but it'll do for now since
        # it's quite a rare occurance.
        ok_('no reports in the time period specified' in response.content)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_report_list_logged_in(self, rget, rpost):

        def mocked_post(url, **options):
            if '/bugs/' in url:
                return Response("""
                   {"hits": [{"id": "123456789",
                              "signature": "Something"}]}
                """)
            raise NotImplementedError(url)

        rpost.side_effect = mocked_post

        really_long_url = (
            'http://thisistheworldsfivehundredthirtyfifthslong'
            'esturk.com/that/contains/a/path/and/?a=query&'
        )
        assert len(really_long_url) > 80

        def mocked_get(url, **options):
            if '/signatureurls/' in url:
                return Response("""{
                    "hits": [
                        {"url": "http://farm.ville", "crash_count":123},
                        {"url": "%s", "crash_count": 1}
                    ],
                    "total": 2
                }
                """ % (really_long_url))

            if 'report/list/' in url:
                return Response("""
                {
                  "hits": [
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Linux",
                      "uuid": "441017f4-e006-4eea-8451-dc20e0120905",
                      "cpu_info": "...",
                      "url": "http://example.com/116",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "browser",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120901000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    },
                    {
                      "user_comments": null,
                      "product": "WaterWolf",
                      "os_name": "Mac OS X",
                      "uuid": "e491c551-be0d-b0fb-c69e-107380120905",
                      "cpu_info": "...",
                      "url": "http://example.com/60053",
                      "last_crash": 1234,
                      "date_processed": "2012-09-05T21:18:58+00:00",
                      "cpu_name": "x86",
                      "uptime": 1234,
                      "process_type": "content",
                      "hangid": null,
                      "reason": "reason7",
                      "version": "5.0a1",
                      "os_version": "1.2.3.4",
                      "build": "20120822000007",
                      "install_age": 1234,
                      "signature": "FakeSignature2",
                      "install_time": "2012-09-05T20:58:24+00:00",
                      "address": "0xdeadbeef",
                      "duplicate_of": null
                    }
                    ],
                    "total": 2
                    }
                """)

            if '/crashes/comments/' in url:
                return Response("""
                {
                  "hits": [
                   {
                     "user_comments": "I LOVE CHEESE",
                     "date_processed": "2012-08-21T11:17:28-07:00",
                     "email": "bob@uncle.com",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
                """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('crashstats.report_list')
        response = self.client.get(url, {'signature': 'sig'})
        eq_(response.status_code, 200)
        ok_('http://farm.ville' not in response.content)
        ok_('bob@uncle.com' not in response.content)

        User.objects.create_user('test', 'test@mozilla.com', 'secret')
        assert self.client.login(username='test', password='secret')

        url = reverse('crashstats.report_list')
        response = self.client.get(url, {'signature': 'sig'})
        eq_(response.status_code, 200)
        # now it suddenly appears when we're logged in
        ok_('http://farm.ville' in response.content)
        ok_('bob@uncle.com' in response.content)
        # not too long...
        ok_(really_long_url[:80 - 3] + '...' in response.content)

    @mock.patch('requests.get')
    def test_raw_data(self, rget):

        def mocked_get(url, **options):
            assert '/crash_data/' in url
            if 'datatype/meta/' in url:
                return Response("""
                  {"foo": "bar",
                   "stuff": 123}
                """)
            if '/datatype/raw/' in url:
                return Response("""
                  bla bla bla
                """.strip())
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        crash_id = '176bcd6c-c2ec-4b0c-9d5f-dadea2120531'
        json_url = reverse('crashstats.raw_data', args=(crash_id, 'json'))
        response = self.client.get(json_url)
        eq_(response.status_code, 403)

        User.objects.create_user('test', 'test@mozilla.com', 'secret')
        assert self.client.login(username='test', password='secret')
        response = self.client.get(json_url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/json')
        eq_(json.loads(response.content),
            {"foo": "bar", "stuff": 123})

        dump_url = reverse('crashstats.raw_data', args=(crash_id, 'dmp'))
        response = self.client.get(dump_url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/octet-stream')
        ok_('bla bla bla' in response.content)

        # dump files are cached.
        # check the mock function and expect no change
        def different_mocked_get(url, **options):
            if 'crash_data/datatype/raw/uuid' in url:
                return Response("""
                  SOMETHING DIFFERENT
                """.strip())
            raise NotImplementedError(url)

        rget.side_effect = different_mocked_get

        response = self.client.get(dump_url)
        eq_(response.status_code, 200)
        ok_('bla bla bla' in response.content)  # still. good.

    @mock.patch('requests.get')
    def test_links_to_builds_rss(self, rget):

        def mocked_get(url, **options):
            if 'products/builds/product' in url:
                # Note that the last one isn't build_type==Nightly
                return Response("""
                    [
                      {
                        "product": "Firefox",
                        "repository": "dev",
                        "buildid": 20120625000001,
                        "beta_number": null,
                        "platform": "Mac OS X",
                        "version": "19.0",
                        "date": "2012-06-25",
                        "build_type": "Nightly"
                      },
                      {
                        "product": "Firefox",
                        "repository": "dev",
                        "buildid": 20120625000002,
                        "beta_number": null,
                        "platform": "Windows",
                        "version": "19.0",
                        "date": "2012-06-25",
                        "build_type": "Nightly"
                      },
                      {
                        "product": "Firefox",
                        "repository": "dev",
                        "buildid": 20120625000003,
                        "beta_number": null,
                        "platform": "BeOS",
                        "version": "5.0a1",
                        "date": "2012-06-25",
                        "build_type": "Beta"
                      }
                    ]
                """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        rss_product_url = reverse('crashstats.buildsrss', args=('Firefox',))
        rss_version_url = reverse('crashstats.buildsrss',
                                  args=('Firefox', '19.0'))

        url = reverse('crashstats.builds', args=('Firefox',))
        response = self.client.get(url)
        ok_('href="%s"' % rss_product_url in response.content)
        ok_('href="%s"' % rss_version_url not in response.content)

        url = reverse('crashstats.builds', args=('Firefox', '19.0'))
        response = self.client.get(url)
        ok_('href="%s"' % rss_product_url not in response.content)
        ok_('href="%s"' % rss_version_url in response.content)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_remembered_date_range_type(self, rget, rpost):
        # if you visit the home page, the default date_range_type will be
        # 'report' but if you switch to 'build' it'll remember that

        def mocked_get(url, **options):
            if 'products' in url and not 'version' in url:
                return Response("""
                    {
                        "products": [
                            "Firefox"
                        ],
                        "hits": {
                            "Firefox": [{
                            "featured": true,
                            "throttle": 100.0,
                            "end_date": "2012-11-27",
                            "product": "Firefox",
                            "release": "Nightly",
                            "version": "19.0",
                            "has_builds": true,
                            "start_date": "2012-09-25"
                            }]
                        },
                        "total": 1
                    }
                """)
            elif 'products' in url:
                return Response("""
                    {
                        "hits": [{
                            "is_featured": true,
                            "throttle": 100.0,
                            "end_date": "2012-11-27",
                            "product": "Firefox",
                            "build_type": "Nightly",
                            "version": "19.0",
                            "has_builds": true,
                            "start_date": "2012-09-25"
                        }],
                        "total": 1
                    }
                """)

            if 'crashes/daily' in url:
                return Response("""
                    {
                      "hits": {
                        "Firefox:19.0": {
                          "2012-10-08": {
                            "product": "Firefox",
                            "adu": 30000,
                            "crash_hadu": 71.099999999999994,
                            "version": "19.0",
                            "report_count": 2133,
                            "date": "2012-10-08"
                          },
                          "2012-10-02": {
                            "product": "Firefox",
                            "adu": 30000,
                            "crash_hadu": 77.299999999999997,
                            "version": "19.0",
                            "report_count": 2319,
                            "date": "2012-10-02"
                         }
                        }
                      }
                    }
                    """)
            if 'crashes/signatures' in url:
                return Response("""
                   {"crashes": [
                     {
                      "count": 188,
                      "mac_count": 66,
                      "content_count": 0,
                      "first_report": "2012-06-21",
                      "startup_percent": 0.0,
                      "currentRank": 0,
                      "previousRank": 1,
                      "first_report_exact": "2012-06-21T21:28:08",
                      "versions":
                          "2.0, 2.1, 3.0a2, 3.0b2, 3.1b1, 4.0a1, 4.0a2, 5.0a1",
                      "percentOfTotal": 0.24258064516128999,
                      "win_count": 56,
                      "changeInPercentOfTotal": 0.011139597126354983,
                      "linux_count": 66,
                      "hang_count": 0,
                      "signature": "FakeSignature1",
                      "versions_count": 8,
                      "changeInRank": 0,
                      "plugin_count": 0,
                      "previousPercentOfTotal": 0.23144104803493501
                    }
                   ],
                    "totalPercentage": 0,
                    "start_date": "2012-05-10",
                    "end_date": "2012-05-24",
                    "totalNumberOfCrashes": 0}
                """)

            raise NotImplementedError(url)

        def mocked_post(**options):
            assert '/bugs/' in options['url'], options['url']
            return Response("""
               {"hits": [{"id": "123456789",
                          "signature": "Something"}]}
            """)

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get

        url = reverse('crashstats.home', args=('Firefox',))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        regex = re.compile('(<a\s+href="\?date_range_type=(\w+)[^>]+)')
        for tag, value in regex.findall(response.content):
            if value == 'report':
                ok_('selected' in tag)
            else:
                ok_('selected' not in tag)

        # now, like the home page does, fire of an AJAX request to frontpage
        # for 'build' instead
        frontpage_json_url = reverse('crashstats.frontpage_json')
        frontpage_reponse = self.client.get(frontpage_json_url, {
            'product': 'Firefox',
            'date_range_type': 'build'
        })
        eq_(frontpage_reponse.status_code, 200)

        # load the home page again, and it should be on build date instead
        response = self.client.get(url)
        eq_(response.status_code, 200)
        for tag, value in regex.findall(response.content):
            if value == 'build':
                ok_('selected' in tag)
            else:
                ok_('selected' not in tag)

        # open topcrashers with 'report'
        topcrasher_report_url = reverse(
            'crashstats.topcrasher',
            kwargs={
                'product': 'Firefox',
                'versions': '19.0',
                'date_range_type': 'report'
            }
        )
        response = self.client.get(topcrasher_report_url)
        eq_(response.status_code, 200)

        # now, go back to the home page, and 'report' should be the new default
        response = self.client.get(url)
        eq_(response.status_code, 200)
        for tag, value in regex.findall(response.content):
            if value == 'report':
                ok_('selected' in tag)
            else:
                ok_('selected' not in tag)

        # open topcrashers with 'build'
        topcrasher_report_url = reverse(
            'crashstats.topcrasher',
            kwargs={
                'product': 'Firefox',
                'versions': '19.0',
                'date_range_type': 'build'
            }
        )
        response = self.client.get(topcrasher_report_url)
        eq_(response.status_code, 200)

        # now, go back to the home page, and 'report' should be the new default
        response = self.client.get(url)
        eq_(response.status_code, 200)
        for tag, value in regex.findall(response.content):
            if value == 'build':
                ok_('selected' in tag)
            else:
                ok_('selected' not in tag)
