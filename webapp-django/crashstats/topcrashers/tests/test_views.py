import datetime

import freezegun
import pyquery

from django.core.urlresolvers import reverse
from django.utils.timezone import utc

from crashstats.crashstats.models import Signature, BugAssociation
from crashstats.crashstats.tests.test_views import BaseTestViews
from crashstats.supersearch.models import SuperSearchUnredacted


class TestTopCrasherViews(BaseTestViews):
    base_url = reverse('topcrashers:topcrashers')

    def test_topcrashers(self):
        BugAssociation.objects.create(
            bug_id=123456789,
            signature='Something'
        )
        BugAssociation.objects.create(
            bug_id=22222,
            signature=u'FakeSignature1 \u7684 Japanese',
        )
        BugAssociation.objects.create(
            bug_id=33333,
            signature=u"FakeSignature1 \u7684 Japanese"
        )

        Signature.objects.create(
            signature=u'FakeSignature1 \u7684 Japanese',
            first_date=datetime.datetime(2000, 1, 1, 12, 23, 34, tzinfo=utc),
            first_build='20000101122334'
        )
        Signature.objects.create(
            signature='mozCool()',
            first_date=datetime.datetime(2016, 5, 2, 0, 0, 0, tzinfo=utc),
            first_build='20160502000000'
        )

        def mocked_supersearch_get(**params):
            if '_columns' not in params:
                params['_columns'] = []

            # By default we range by date, so there should be no filter on
            # the build id.
            assert 'build_id' not in params

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
                                'startup_crash': [{
                                    'term': 'T',
                                    'count': 100,
                                }],
                                'histogram_uptime': [{
                                    'term': 0,
                                    'count': 60,
                                }],
                                'cardinality_install_time': {
                                    'value': 13,
                                },
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
                                'startup_crash': [{
                                    'term': 'T',
                                    'count': 50,
                                }],
                                'histogram_uptime': [{
                                    'term': 0,
                                    'count': 40,
                                }],
                                'cardinality_install_time': {
                                    'value': 11,
                                },
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

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        url = self.base_url + '?product=WaterWolf&version=19.0'

        response = self.client.get(self.base_url, {'product': 'WaterWolf'})
        assert url in response['Location']

        # Test that several versions do not raise an error.
        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': ['19.0', '20.0'],
        })
        assert response.status_code, 200

        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '19.0',
        })
        assert response.status_code == 200
        doc = pyquery.PyQuery(response.content)
        selected_count = doc('.tc-result-count a[class="selected"]')
        assert selected_count.text() == '50'

        # there's actually only one such TD
        bug_ids = [x.text for x in doc('td.bug_ids_more > a')]
        # higher bug number first
        assert bug_ids == ['33333', '22222']

        # Check the first appearance date is there.
        assert '2000-01-01 12:23:34' in response.content

        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '19.0',
            '_facets_size': '100',
        })
        assert response.status_code == 200
        doc = pyquery.PyQuery(response.content)
        selected_count = doc('.tc-result-count a[class="selected"]')
        assert selected_count.text() == '100'

        # Check the startup crash icon is there.
        assert (
            'Potential Startup Crash, 50 out of 80 crashes happened during '
            'startup' in response.content
        )
        assert 'Startup Crash, all crashes happened during startup' in response.content

    def test_product_sans_featured_version(self):
        def mocked_supersearch_get(**params):
            if '_columns' not in params:
                params['_columns'] = []

            # By default we range by date, so there should be no filter on
            # the build id.
            assert 'build_id' not in params

            if 'hang_type' not in params['_aggs.signature']:
                # Return results for the previous week.
                results = {
                    'hits': [],
                    'facets': {
                        'signature': []
                    },
                    'total': 0
                }
            else:
                # Return results for the current week.
                results = {
                    'hits': [],
                    'facets': {
                        'signature': []
                    },
                    'total': 0
                }

            results['hits'] = self.only_certain_columns(
                results['hits'],
                params['_columns']
            )
            return results

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        response = self.client.get(self.base_url, {'product': 'SeaMonkey'})
        assert response.status_code == 302
        actual_url = self.base_url + '?product=SeaMonkey&version=9.5'
        assert actual_url in response['Location']

        response = self.client.get(self.base_url, {
            'product': 'SeaMonkey',
            'version': '9.5',
        })
        assert response.status_code == 200
        # Not testing the response content.
        # See test_topcrashers() above instead. Here we just want to make
        # sure it renders at all when the product has no featured versions.

    def test_400_by_bad_days(self):
        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '0.1',
            'days': 'xxxxxx',
        })
        assert response.status_code == 400
        assert 'not a number' in response.content
        assert response['Content-Type'] == 'text/html; charset=utf-8'

    def test_400_by_bad_facets_size(self):
        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            '_facets_size': 'notanumber',
        })
        assert response.status_code == 400
        assert 'Enter a whole number' in response.content
        assert response['Content-Type'] == 'text/html; charset=utf-8'

    def test_with_unsupported_product(self):
        # SnowLion is not in the mocked Products list
        response = self.client.get(self.base_url, {
            'product': 'SnowLion',
            'version': '0.1',
        })
        assert response.status_code == 404

    def test_without_any_signatures(self):
        url = self.base_url + '?product=WaterWolf&version=19.0'
        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
        })
        assert url in response['Location']

        def mocked_supersearch_get(**params):
            return {
                'hits': [],
                'facets': {
                    'signature': []
                },
                'total': 0
            }

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '19.0',
        })
        assert response.status_code == 200

    def test_modes(self):
        def mocked_supersearch_get(**params):
            return {
                'hits': [],
                'facets': {
                    'signature': []
                },
                'total': 0
            }

        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

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
            assert response.status_code == 200
            assert now in response.content
            assert today not in response.content

            # Now test the "day time" data.
            response = self.client.get(self.base_url, {
                'product': 'WaterWolf',
                'version': '19.0',
                '_tcbs_mode': 'byday',
            })
            assert response.status_code == 200
            assert today in response.content
            assert now not in response.content

    def test_by_build(self):
        def mocked_supersearch_get(**params):
            assert 'build_id' in params
            return {
                'hits': [],
                'facets': {
                    'signature': []
                },
                'total': 0
            }
        SuperSearchUnredacted.implementation().get.side_effect = mocked_supersearch_get

        response = self.client.get(self.base_url, {
            'product': 'WaterWolf',
            'version': '19.0',
            '_range_type': 'build',
        })
        assert response.status_code == 200
