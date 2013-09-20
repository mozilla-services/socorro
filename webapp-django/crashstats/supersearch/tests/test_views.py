import json
import mock
from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from waffle import Switch

from crashstats.crashstats.tests.test_views import BaseTestViews, Response


class TestViews(BaseTestViews):

    @staticmethod
    def setUpClass():
        TestViews.switch = Switch.objects.create(
            name='supersearch-all',
            active=True,
        )

    @staticmethod
    def tearDownClass():
        try:
            TestViews.switch.delete()
        except AssertionError:
            # test_search_waffle_switch removes that switch before, causing
            # this error
            pass

    def test_search_waffle_switch(self):
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

    @mock.patch('requests.get')
    def test_search(self, rget):
        self._login()
        url = reverse('supersearch.search')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Run a search to get some results' in response.content)

    @mock.patch('requests.get')
    def test_search_fields(self, rget):
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
            assert 'supersearch' in url
            if 'product/WaterWolf' in url:
                return Response("""{
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
                            "build_id": null
                        },
                        {
                            "signature": "EMPTY",
                            "date": "2017-01-31T23:12:57",
                            "uuid": "aaaaaaaaaaaaa4",
                            "product": "WaterWolf",
                            "version": "1.0",
                            "platform": "Linux",
                            "build_id": null
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
                } """)
            if 'product/SeaMonkey' in url:
                return Response("""{
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
                } """)
            elif 'nsASDOMWindowEnumerator' in url:
                return Response("""{
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
                }""")
            else:
                return Response('{"hits": [], "facets": [], "total": 0}')

            raise NotImplementedError(url)

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get

        url = reverse('supersearch.search_results')
        response = self.client.get(
            url,
            {'product': 'WaterWolf'}
        )
        eq_(response.status_code, 200)
        # Test results are present
        ok_('table id="reports-list"' in response.content)
        ok_('nsASDOMWindowEnumerator::GetNext()' in response.content)
        ok_('mySignatureIsCool' in response.content)
        ok_('mineIsCoolerThanYours' in response.content)
        ok_('EMPTY' in response.content)
        ok_('aaaaaaaaaaaaa1' in response.content)
        ok_('888981' in response.content)
        ok_('Linux' in response.content)
        ok_('2017-01-31 23:12:57' in response.content)
        # Test facets are present
        ok_('table id="facets-list"' in response.content)
        # Test bugs are present
        ok_('<th>Bugs</th>' in response.content)
        ok_('123456' in response.content)

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
            return Response("""
                {"hits": [], "total": 0}
            """)

        def mocked_get(url, **options):
            assert 'supersearch' in url
            if '_facets/url' in url:
                facets = """{
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
                }"""
            else:
                facets = """{
                    "platform": [
                        {
                            "term": "Linux",
                            "count": 3
                        }
                    ]
                }"""

            return Response("""{
                "hits": [
                    {
                        "signature": "nsASDOMWindowEnumerator::GetNext()",
                        "date": "2017-01-31T23:12:57",
                        "uuid": "aaaaaaaaaaaaa1",
                        "product": "WaterWolf",
                        "version": "1.0",
                        "platform": "Linux",
                        "build_id": 888981,
                        "email": "robert.robichet@inconnus.fr",
                        "url": "http://example.org"
                    },
                    {
                        "signature": "mySignatureIsCool",
                        "date": "2017-01-31T23:12:57",
                        "uuid": "aaaaaaaaaaaaa2",
                        "product": "WaterWolf",
                        "version": "1.0",
                        "platform": "Linux",
                        "build_id": 888981,
                        "email": "jean-pierre.avidol@inconnus.fr",
                        "url": "http://example.org"
                    },
                    {
                        "signature": "mineIsCoolerThanYours",
                        "date": "2017-01-31T23:12:57",
                        "uuid": "aaaaaaaaaaaaa3",
                        "product": "WaterWolf",
                        "version": "1.0",
                        "platform": "Linux",
                        "build_id": null,
                        "email": "marcel.patoulatchi@inconnus.fr",
                        "url": "http://example.org"
                    }
                ],
                "facets": %s,
                "total": 3
            } """ % facets)

        rpost.side_effect = mocked_post
        rget.side_effect = mocked_get

        url = reverse('supersearch.search_results')

        # Logged out user, cannot see the email field
        response = self.client.get(
            url,
            {
                '_columns': ['version', 'email'],
                '_facets': ['url', 'platform']
            }
        )

        eq_(response.status_code, 200)
        ok_('Email' not in response.content)
        ok_('marcel.patoulatchi@inconnus.fr' not in response.content)
        ok_('Url facet' not in response.content)
        ok_('http://example.org' not in response.content)
        ok_('Version' in response.content)
        ok_('1.0' in response.content)

        # Logged in user, can see the email field
        self._login()
        response = self.client.get(
            url,
            {
                '_columns': ['version', 'email'],
                '_facets': ['url', 'platform']
            }
        )

        eq_(response.status_code, 200)
        ok_('Email' in response.content)
        ok_('marcel.patoulatchi@inconnus.fr' in response.content)
        ok_('Url facet' in response.content)
        ok_('http://example.org' in response.content)
        ok_('Version' in response.content)
        ok_('1.0' in response.content)
