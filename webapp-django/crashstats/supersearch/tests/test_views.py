import json
import mock
from nose.tools import eq_, ok_

from django.contrib.auth.models import User
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

    def _login(self):
        User.objects.create_user('kairo', 'kai@ro.com', 'secret')
        assert self.client.login(username='kairo', password='secret')

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

    def test_search_need_admin(self):
        url = reverse('supersearch.search')
        response = self.client.get(url)
        eq_(response.status_code, 302)

        url = reverse('supersearch.search_results')
        response = self.client.get(url)
        eq_(response.status_code, 302)

        url = reverse('supersearch.search_fields')
        response = self.client.get(url)
        eq_(response.status_code, 302)

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
        self._login()

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
            if 'products/WaterWolf' in url:
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
            elif 'products/NightTrain' in url:
                return Response('{"hits": [], "total": 0}')
            elif 'products/SeaMonkey' in url:
                self.assertTrue('plugin_search_mode/is_exactly' in url)
                return Response("""
                {"hits": [
                      {
                      "count": 586,
                      "signature": "nsASDOMWindowEnumerator::GetNext()",
                      "numcontent": 0,
                      "is_windows": 586,
                      "is_linux": 0,
                      "numplugin": 533,
                      "is_mac": 0,
                      "numhang": 0,
                      "pluginname": "superAddOn",
                      "pluginfilename": "addon.dll",
                      "pluginversion": "1.2.3"
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

        url = reverse('supersearch.search_results')
        response = self.client.get(
            url,
            {'product': 'WaterWolf'}
        )
        eq_(response.status_code, 200)
        ok_('table id="signatureList"' in response.content)
        ok_('nsASDOMWindowEnumerator::GetNext()' in response.content)
        ok_('mySignatureIsCool' in response.content)
        ok_('mineIsCoolerThanYours' in response.content)
        ok_('(null signature)' in response.content)

        # Test with empty results
        response = self.client.get(url, {
            'product': 'NightTrain',
            'date': '2012-01-01'
        })
        eq_(response.status_code, 200)
        ok_('table id="signatureList"' not in response.content)
        ok_('No results were found' in response.content)

        response = self.client.get(
            url,
            {'signature': '~nsASDOMWindowEnumerator'}
        )
        eq_(response.status_code, 200)
        ok_('table id="signatureList"' in response.content)
        ok_('nsASDOMWindowEnumerator::GetNext()' in response.content)
        # No bug numbers in results yet, but there should be at some point
        # ok_('123456' in response.content)
