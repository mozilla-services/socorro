import mock
import pyquery
from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from waffle import Switch

from crashstats.crashstats.tests.test_views import BaseTestViews, Response
from crashstats.supersearch.tests.test_views import (
    SUPERSEARCH_FIELDS_MOCKED_RESULTS
)

DUMB_SIGNATURE = 'mozilla::wow::such_signature(smth*)'


class TestViews(BaseTestViews):

    @staticmethod
    def setUpClass():
        TestViews.switch = Switch.objects.create(
            name='signature-report',
            active=True,
        )

    @staticmethod
    def tearDownClass():
        TestViews.switch.delete()

    def test_waffle_switch(self):
        # Deactivate the switch to verify it's not accessible.
        TestViews.switch.active = False
        TestViews.switch.save()

        url = reverse('signature:signature_report')
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('signature:signature_reports')
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('signature:signature_aggregation', args=('some_agg',))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        TestViews.switch.active = True
        TestViews.switch.save()

    @mock.patch('requests.get')
    def test_signature_report(self, rget):

        def mocked_get(url, params, **options):
            assert 'supersearch' in url

            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

        rget.side_effect = mocked_get

        url = reverse('signature:signature_report')
        response = self.client.get(url, {'signature': DUMB_SIGNATURE})
        eq_(response.status_code, 200)
        ok_(DUMB_SIGNATURE in response.content)
        ok_('Loading' in response.content)

    @mock.patch('requests.get')
    def test_signature_reports(self, rget):
        def mocked_get(url, params, **options):
            assert 'supersearch' in url

            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

            ok_('signature' in params)
            eq_(params['signature'], '=' + DUMB_SIGNATURE)

            if 'product' in params:
                return Response({
                    "hits": [
                        {
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa1",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": 888981
                        },
                        {
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa2",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": 888981
                        },
                        {
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa3",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": None
                        },
                        {
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa4",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": None
                        }
                    ],
                    "total": 4
                })

            return Response({"hits": [], "total": 0})

        rget.side_effect = mocked_get

        url = reverse('signature:signature_reports')

        # Test with no results.
        response = self.client.get(url, {
            'signature': DUMB_SIGNATURE,
            'date': '2012-01-01',
        })
        eq_(response.status_code, 200)
        ok_('table id="reports-list"' not in response.content)
        ok_('No results were found' in response.content)

        # Test with results.
        response = self.client.get(url, {
            'signature': DUMB_SIGNATURE,
            'product': 'WaterWolf'
        })
        eq_(response.status_code, 200)
        ok_('table id="reports-list"' in response.content)
        ok_('aaaaaaaaaaaaa1' in response.content)
        ok_('888981' in response.content)
        ok_('Linux' in response.content)
        ok_('2017-01-31 23:12:57' in response.content)

        # Test with a different columns list.
        response = self.client.get(url, {
            'signature': DUMB_SIGNATURE,
            'product': 'WaterWolf',
            '_columns': ['build_id', 'platform'],
        })
        eq_(response.status_code, 200)
        ok_('table id="reports-list"' in response.content)
        # The build and platform appear
        ok_('888981' in response.content)
        ok_('Linux' in response.content)
        # The crash id is always shown
        ok_('aaaaaaaaaaaaa1' in response.content)
        # The version and date do not appear
        ok_('1.0' not in response.content)
        ok_('2017' not in response.content)

    @mock.patch('requests.get')
    def test_parameters(self, rget):
        def mocked_get(url, params, **options):
            assert 'supersearch' in url

            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

            # Verify that all expected parameters are in the URL.
            ok_('product' in params)
            ok_('WaterWolf' in params['product'])
            ok_('NightTrain' in params['product'])

            ok_('address' in params)
            ok_('0x0' in params['address'])
            ok_('0xa' in params['address'])

            ok_('reason' in params)
            ok_('^hello' in params['reason'])
            ok_('$thanks' in params['reason'])

            ok_('java_stack_trace' in params)
            ok_('Exception' in params['java_stack_trace'])

            return Response({
                "hits": [],
                "facets": "",
                "total": 0
            })

        rget.side_effect = mocked_get

        url = reverse('signature:signature_reports')

        response = self.client.get(
            url, {
                'signature': DUMB_SIGNATURE,
                'product': ['WaterWolf', 'NightTrain'],
                'address': ['0x0', '0xa'],
                'reason': ['^hello', '$thanks'],
                'java_stack_trace': 'Exception',
            }
        )
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_signature_reports_pagination(self, rget):
        """Test that the pagination of results works as expected.
        """
        def mocked_get(url, params, **options):
            assert 'supersearch' in url

            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

            # Make sure a negative page does not lead to negative offset value.
            # But instead it is considered as the page 1 and thus is not added.
            ok_('_results_offset' not in params)

            hits = []
            for i in range(140):
                hits.append({
                    "signature": "nsASDOMWindowEnumerator::GetNext()",
                    "date": "2017-01-31T23:12:57",
                    "uuid": i,
                    "product": "WaterWolf",
                    "version": "1.0",
                    "platform": "Linux",
                    "build_id": 888981
                })
            return Response({
                "hits": hits,
                "facets": "",
                "total": len(hits)
            })

        rget.side_effect = mocked_get

        url = reverse('signature:signature_reports')

        response = self.client.get(
            url,
            {
                'signature': DUMB_SIGNATURE,
                'product': ['WaterWolf'],
                '_columns': ['platform']
            }
        )

        eq_(response.status_code, 200)
        ok_('140' in response.content)

        # Check that the pagination URL contains all three expected parameters.
        doc = pyquery.PyQuery(response.content)
        next_page_url = str(doc('.pagination a').eq(0))
        ok_('product=WaterWolf' in next_page_url)
        ok_('_columns=platform' in next_page_url)
        ok_('page=2' in next_page_url)

        # Test that a negative page value does not break it.
        response = self.client.get(url, {
            'signature': DUMB_SIGNATURE,
            'page': '-1',
        })
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_signature_aggregation(self, rget):
        def mocked_get(url, params, **options):
            assert 'supersearch' in url

            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

            ok_('signature' in params)
            eq_(params['signature'], '=' + DUMB_SIGNATURE)

            ok_('_facets' in params)

            if 'product' in params['_facets']:
                return Response({
                    "hits": [],
                    "facets": {
                        "product": [
                            {
                                "term": "windows",
                                "count": 42,
                            },
                            {
                                "term": "linux",
                                "count": 1337,
                            },
                            {
                                "term": "mac",
                                "count": 3,
                            },
                        ]
                    },
                    "total": 1382
                })

            return Response({
                "hits": [],
                "facets": {
                    "platform": []
                },
                "total": 0
            })

        rget.side_effect = mocked_get

        # Test with no results.
        url = reverse(
            'signature:signature_aggregation',
            args=('platform',)
        )

        response = self.client.get(url, {'signature': DUMB_SIGNATURE})
        eq_(response.status_code, 200)
        ok_('Product' not in response.content)
        ok_('No results were found' in response.content)

        # Test with results.
        url = reverse(
            'signature:signature_aggregation',
            args=('product',)
        )

        response = self.client.get(url, {'signature': DUMB_SIGNATURE})
        eq_(response.status_code, 200)
        ok_('Product' in response.content)
        ok_('1337' in response.content)
        ok_('linux' in response.content)
        ok_(str(1337 / 1382 * 100) in response.content)
        ok_('windows' in response.content)
        ok_('mac' in response.content)
