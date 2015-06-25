import datetime
import freezegun
import mock
import pyquery
from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from crashstats.supersearch.models import SuperSearch
from crashstats.crashstats.tests.test_views import (
    BaseTestViews, Response, mocked_post_123
)


class TestViews(BaseTestViews):
    base_url = reverse('topcrashers:topcrashers')

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    def test_topcrashers(self, rpost):

        def mocked_post(**options):
            return {
                "hits": [
                    {"id": 123456789,
                     "signature": "Something"},
                    {"id": 22222,
                     "signature": u"FakeSignature1 \u7684 Japanese"},
                    {"id": 33333,
                     "signature": u"FakeSignature1 \u7684 Japanese"}
                ]
            }
        rpost.side_effect = mocked_post

        def mocked_supersearch_get(**params):
            if '_columns' not in params:
                params['_columns'] = []

            if 'date' in params:
                # Return results for the previous week.
                results = {
                    'hits': [],
                    'facets': {
                        'signature': [{
                            'term': u'FakeSignature1 \u7684 Japanese',
                            'count': 100,
                            'facets': {
                                'platform': [{
                                    'term': 'WaterWolf',
                                    'count': 50,
                                }],
                                'is_garbage_collecting': [{
                                    'term': 't',
                                    'count': 50,
                                }],
                                'hang_type': [{
                                    'term': 1,
                                    'count': 50,
                                }],
                                'process_type': [{
                                    'term': 'plugin',
                                    'count': 50,
                                }],
                            }
                        }]
                    },
                    'total': 250
                }
            else:
                # Return results for the current week.
                results = {
                    'hits': [],
                    'facets': {
                        'signature': [{
                            'term': u'FakeSignature1 \u7684 Japanese',
                            'count': 100,
                            'facets': {
                                'platform': [{
                                    'term': 'WaterWolf',
                                    'count': 50,
                                }],
                                'is_garbage_collecting': [{
                                    'term': 't',
                                    'count': 50,
                                }],
                                'hang_type': [{
                                    'term': 1,
                                    'count': 50,
                                }],
                                'process_type': [{
                                    'term': 'plugin',
                                    'count': 50,
                                }],
                            }
                        }]
                    },
                    'total': 250
                }

            results['hits'] = self.only_certain_columns(
                results['hits'],
                params['_columns']
            )
            return results
        SuperSearch.implementation().get.side_effect = mocked_supersearch_get

        url = self.base_url + '?product=WaterWolf&version=19.0'

        response = self.client.get(self.base_url, {'product': 'WaterWolf'})
        ok_(url in response['Location'])

        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '19.0',
        })
        eq_(response.status_code, 200)

        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '19.0',
        })
        eq_(response.status_code, 200)
        doc = pyquery.PyQuery(response.content)
        selected_count = doc('.tc-result-count a[class="selected"]')
        eq_(selected_count.text(), '50')

        # there's actually only one such TD
        bug_ids = [x.text for x in doc('td.bug_ids_more > a')]
        # higher bug number first
        eq_(bug_ids, ['33333', '22222'])

        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '19.0',
            '_facets_size': '100',
        })
        eq_(response.status_code, 200)
        doc = pyquery.PyQuery(response.content)
        selected_count = doc('.tc-result-count a[class="selected"]')
        eq_(selected_count.text(), '100')

    def test_topcrasher_with_invalid_version(self):
        # 0.1 is not a valid release version
        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '0.1',
        })
        eq_(response.status_code, 404)

    def test_topcrasher_with_product_sans_release(self):
        # SnowLion is not a product at all
        response = self.client.get(self.base_url, {
            'product': 'SnowLion',
            'version': '0.1',
        })
        eq_(response.status_code, 404)

        # SeaMonkey is a product but has no active releases
        response = self.client.get(self.base_url, {
            'product': 'SeaMonkey',
            'version': '9.5',
        })
        eq_(response.status_code, 404)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.get')
    def test_topcrasher_without_any_signatures(self, rget, rpost):
        url = self.base_url + '?product=WaterWolf&version=19.0'
        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
        })
        ok_(url in response['Location'])

        rpost.side_effect = mocked_post_123

        def mocked_get(url, params, **options):
            if '/products' in url:
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
                        "version": "19.0",
                        "has_builds": true
                    }],
                    "total": "1"
                }
                """)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        def mocked_supersearch_get(**params):
            return {
                'hits': [],
                'facets': {
                    'signature': []
                },
                'total': 0
            }
        SuperSearch.implementation().get.side_effect = mocked_supersearch_get

        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '19.0',
        })
        eq_(response.status_code, 200)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    def test_topcrasher_modes(self, rpost):
        rpost.side_effect = mocked_post_123

        def mocked_supersearch_get(**params):
            return {
                'hits': [],
                'facets': {
                    'signature': []
                },
                'total': 0
            }
        SuperSearch.implementation().get.side_effect = mocked_supersearch_get

        now = datetime.datetime.utcnow()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        timestr = '%Y-%m-%d %H:%M:%S'
        now = now.strftime(timestr)
        today = today.strftime(timestr)

        with freezegun.freeze_time(now, tz_offset=0):
            # By default, it returns "real-time" data.
            response = self.client.get(self.base_url, {
                'product': 'WaterWolf',
                'version': '19.0',
            })
            eq_(response.status_code, 200)
            ok_(now in response.content, now)
            ok_(today not in response.content)

            # Now test the "day time" data.
            response = self.client.get(self.base_url, {
                'product': 'WaterWolf',
                'version': '19.0',
                '_tcbs_mode': 'byday',
            })
            eq_(response.status_code, 200)
            ok_(today in response.content)
            ok_(now not in response.content)
