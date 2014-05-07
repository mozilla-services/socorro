import datetime
import json
import mock
import pyquery
from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse
from django.utils.timezone import utc

from waffle import Switch

from crashstats.crashstats.tests.test_views import BaseTestViews, Response
from crashstats.supersearch.views import get_report_list_parameters


SUPERSEARCH_FIELDS_MOCKED_RESULTS = {
    'signature': {
        'name': 'signature',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_type': 'StringField',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'product': {
        'name': 'product',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_type': 'MultipleValueField',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'version': {
        'name': 'version',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_type': 'MultipleValueField',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'platform': {
        'name': 'platform',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_type': 'MultipleValueField',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'dump': {
        'name': 'dump',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_type': 'MultipleValueField',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': False,
        'is_mandatory': False,
    },
    'release_channel': {
        'name': 'release_channel',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_type': 'MultipleValueField',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'date': {
        'name': 'date',
        'query_type': 'datetime',
        'namespace': 'processed_crash',
        'form_field_type': 'DateTimeField',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'address': {
        'name': 'address',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_type': 'StringField',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'build_id': {
        'name': 'build_id',
        'query_type': 'int',
        'namespace': 'processed_crash',
        'form_field_type': 'IntegerField',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'reason': {
        'name': 'reason',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_type': 'StringField',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'java_stack_trace': {
        'name': 'java_stack_trace',
        'query_type': 'enum',
        'namespace': 'processed_crash',
        'form_field_type': 'MultipleValueField',
        'form_field_choices': None,
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'email': {
        'name': 'email',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_type': 'StringField',
        'form_field_choices': None,
        'permissions_needed': ['crashstats.view_pii'],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'url': {
        'name': 'url',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_type': 'StringField',
        'form_field_choices': None,
        'permissions_needed': ['crashstats.view_pii'],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'exploitability': {
        'name': 'exploitability',
        'query_type': 'str',
        'namespace': 'processed_crash',
        'form_field_type': 'MultipleValueField',
        'form_field_choices': [
            'high', 'normal', 'low', 'none', 'unknown', 'error'
        ],
        'permissions_needed': ['crashstats.view_exploitability'],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
}


class TestViews(BaseTestViews):

    @staticmethod
    def setUpClass():
        TestViews.switch = Switch.objects.create(
            name='supersearch-all',
            active=True,
        )

        TestViews.custom_switch = Switch.objects.create(
            name='supersearch-custom-query',
            active=True,
        )

    @staticmethod
    def tearDownClass():
        try:
            TestViews.switch.delete()
            TestViews.custom_switch.delete()
        except AssertionError:
            # test_search_waffle_switch removes those switches before, causing
            # this error
            pass

    def test_search_waffle_switch(self):
        # Delete the custom-query switch but keep the generic one around.
        TestViews.custom_switch.delete()
        url = reverse('supersearch.search_custom')
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('supersearch.search_query')
        response = self.client.get(url)
        eq_(response.status_code, 404)

        # delete the switch to verify it's not accessible
        TestViews.switch.delete()

        url = reverse('supersearch.search')
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('supersearch.search_results')
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('supersearch.search_fields')
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('supersearch.search_custom')
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('supersearch.search_query')
        response = self.client.get(url)
        eq_(response.status_code, 404)

    @mock.patch('requests.get')
    def test_search(self, rget):

        def mocked_get(url, params, **options):
            assert 'supersearch' in url

            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

        rget.side_effect = mocked_get

        self._login()
        url = reverse('supersearch.search')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Run a search to get some results' in response.content)

    @mock.patch('requests.get')
    def test_search_fields(self, rget):

        def mocked_get(url, params, **options):
            assert 'supersearch' in url

            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

        rget.side_effect = mocked_get

        self._login()
        url = reverse('supersearch.search_fields')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(json.loads(response.content))  # Verify it's valid JSON
        ok_('WaterWolf' in response.content)
        ok_('SeaMonkey' in response.content)
        ok_('NightTrain' in response.content)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_search_results(self, rget, rpost):
        def mocked_post(url, **options):
            assert 'bugs' in url, url
            return Response({
                "hits": [
                    {
                        "id": "123456",
                        "signature": "nsASDOMWindowEnumerator::GetNext()"
                    }
                ],
                "total": 1
            })

        def mocked_get(url, params, **options):
            assert 'supersearch' in url

            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

            if 'product' in params and 'WaterWolf' in params['product']:
                return Response({
                    "hits": [
                        {
                            "signature": "nsASDOMWindowEnumerator::GetNext()",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa1",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": 888981
                        },
                        {
                            "signature": "mySignatureIsCool",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa2",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": 888981
                        },
                        {
                            "signature": "mineIsCoolerThanYours",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa3",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": None
                        },
                        {
                            "signature": "EMPTY",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa4",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": None
                        }
                    ],
                    "facets": {
                        "signature": [
                            {
                                "term": "nsASDOMWindowEnumerator::GetNext()",
                                "count": 1
                            },
                            {
                                "term": "mySignatureIsCool",
                                "count": 1
                            },
                            {
                                "term": "mineIsCoolerThanYours",
                                "count": 1
                            },
                            {
                                "term": "EMPTY",
                                "count": 1
                            }
                        ]
                    },
                    "total": 4
                })
            elif 'product' in params and 'SeaMonkey' in params['product']:
                return Response({
                    "hits": [
                        {
                            "signature": "nsASDOMWindowEnumerator::GetNext()",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": 888981
                        },
                        {
                            "signature": "mySignatureIsCool",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": 888981
                        }
                    ],
                    "facets": {
                        "build_id": [
                            {
                                "term": "888981",
                                "count": 2
                            }
                        ]
                    },
                    "total": 2
                })
            elif (
                'signature' in params and
                '~nsASDOMWindowEnumerator' in params['signature']
            ):
                return Response({
                    "hits": [
                        {
                            "signature": "nsASDOMWindowEnumerator::GetNext()",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": 12345678
                        }
                    ],
                    "facets": {
                        "signature": [
                            {
                                "term": "nsASDOMWindowEnumerator::GetNext()",
                                "count": 1
                            }
                        ]
                    },
                    "total": 1
                })
            else:
                return Response({"hits": [], "facets": [], "total": 0})

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get

        url = reverse('supersearch.search_results')
        response = self.client.get(
            url,
            {'product': 'WaterWolf'}
        )
        eq_(response.status_code, 200)
        # Test results are existing
        ok_('table id="reports-list"' in response.content)
        ok_('nsASDOMWindowEnumerator::GetNext()' in response.content)
        ok_('mySignatureIsCool' in response.content)
        ok_('mineIsCoolerThanYours' in response.content)
        ok_('EMPTY' in response.content)
        ok_('aaaaaaaaaaaaa1' in response.content)
        ok_('888981' in response.content)
        ok_('Linux' in response.content)
        ok_('2017-01-31 23:12:57' in response.content)
        # Test facets are existing
        ok_('table id="facets-list"' in response.content)
        # Test bugs are existing
        ok_('<th scope="col">Bugs</th>' in response.content)
        ok_('123456' in response.content)
        # Test links on terms are existing
        ok_('product=%3DWaterWolf' in response.content)

        # Test with empty results
        response = self.client.get(url, {
            'product': 'NightTrain',
            'date': '2012-01-01'
        })
        eq_(response.status_code, 200)
        ok_('table id="reports-list"' not in response.content)
        ok_('No results were found' in response.content)

        # Test with a signature param
        response = self.client.get(
            url,
            {'signature': '~nsASDOMWindowEnumerator'}
        )
        eq_(response.status_code, 200)
        ok_('table id="reports-list"' in response.content)
        ok_('nsASDOMWindowEnumerator::GetNext()' in response.content)
        ok_('123456' in response.content)

        # Test with a different facet
        response = self.client.get(
            url,
            {'_facets': 'build_id', 'product': 'SeaMonkey'}
        )
        eq_(response.status_code, 200)
        ok_('table id="reports-list"' in response.content)
        ok_('table id="facets-list"' in response.content)
        ok_('888981' in response.content)
        # Bugs should not be there, they appear only in the signature facet
        ok_('<th>Bugs</th>' not in response.content)
        ok_('123456' not in response.content)

        # Test with a different columns list
        response = self.client.get(
            url,
            {'_columns': ['build_id', 'platform'], 'product': 'WaterWolf'}
        )
        eq_(response.status_code, 200)
        ok_('table id="reports-list"' in response.content)
        ok_('table id="facets-list"' in response.content)
        # The build and platform appear
        ok_('888981' in response.content)
        ok_('Linux' in response.content)
        # The crash id is always shown
        ok_('aaaaaaaaaaaaa1' in response.content)
        # The version and date do not appear
        ok_('1.0' not in response.content)
        ok_('2017' not in response.content)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_search_results_admin_mode(self, rget, rpost):
        """Test that an admin can see more fields, and that a non-admin cannot.
        """
        def mocked_post(**options):
            assert 'bugs' in options['url'], options['url']
            return Response({"hits": [], "total": 0})

        def mocked_get(url, params, **options):
            assert 'supersearch' in url

            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

            if '_facets' in params and 'url' in params['_facets']:
                facets = {
                    "platform": [
                        {
                            "term": "Linux",
                            "count": 3
                        }
                    ],
                    "url": [
                        {
                            "term": "http://example.org",
                            "count": 3
                        }
                    ]
                }
            else:
                facets = {
                    "platform": [
                        {
                            "term": "Linux",
                            "count": 3
                        }
                    ]
                }

            return Response({
                "hits": [
                    {
                        "signature": "nsASDOMWindowEnumerator::GetNext()",
                        "date": "2017-01-31T23:12:57",
                        "uuid": "aaaaaaaaaaaaa1",
                        "product": "WaterWolf",
                        "version": "1.0",
                        "platform": "Linux",
                        "build_id": 888981,
                        "email": "bob@example.org",
                        "url": "http://example.org",
                        "exploitability": "high"
                    },
                    {
                        "signature": "mySignatureIsCool",
                        "date": "2017-01-31T23:12:57",
                        "uuid": "aaaaaaaaaaaaa2",
                        "product": "WaterWolf",
                        "version": "1.0",
                        "platform": "Linux",
                        "build_id": 888981,
                        "email": "bob@example.org",
                        "url": "http://example.org",
                        "exploitability": "low"
                    },
                    {
                        "signature": "mineIsCoolerThanYours",
                        "date": "2017-01-31T23:12:57",
                        "uuid": "aaaaaaaaaaaaa3",
                        "product": "WaterWolf",
                        "version": "1.0",
                        "platform": "Linux",
                        "build_id": None,
                        "email": "bob@example.org",
                        "url": "http://example.org",
                        "exploitability": "error"
                    }
                ],
                "facets": facets,
                "total": 3
            })

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get

        url = reverse('supersearch.search_results')

        # Logged in user, can see the email field
        user = self._login()
        group = self._create_group_with_permission('view_pii')
        user.groups.add(group)

        response = self.client.get(
            url,
            {
                '_columns': ['version', 'email', 'url', 'exploitability'],
                '_facets': ['url', 'platform']
            }
        )

        eq_(response.status_code, 200)
        ok_('Email' in response.content)
        ok_('bob@example.org' in response.content)
        ok_('Url facet' in response.content)
        ok_('http://example.org' in response.content)
        ok_('Version' in response.content)
        ok_('1.0' in response.content)

        # Without the correct permission the user cannot see exploitability.
        ok_('Exploitability' not in response.content)

        exp_group = self._create_group_with_permission('view_exploitability')
        user.groups.add(exp_group)

        response = self.client.get(
            url,
            {
                '_columns': ['version', 'email', 'url', 'exploitability'],
                '_facets': ['url', 'platform']
            }
        )

        eq_(response.status_code, 200)
        ok_('Email' in response.content)
        ok_('Exploitability' in response.content)
        ok_('high' in response.content)

        # Logged out user, cannot see the email field
        self._logout()
        response = self.client.get(
            url,
            {
                '_columns': ['version', 'email', 'url'],
                '_facets': ['url', 'platform']
            }
        )

        eq_(response.status_code, 200)
        ok_('Email' not in response.content)
        ok_('bob@example.org' not in response.content)
        ok_('Url facet' not in response.content)
        ok_('http://example.org' not in response.content)
        ok_('Version' in response.content)
        ok_('1.0' in response.content)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_search_results_parameters(self, rget, rpost):
        def mocked_post(**options):
            assert 'bugs' in options['url'], options['url']
            return Response({
                "hits": [],
                "total": 0
            })

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

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get

        url = reverse('supersearch.search_results')

        response = self.client.get(
            url, {
                'product': ['WaterWolf', 'NightTrain'],
                'address': ['0x0', '0xa'],
                'reason': ['^hello', '$thanks'],
                'java_stack_trace': 'Exception',
            }
        )
        eq_(response.status_code, 200)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_search_results_pagination(self, rget, rpost):
        """Test that the pagination of results works as expected.
        """
        def mocked_post(**options):
            assert 'bugs' in options['url'], options['url']
            return Response("""
                {"hits": [], "total": 0}
            """)

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

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get

        url = reverse('supersearch.search_results')

        response = self.client.get(
            url,
            {
                '_columns': ['version'],
                '_facets': ['platform']
            }
        )

        eq_(response.status_code, 200)
        ok_('140' in response.content)

        # Check that the pagination URL contains all three expected parameters.
        doc = pyquery.PyQuery(response.content)
        next_page_url = str(doc('.pagination a').eq(0))
        ok_('_facets=platform' in next_page_url)
        ok_('_columns=version' in next_page_url)
        ok_('page=2' in next_page_url)

        # Test that a negative page value does not break it.
        response = self.client.get(url, {'page': '-1'})
        eq_(response.status_code, 200)

    def test_get_report_list_parameters(self):
        source = {
            'date': ['<2013-01-01T10:00:00+00:00']
        }
        res = get_report_list_parameters(source)
        eq_(res['date'], datetime.datetime(2013, 1, 1, 10).replace(tzinfo=utc))
        ok_('range_value' not in res)
        ok_('range_unit' not in res)

        source = {
            'date': ['>=2013-01-01T10:00:00+00:00']
        }
        res = get_report_list_parameters(source)
        eq_(res['date'].date(), datetime.datetime.utcnow().date())
        ok_('range_value' in res)
        eq_(res['range_unit'], 'hours')

        source = {
            'date': [
                '>2013-01-01T10:00:00+00:00',
                '<2013-02-01T10:00:00+00:00'
            ],
            'product': ['WaterWolf'],
            'version': ['3.0b1', '4.0a', '5.1'],
            'release_channel': 'aurora',
            'build_id': ['12345', '~67890'],
        }
        res = get_report_list_parameters(source)
        eq_(res['date'].date(), datetime.date(2013, 2, 1))
        ok_('range_value' in res)
        ok_(res['range_unit'], 'hours')

        eq_(res['release_channels'], 'aurora')
        ok_('release_channel' not in res)
        eq_(res['product'], ['WaterWolf'])
        eq_(
            res['version'],
            ['WaterWolf:3.0b1', 'WaterWolf:4.0a', 'WaterWolf:5.1']
        )

        eq_(res['build_id'], ['12345'])

    def create_custom_query_perm(self):
        user = self._login()
        group = self._create_group_with_permission('run_custom_queries')
        user.groups.add(group)

    @mock.patch('requests.get')
    def test_search_custom_permission(self, rget):

        def mocked_get(url, params, **options):
            assert 'supersearch' in url

            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

            return Response()

        rget.side_effect = mocked_get

        url = reverse('supersearch.search_custom')

        response = self.client.get(url)
        eq_(response.status_code, 302)

        self.create_custom_query_perm()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Run a search to get some results' in response.content)

    @mock.patch('requests.get')
    def test_search_custom(self, rget):

        def mocked_get(url, params, **options):
            assert 'supersearch' in url

            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

            return Response()

        rget.side_effect = mocked_get

        self.create_custom_query_perm()

        url = reverse('supersearch.search_custom')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Run a search to get some results' in response.content)

    @mock.patch('requests.get')
    def test_search_custom_parameters(self, rget):
        self.create_custom_query_perm()

        def mocked_get(url, params, **options):
            if '/supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

            if '/supersearch' in url:
                ok_('_return_query' in params)
                ok_('signature' in params)
                eq_(params['signature'], ['nsA'])

                return Response({
                    "query": {"query": None},
                    "indices": ["socorro200000", "socorro200001"]
                })

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('supersearch.search_custom')
        response = self.client.get(url, {'signature': 'nsA'})
        eq_(response.status_code, 200)
        ok_('Run a search to get some results' in response.content)
        ok_('{&#34;query&#34;: null}' in response.content)
        ok_('socorro200000' in response.content)
        ok_('socorro200001' in response.content)

    @mock.patch('requests.get')
    @mock.patch('requests.post')
    def test_search_query(self, rget, rpost):
        self.create_custom_query_perm()

        def mocked_get(url, params, **options):
            if 'supersearch/fields' in url:
                return Response(SUPERSEARCH_FIELDS_MOCKED_RESULTS)

            return Response('{"hits": []}')

        def mocked_post(url, data, **options):
            ok_('/query' in url)
            ok_('query' in data)
            ok_('indices' in data)

            return Response({"hits": []})

        rget.side_effect = mocked_get
        rpost.side_effect = mocked_post

        url = reverse('supersearch.search_query')
        response = self.client.post(url, {'query': '{"query": {}}'})
        eq_(response.status_code, 200)

        content = json.loads(response.content)
        ok_('hits' in content)
        eq_(content['hits'], [])

        # Test a failure.
        response = self.client.post(url)
        eq_(response.status_code, 400)
        ok_('query' in response.content)
