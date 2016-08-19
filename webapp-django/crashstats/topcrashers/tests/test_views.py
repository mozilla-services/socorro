import datetime

import freezegun
import mock
import pyquery
from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse
from django.utils.timezone import utc

from crashstats.crashstats.models import SignatureFirstDate
from crashstats.crashstats.tests.test_views import (
    BaseTestViews, mocked_post_123
)
from crashstats.supersearch.models import SuperSearchUnredacted


class TestViews(BaseTestViews):
    base_url = reverse('topcrashers:topcrashers')

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    @mock.patch('requests.post')
    def test_topcrashers(self, rpost, bugs_get):

        def mocked_bugs(**options):
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
        bugs_get.side_effect = mocked_bugs

        def mocked_signature_first_date_get(**options):
            return {
                "hits": [
                    {
                        "signature": u"FakeSignature1 \u7684 Japanese",
                        "first_date": datetime.datetime(
                            2000, 1, 1, 12, 23, 34,
                            tzinfo=utc,
                        ),
                        "first_build": "20000101122334",
                    },
                    {
                        "signature": u"mozCool()",
                        "first_date": datetime.datetime(
                            2016, 5, 2, 0, 0, 0,
                            tzinfo=utc,
                        ),
                        "first_build": "20160502000000",
                    },
                ],
                "total": 2
            }

        SignatureFirstDate.implementation().get.side_effect = (
            mocked_signature_first_date_get
        )

        def mocked_supersearch_get(**params):
            if '_columns' not in params:
                params['_columns'] = []

            # By default we range by date, so there should be no filter on
            # the build id.
            ok_('build_id' not in params)

            if 'hang_type' not in params['_aggs.signature']:
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
                                'histogram_uptime': [{
                                    'term': 0,
                                    'count': 40,
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
                                'histogram_uptime': [{
                                    'term': 0,
                                    'count': 60,
                                }],
                            }
                        }, {
                            'term': u'mozCool()',
                            'count': 80,
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
                                    'term': 'browser',
                                    'count': 50,
                                }],
                                'histogram_uptime': [{
                                    'term': 0,
                                    'count': 40,
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
        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        url = self.base_url + '?product=WaterWolf&version=19.0'

        response = self.client.get(self.base_url, {'product': 'WaterWolf'})
        ok_(url in response['Location'])

        # Test that several versions do not raise an error.
        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': ['19.0', '20.0'],
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

        # Check the first appearance date is there.
        ok_('2000-01-01 12:23:34' in response.content)

        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '19.0',
            '_facets_size': '100',
        })
        eq_(response.status_code, 200)
        doc = pyquery.PyQuery(response.content)
        selected_count = doc('.tc-result-count a[class="selected"]')
        eq_(selected_count.text(), '100')

        # Check the startup crash icon is there.
        ok_('Startup Crash' in response.content)

    def test_topcrashers_400_by_bad_days(self):
        response = self.client.get(self.base_url, {
            'product': 'SnowLion',
            'version': '0.1',
            'days': 'xxxxxx',
        })
        eq_(response.status_code, 400)
        ok_('not a number' in response.content)
        eq_(response['Content-Type'], 'text/html; charset=utf-8')

    def test_topcrasher_with_product_sans_release(self):
        # SnowLion is not a product at all
        response = self.client.get(self.base_url, {
            'product': 'SnowLion',
            'version': '0.1',
        })
        eq_(response.status_code, 404)

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    def test_topcrasher_without_any_signatures(self, rpost):
        url = self.base_url + '?product=WaterWolf&version=19.0'
        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
        })
        ok_(url in response['Location'])

        rpost.side_effect = mocked_post_123

        def mocked_supersearch_get(**params):
            return {
                'hits': [],
                'facets': {
                    'signature': []
                },
                'total': 0
            }
        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

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
        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        now = datetime.datetime.utcnow().replace(microsecond=0)
        today = now.replace(hour=0, minute=0, second=0)

        with freezegun.freeze_time(now, tz_offset=0):
            now = now.isoformat()
            today = today.isoformat()

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

    @mock.patch('crashstats.crashstats.models.Bugs.get')
    def test_topcrasher_by_build(self, rpost):
        rpost.side_effect = mocked_post_123

        def mocked_supersearch_get(**params):
            ok_('build_id' in params)
            return {
                'hits': [],
                'facets': {
                    'signature': []
                },
                'total': 0
            }
        SuperSearchUnredacted.implementation().get.side_effect = (
            mocked_supersearch_get
        )

        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '19.0',
            '_range_type': 'build',
        })
        eq_(response.status_code, 200)

        # Test with a version that does not support builds.
        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '18.0',
            '_range_type': 'build',
        })
        eq_(response.status_code, 200)
        ok_('versions do not support the by build date' in response.content)
        ok_('Range Type:' not in response.content)
