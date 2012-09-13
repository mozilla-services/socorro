import json
import mock
from nose.tools import eq_, ok_
from django.test import TestCase
from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured


class Response(object):
    def __init__(self, content=None, status_code=200):
        self.content = content
        self.status_code = status_code


class TestViews(TestCase):

    def setUp(self):
        super(TestViews, self).setUp()

        # checking settings.CACHES isn't as safe as `cache.__class__`
        if 'LocMemCache' not in cache.__class__.__name__:
            raise ImproperlyConfigured(
                'The tests requires that you use LocMemCache when running'
            )

        # we do this here so that the current/versions thing
        # is cached since that's going to be called later
        # in every view more or less
        with mock.patch('requests.get') as rget:
            def mocked_get(url, **options):
                if 'current/versions' in url:
                    return Response("""
                        {"currentversions": [
                         {"product": "Firefox",
                          "throttle": "100.00",
                          "end_date": "2012-05-10 00:00:00",
                          "start_date": "2012-03-08 00:00:00",
                          "featured": true,
                          "version": "19.0",
                          "release": "Beta",
                          "id": 922},
                         {"product": "Firefox",
                          "throttle": "100.00",
                          "end_date": "2012-05-10 00:00:00",
                          "start_date": "2012-03-08 00:00:00",
                          "featured": true,
                          "version": "18.0",
                          "release": "Stable",
                          "id": 920},
                         {"product": "Camino",
                          "throttle": "99.00",
                          "end_date": "2012-05-10 00:00:00",
                          "start_date": "2012-03-08 00:00:00",
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

    def test_homepage_redirect(self):
        response = self.client.get('/')
        eq_(response.status_code, 302)
        destination = reverse('crashstats.products',
                              args=[settings.DEFAULT_PRODUCT])
        ok_(destination in response['Location'])

    def test_buginfo(self):
        url = reverse('crashstats.buginfo')

        with mock.patch('requests.get') as rget:
            def mocked_get(url, **options):
                if 'bug?id=' in url:
                    return Response('{"bugs": [{"product": "allizom.org"}]}')

                raise NotImplementedError(url)

            rget.side_effect = mocked_get

            response = self.client.get(url)
            self.assertEqual(response.status_code, 400)

            response = self.client.get(url, {'bug_ids': '123,456'})
            self.assertEqual(response.status_code, 400)

            response = self.client.get(url, {'include_fields': 'product'})
            self.assertEqual(response.status_code, 400)

            response = self.client.get(url, {'bug_ids': ' 123, 456 ',
                                             'include_fields': ' product'})
            self.assertEqual(response.status_code, 200)

            struct = json.loads(response.content)
            self.assertTrue(struct['bugs'])
            self.assertEqual(struct['bugs'][0]['product'], 'allizom.org')

    def test_products(self):
        url = reverse('crashstats.products', args=('Firefox',))

        def mocked_get(url, **options):
            if 'crashes' in url:
                return Response("""
                {
                  "hits": {
                    "Firefox:17.0a1": {
                      "2012-08-23": {
                        "adu": "80388",
                        "crash_hadu": "12.279",
                        "date": "2012-08-23",
                        "product": "Firefox",
                        "report_count": "9871",
                        "version": "17.0a1"
                      }
                    }
                  }
                }
                """)

            raise NotImplementedError(url)

        with mock.patch('requests.get') as rget:

            rget.side_effect = mocked_get

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            # XXX: we should maybe do some light tests on the response.content
            # see mocked_get() above

            # now, let's do it with crazy versions
            url = reverse('crashstats.products',
                          args=('Firefox', '19.0;99'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)

            # more crazy versions
            url = reverse('crashstats.products',
                          args=('Firefox', '99'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)

            # now, let's do it with good versions
            url = reverse('crashstats.products',
                          args=('Firefox', '18.0;19.0'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_products_with_unrecognized_product(self):
        url = reverse('crashstats.products', args=('NeverHeardOf',))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_topcrasher(self):
        # first without a version
        no_version_url = reverse('crashstats.topcrasher',
                                 args=('Firefox',))
        url = reverse('crashstats.topcrasher',
                      args=('Firefox', '19.0'))
        response = self.client.get(no_version_url)
        ok_(url in response['Location'])

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
                      "first_report_exact": "2012-06-21 21:28:08",
                      "versions": "2.0, 2.1, 3.0a2, 3.0b2, 3.1b1, 4.0a1, 4.0a2, 5.0a1",
                      "percentOfTotal": 0.24258064516128999,
                      "win_count": 56,
                      "changeInPercentOfTotal": 0.011139597126354983,
                      "linux_count": 66,
                      "hang_count": 0,
                      "signature": "FakeSignature1",
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
            raise NotImplementedError(url)

        with mock.patch('requests.post') as rpost:
            rpost.side_effect = mocked_post
            with mock.patch('requests.get') as rget:
                rget.side_effect = mocked_get

                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_daily(self):
        url = reverse('crashstats.daily')

        def mocked_get(url, **options):
            if 'current/versions' in url:

                return Response("""
                    {"currentversions": [{
                      "product": "Firefox",
                      "throttle": "100.00",
                      "end_date": "2012-05-10 00:00:00",
                      "start_date": "2012-03-08 00:00:00",
                      "featured": true,
                      "version": "19.0",
                      "release": "Beta",
                      "id": 922}]
                      }
                  """)
            if 'crashes' in url:
                return Response("""
                       {
                         "hits": {
                           "Firefox:17.0a1": {
                             "2012-08-23": {
                               "adu": "80388",
                               "crash_hadu": "12.279",
                               "date": "2012-08-23",
                               "product": "Firefox",
                               "report_count": "9871",
                               "version": "17.0a1"
                             }
                           }
                         }
                       }

                """)

            raise NotImplementedError(url)

        with mock.patch('requests.get') as rget:
            rget.side_effect = mocked_get

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            # XXX any basic tests with can do on response.content?

    def test_builds(self):
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

        with mock.patch('requests.get') as rget:
            rget.side_effect = mocked_get
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue('20120625000001' in response.content)
            self.assertTrue('20120625000002' in response.content)
            # the not, build_type==Nightly
            self.assertTrue('20120625000003' not in response.content)

            rss_response = self.client.get(rss_url)
            self.assertEquals(rss_response.status_code, 200)
            self.assertEquals(rss_response['Content-Type'],
                              'application/rss+xml; charset=utf-8')
            self.assertTrue('20120625000001' in rss_response.content)
            self.assertTrue('20120625000002' in rss_response.content)
            # the not, build_type==Nightly
            self.assertTrue('20120625000003' not in rss_response.content)

    def test_builds_by_old_version(self):
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

        with mock.patch('requests.get') as rget:
            rget.side_effect = mocked_get
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            header = response.content.split('<h2')[1].split('</h2>')[0]
            self.assertTrue('18.0' in header)

    def test_query(self):
        url = reverse('crashstats.query')

        def mocked_get(url, **options):
            if 'search/signatures' in url:
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

            raise NotImplementedError(url)

        with mock.patch('requests.get') as rget:
            rget.side_effect = mocked_get

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            # XXX any basic tests with can do on response.content?

    def test_plot_signature(self):
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

        with mock.patch('requests.get') as rget:
            rget.side_effect = mocked_get

            # invalid start date
            url = reverse('crashstats.plot_signature',
                          args=('Firefox', '19.0',
                                '2012-02-33', '2012-12-01',
                                'Read::Bytes'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 400)

            # invalid end date
            url = reverse('crashstats.plot_signature',
                          args=('Firefox', '19.0',
                                '2012-02-28', '2012-13-01',
                                'Read::Bytes'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 400)

            # valid dates
            url = reverse('crashstats.plot_signature',
                          args=('Firefox', '19.0',
                                '2011-12-01', '2011-12-02',
                                'Read::Bytes'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue('application/json' in response['content-type'])
            struct = json.loads(response.content)
            self.assertTrue(struct['signature'])

    def test_topchangers(self):
        url = reverse('crashstats.topchangers',
                      args=('Firefox', '19.0'))

        url_duration = reverse('crashstats.topchangers',
                               args=('Firefox', '19.0', '7'))

        bad_url_duration = reverse('crashstats.topchangers',
                                   args=('Firefox', '19.0', '111'))

        bad_url = reverse('crashstats.topchangers',
                      args=('Camino', '19.0'))

        bad_url2 = reverse('crashstats.topchangers',
                      args=('Firefox', '19.999'))

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
                      "first_report_exact": "2012-06-21 21:28:08",
                      "versions": "2.0, 2.1, 3.0a2, 3.0b2, 3.1b1, 4.0a1, 4.0a2, 5.0a1",
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

        with mock.patch('requests.post') as rpost:
            rpost.side_effect = mocked_post
            with mock.patch('requests.get') as rget:
                rget.side_effect = mocked_get

                # invalid version for the product name
                response = self.client.get(bad_url)
                self.assertEqual(response.status_code, 404)

                # invalid version for the product name
                response = self.client.get(bad_url2)
                self.assertEqual(response.status_code, 404)

                # valid response
                response = self.client.get(url_duration)
                self.assertEqual(response.status_code, 200)

                # an integer but not one we can accept
                response = self.client.get(bad_url_duration)
                self.assertEqual(response.status_code, 400)

                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_hangreport(self):
        def mocked_get(url, **options):
            if 'current/versions' in url:
                return Response("""
                    {"currentversions": [{
                      "product": "Firefox",
                      "throttle": "100.00",
                      "end_date": "2012-05-10 00:00:00",
                      "start_date": "2012-03-08 00:00:00",
                      "featured": true,
                      "version": "19.0",
                      "release": "Beta",
                      "id": 922}]
                      }
                  """)
            if 'reports/hang' in url:
                return Response("""
                {"currentPage": 1,
                 "endDate": "2012-06-01 00:00:00+00:00",
                 "hangReport": [{
                   "browser_hangid": "30a712a4-6512-479d-9a0a-48b4d8c7ca13",
                   "browser_signature": "hang | mozilla::plugins::PPluginInstanceParent::CallNPP_HandleEvent(mozilla::plugins::NPRemoteEvent const&, short*)",
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
                """)

            raise NotImplementedError(url)

        url = reverse('crashstats.hangreport', args=('Firefox', '19.0'))

        with mock.patch('requests.get') as rget:
            rget.side_effect = mocked_get

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue('text/html' in response['content-type'])

            # if you try to fake the page you get redirect back
            response = self.client.get(url, {'page': 9})
            self.assertEqual(response.status_code, 302)

            response = self.client.get(url, {'page': ''})
            self.assertEqual(response.status_code, 400)

            response = self.client.get(url, {'duration': 'xxx'})
            self.assertEqual(response.status_code, 400)

            response = self.client.get(url, {'duration': 999})
            self.assertEqual(response.status_code, 400)

    def test_signature_summary(self):
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

        with mock.patch('requests.get') as rget:
            rget.side_effect = mocked_get

            response = self.client.get(url, {'range_value': '1'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue('application/json' in response['content-type'])
            struct = json.loads(response.content)
            self.assertTrue(struct['architectures'])
            self.assertTrue(struct['flashVersions'])
            self.assertTrue(struct['percentageByOs'])
            self.assertTrue(struct['processTypes'])
            self.assertTrue(struct['productVersions'])
            self.assertTrue(struct['uptimeRange'])

    @mock.patch('requests.get')
    def test_report_index(self, rget):
        dump = "OS|Mac OS X|10.6.8 10K549\\nCPU|amd64|family 6 mod"
        comment0 = "This is a comment"
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
                     "date_processed": "2012-08-21 11:17:28.388291-07:00",
                     "email": "socorro-12109@restmail.net",
                     "uuid": "469bde48-0e8f-3586-d486-b98810120830"
                    }
                  ],
                  "total": 1
                }
              """ % comment0)

            if 'crash/processed' in url:
                return Response("""
                {
                  "client_crash_date": "2012-06-11 06:08:45.0",
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
                  "date_processed": "2012-06-11 06:08:44.478797",
                  "cpu_name": "amd64",
                  "reason": "EXC_BAD_ACCESS / KERN_INVALID_ADDRESS",
                  "address": "0x8",
                  "completeddatetime": "2012-06-11 06:08:57.58750",
                  "success": true
                }
                """ % dump)

            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('crashstats.report_index',
                      args=['11cb72f5-eb28-41e1-a8e4-849982120611'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('FakeSignature1' in response.content)
        self.assertTrue('11cb72f5-eb28-41e1-a8e4-849982120611'
                        in response.content)
        self.assertTrue(comment0 in response.content)
