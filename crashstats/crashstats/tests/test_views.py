import json
import mock
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
        if 'LocMemCache' not in settings.CACHES['default']['BACKEND']:
            raise ImproperlyConfigured(
                    'The tests requires that you use LocMemCache when running')

        # we do this here so that the current/versions thing
        # is cached since that's going to be called later
        # in every view more or less
        with mock.patch('requests.get') as rget:
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
                raise NotImplementedError(url)
            rget.side_effect = mocked_get
            from crashstats.crashstats.models import CurrentVersions
            api = CurrentVersions()
            api.get()

    def tearDown(self):
        super(TestViews, self).tearDown()
        cache.clear()

    def test_buginfo(self):
        url = reverse('crashstats.buginfo')

        with mock.patch('requests.get') as rget:
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
            if 'adu/byday' in url:
                return Response("""
                   {"product": "Thunderbird",
                    "start_date": "2012-05-29 00:00:00+00:00",
                    "end_date": "2012-05-30 00:00:00+00:00",
                    "versions": [{"statistics": [], "version": "12.0"}]
                    }
                """)

            raise NotImplementedError(url)

        with mock.patch('requests.get') as rget:

            rget.side_effect = mocked_get

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            # XXX: we should maybe do some light tests on the response.content
            # see mocked_get() above

            # now, let's do it with versions
            url = reverse('crashstats.products',
                          args=('Firefox', '12;13'))

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_topcrasher(self):
        url = reverse('crashstats.topcrasher',
                      args=('Firefox', '19'))

        def mocked_post(**options):
            assert 'by/signatures' in options['url'], options['url']
            return Response("""
               {"bug_associations": [{"bug_id": "123456789",
                                      "signature": "Something"}]}
            """)

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
            if 'crashes/signatures' in url:
                return Response("""
                   {"crashes": [],
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
            if 'adu/byday' in url:
                return Response("""
                   {"product": "Thunderbird",
                    "start_date": "2012-05-29 00:00:00+00:00",
                    "end_date": "2012-05-30 00:00:00+00:00",
                    "versions": [{"statistics": [], "version": "12.0"}]
                    }
                """)

            raise NotImplementedError(url)

        with mock.patch('requests.get') as rget:
            rget.side_effect = mocked_get

            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            # XXX any basic tests with can do on response.content?

    def test_query(self):
        url = reverse('crashstats.query')

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

    def test_signature_summary(self):
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

            # invalid range_value
            response = self.client.get(url, {'range_value': 'xxx'})
            self.assertEqual(response.status_code, 400)

            # invalid date
            response = self.client.get(url, {'range_value': '1',
                                             'date': '2012-02-33'})
            self.assertEqual(response.status_code, 400)

            # valid input
            response = self.client.get(url, {'range_value': '1',
                                             'date': '2012-02-13'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue('application/json' in response['content-type'])
            struct = json.loads(response.content)
            self.assertTrue(struct['architectures'])
            self.assertTrue(struct['flashVersions'])
            self.assertTrue(struct['percentageByOs'])
            self.assertTrue(struct['processTypes'])
            self.assertTrue(struct['productVersions'])
            self.assertTrue(struct['uptimeRange'])
