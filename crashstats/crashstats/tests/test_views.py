import csv
import json
from cStringIO import StringIO
import mock
from nose.tools import eq_, ok_
from django.test import TestCase
from django.test.client import RequestFactory
from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.models import User


class Response(object):
    def __init__(self, content=None, status_code=200):
        self.content = content
        self.status_code = status_code


class TestViews(TestCase):

    @mock.patch('requests.get')
    def setUp(self, rget):
        super(TestViews, self).setUp()

        # checking settings.CACHES isn't as safe as `cache.__class__`
        if 'LocMemCache' not in cache.__class__.__name__:
            raise ImproperlyConfigured(
                'The tests requires that you use LocMemCache when running'
            )

        # we do this here so that the current/versions thing
        # is cached since that's going to be called later
        # in every view more or less
        def mocked_get(url, **options):
            if 'current/versions' in url:
                return Response("""
                    {"currentversions": [
                     {"product": "Firefox",
                      "throttle": "100.00",
                      "end_date": "2012-05-10T00:00:00",
                      "start_date": "2012-03-08T00:00:00",
                      "featured": true,
                      "version": "19.0",
                      "release": "Beta",
                      "id": 922},
                     {"product": "Firefox",
                      "throttle": "100.00",
                      "end_date": "2012-05-10T00:00:00",
                      "start_date": "2012-03-08T00:00:00",
                      "featured": true,
                      "version": "18.0",
                      "release": "Stable",
                      "id": 920},
                     {"product": "Firefox",
                      "throttle": "100.00",
                      "end_date": "2012-05-10T00:00:00",
                      "start_date": "2012-03-08T00:00:00",
                      "featured": true,
                      "version": "20.0",
                      "release": "Nightly",
                      "id": 923},
                      {"product": "Thunderbird",
                      "throttle": "100.00",
                      "end_date": "2012-05-10T00:00:00",
                      "start_date": "2012-03-08T00:00:00",
                      "featured": true,
                      "version": "18.0",
                      "release": "Aurora",
                      "id": 924},
                     {"product": "Thunderbird",
                      "throttle": "100.00",
                      "end_date": "2012-05-10T00:00:00",
                      "start_date": "2012-03-08T00:00:00",
                      "featured": true,
                      "version": "19.0",
                      "release": "Nightly",
                      "id": 925},
                     {"product": "Camino",
                      "throttle": "99.00",
                      "end_date": "2012-05-10T00:00:00",
                      "start_date": "2012-03-08T00:00:00",
                      "featured": true,
                      "version": "9.5",
                      "release": "Alpha",
                      "id": 921}]
                      }
                      """)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get
        from crashstats.crashstats.models import CurrentVersions
        api = CurrentVersions()
        api.get()

    def tearDown(self):
        super(TestViews, self).tearDown()
        cache.clear()

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
            if 'products' in url:
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
                        "WaterWolf:2.1": {
                          "2012-10-08": {
                            "product": "WaterWolf",
                            "adu": 30000,
                            "crash_hadu": 71.099999999999994,
                            "version": "2.1",
                            "report_count": 2133,
                            "date": "2012-10-08"
                          },
                          "2012-10-02": {
                            "product": "WaterWolf",
                            "adu": 30000,
                            "crash_hadu": 77.299999999999997,
                            "version": "2.1",
                            "report_count": 2319,
                            "date": "2012-10-02"
                         }
                        }
                      }
                    }
                    """)

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        # Test that in the event that no params are passed set_base_data will
        # ensure that the default product is used as a fallback.
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.get(url, {'product': 'Firefox'})
        eq_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        ok_(struct['product_versions'])
        eq_(struct['count'], 1)

    @mock.patch('requests.get')
    def test_products_list(self, rget):
        url = reverse('crashstats.products_list')

        def mocked_get(url, **options):
            if 'products' in url:
                return Response("""
                {
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

        def mocked_get(**options):
            if 'crashtrends/start_date' in options['url']:
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
            'product': 'WaterWolf',
            'version': '5.0a1',
            'start_date': '2012-10-01',
            'end_date': '20120-10-10'
        })
        ok_(response.status_code, 200)
        ok_('application/json' in response['content-type'])
        struct = json.loads(response.content)
        eq_(struct['total'], 2)

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

    @mock.patch('requests.get')
    def test_daily(self, rget):
        url = reverse('crashstats.daily')

        def mocked_get(url, **options):
            if 'products' in url:
                return Response("""
                    {
                      "hits": [{
                        "sort": 0,
                        "default_version": "19.0",
                        "release_name": "firefox",
                        "rapid_release_version": "5.0",
                        "product_name": "Firefox"
                      },{
                        "sort": 1,
                        "default_version": "18.0",
                        "release_name":"Thunderbird",
                        "rapid_release_version": "5.0",
                        "product_name": "Thunderbird"}],
                      "total": 2}
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

        response = self.client.get(url, {'p': 'Firefox'})
        eq_(response.status_code, 200)
        # XXX any basic tests with can do on response.content?

        # check that the CSV version is working too
        response = self.client.get(url, {'p': 'Firefox', 'format': 'csv'})
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/csv')

        # also, I should be able to read it
        reader = csv.reader(response)
        ok_(list(reader))

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
                    }
                    ],
                    "total": 3
                } """)
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
        ok_('table id="signatures-list"' not in response.content)

        response = self.client.get(url, {'product': 'Firefox'})
        eq_(response.status_code, 200)
        ok_('<h2>Query Results</h2>' in response.content)
        ok_('table id="signatures-list"' in response.content)
        ok_('nsASDOMWindowEnumerator::GetNext()' in response.content)
        ok_('mySignatureIsCool' in response.content)
        ok_('mineIsCoolerThanYours' in response.content)

        response = self.client.get(url, {'query': 'nsASDOMWindowEnumerator'})
        eq_(response.status_code, 200)
        ok_('<h2>Query Results</h2>' in response.content)
        ok_('table id="signatures-list"' in response.content)
        ok_('nsASDOMWindowEnumerator::GetNext()' in response.content)
        ok_('123456' in response.content)

        # Test a simple search containing a ooid
        ooid = '1234abcd-ef56-7890-ab12-abcdef123456'
        response = self.client.get(url, {
            'query': ooid,
            'query_type': 'simple'
        })
        eq_(response.status_code, 302)
        ok_(ooid in response['Location'])

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
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)

        # invalid version for the product name
        response = self.client.get(bad_url)
        eq_(response.status_code, 404)

        # invalid version for the product name
        response = self.client.get(bad_url2)
        eq_(response.status_code, 404)

        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_hangreport(self, rget):
        def mocked_get(url, **options):
            if 'current/versions' in url:
                return Response("""
                    {"currentversions": [{
                      "product": "Firefox",
                      "throttle": "100.00",
                      "end_date": "2012-05-10T00:00:00",
                      "start_date": "2012-03-08T00:00:00",
                      "featured": true,
                      "version": "19.0",
                      "release": "Beta",
                      "id": 922}]
                      }
                  """)
            if 'reports/hang' in url:
                browser_signature = (
                    'hang | mozilla::plugins::PPluginInstance'
                    'Parent::CallNPP_HandleEvent(mozilla::plugins::NPRemoteEve'
                    'nt const&, short*)'
                )
                return Response("""
                {"currentPage": 1,
                 "endDate": "2012-06-01T00:00:00+00:00",
                 "hangReport": [{
                   "browser_hangid": "30a712a4-6512-479d-9a0a-48b4d8c7ca13",
                   "browser_signature": "%s",
                   "duplicates": [
                     null,
                     null,
                     null
                   ],
                   "flash_version": "11.3.300.250",
                   "plugin_signature": "hang | ZwYieldExecution",
                   "report_day": "2012-05-31",
                   "url": "http://example.com",
                   "uuid": "176bcd6c-c2ec-4b0c-9d5f-dadea2120531"
                   }],
                 "totalCount": 1,
                 "totalPages": 1}
                """ % browser_signature)

            raise NotImplementedError(url)

        url = reverse('crashstats.hangreport', args=('Firefox', '19.0'))
        url_wo_version = reverse('crashstats.hangreport',
                                 args=('Firefox',))

        rget.side_effect = mocked_get

        response = self.client.get(url_wo_version)
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('text/html' in response['content-type'])

        # if you try to fake the page you get redirect back
        response = self.client.get(url, {'page': 9})
        eq_(response.status_code, 302)

        response = self.client.get(url, {'page': ''})
        eq_(response.status_code, 400)

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

        response = self.client.get(url, {'range_value': '1'})
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

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_report_index(self, rget, rpost):
        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod"
        comment0 = "This is a comment"
        email0 = "some@emailaddress.com"

        def mocked_get(url, **options):
            if 'crash/meta' in url:
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
              """ % (comment0, email0))

            if 'crash/processed' in url:
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

        # the email address will appear if we log in
        User.objects.create_user('test', 'test@mozilla.com', 'secret')
        assert self.client.login(username='test', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(email0 in response.content)

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

        response = self.client.get(url, {'range_value': 'xxx'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'range_value': 3})
        eq_(response.status_code, 200)

        ok_('0xdeadbeef' in response.content)
        ok_('I LOVE CHEESE' in response.content)
        ok_('bob@uncle.com' not in response.content)

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
        response = self.client.get(url, {'range_value': 3})
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
        response = self.client.get(url, {'range_value': 3})
        eq_(response.status_code, 200)
        ok_('http://farm.ville' not in response.content)
        ok_('bob@uncle.com' not in response.content)

        User.objects.create_user('test', 'test@mozilla.com', 'secret')
        assert self.client.login(username='test', password='secret')

        url = reverse('crashstats.report_list')
        response = self.client.get(url, {'range_value': 3})
        eq_(response.status_code, 200)
        # now it suddenly appears when we're logged in
        ok_('http://farm.ville' in response.content)
        ok_('bob@uncle.com' in response.content)
        # not too long...
        ok_(really_long_url[:80 - 3] + '...' in response.content)

    @mock.patch('requests.get')
    def test_raw_data(self, rget):

        def mocked_get(url, **options):
            if 'crash/meta/by/uuid' in url:
                return Response("""
                  {"foo": "bar",
                   "stuff": 123}
                """)
            if 'crash/raw_crash/by/uuid' in url:
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

        dump_url = reverse('crashstats.raw_data', args=(crash_id, 'dump'))
        response = self.client.get(dump_url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/octet-stream')
        ok_('bla bla bla' in response.content)

        # dump files are cached.
        # check the mock function and expect no change
        def different_mocked_get(url, **options):
            if 'crash/raw_crash/by/uuid' in url:
                return Response("""
                  SOMETHING DIFFERENT
                """.strip())
            raise NotImplementedError(url)

        rget.side_effect = different_mocked_get

        response = self.client.get(dump_url)
        eq_(response.status_code, 200)
        ok_('bla bla bla' in response.content)  # still. good.
