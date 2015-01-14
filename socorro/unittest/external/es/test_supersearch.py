# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from nose.plugins.attrib import attr
from nose.tools import assert_raises, eq_, ok_

from socorro.external import BadArgumentError
from socorro.external.es.supersearch import SuperSearch
from socorro.lib import datetimeutil, search_common
from socorro.unittest.external.es.base import (
    ElasticsearchTestCase,
    minimum_es_version,
)

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


@attr(integration='elasticsearch')  # for nosetests
class IntegrationTestSuperSearch(ElasticsearchTestCase):
    """Test SuperSearch with an elasticsearch database containing fake
    data. """

    def setUp(self):
        super(IntegrationTestSuperSearch, self).setUp()

        self.api = SuperSearch(config=self.config)
        self.now = datetimeutil.utc_now()

    def test_get_indices(self):
        now = datetime.datetime(2001, 1, 2, 0, 0)
        lastweek = now - datetime.timedelta(weeks=1)
        lastmonth = now - datetime.timedelta(weeks=4)

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastweek, '>'),
        ]

        res = self.api.get_indices(dates)
        eq_(res, ['socorro_integration_test_reports'])

        config = self.get_mware_config(es_index='socorro_%Y%W')
        api = SuperSearch(config=config)

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastweek, '>'),
        ]

        res = api.get_indices(dates)
        eq_(res, ['socorro_200052', 'socorro_200101'])

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastmonth, '>'),
        ]

        res = api.get_indices(dates)
        eq_(
            res,
            [
                'socorro_200049', 'socorro_200050', 'socorro_200051',
                'socorro_200052', 'socorro_200101'
            ]
        )

    @minimum_es_version('1.0')
    def test_get(self):
        """Run a very basic test, just to see if things work. """
        self.index_crash({
            'signature': 'js::break_your_browser',
            'date_processed': self.now,
            'build': 20000000,
            'os_name': 'Linux',
            'json_dump': {
                'write_combine_size': 9823012
            }
        })
        self.refresh_index()

        res = self.api.get()

        ok_('hits' in res)
        ok_('total' in res)
        ok_('facets' in res)

        eq_(res['total'], 1)
        eq_(len(res['hits']), 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')

        eq_(res['facets'].keys(), ['signature'])
        eq_(
            res['facets']['signature'][0],
            {'term': 'js::break_your_browser', 'count': 1}
        )

        # Test fields are being renamed.
        ok_('date' in res['hits'][0])  # date_processed -> date
        ok_('build_id' in res['hits'][0])  # build -> build_id
        ok_('platform' in res['hits'][0])  # os_name -> platform

        # Test namespaces are correctly removed.
        # processed_crash.json_dump.write_combine_size > write_combine_size
        ok_('write_combine_size' in res['hits'][0])

    @minimum_es_version('1.0')
    def test_get_with_enum_operators(self):
        self.index_crash({
            'product': 'WaterWolf',
            'app_notes': 'somebody that I used to know',
            'date_processed': self.now,
        })
        self.index_crash({
            'product': 'NightTrain',
            'app_notes': None,
            'date_processed': self.now,
        })
        self.index_crash({
            'product': 'NightTrain',
            'app_notes': 'processor that I used to run',
            'date_processed': self.now,
        })
        self.refresh_index()

        # A term that exists.
        res = self.api.get(
            product='WaterWolf'  # has terms
        )

        eq_(res['total'], 1)
        eq_(len(res['hits']), 1)
        eq_(res['hits'][0]['product'], 'WaterWolf')

        # Not a term that exists.
        res = self.api.get(
            product='!WaterWolf'  # does not have terms
        )

        eq_(res['total'], 2)
        eq_(len(res['hits']), 2)
        eq_(res['hits'][0]['product'], 'NightTrain')

        # A term that does not exist.
        res = self.api.get(
            product='EarthRacoon'  # has terms
        )

        eq_(res['total'], 0)

        # A phrase instead of a term.
        res = self.api.get(
            app_notes='that I used'  # has terms
        )

        eq_(res['total'], 2)
        eq_(len(res['hits']), 2)
        for hit in res['hits']:
            ok_('that I used' in hit['app_notes'])

    @minimum_es_version('1.0')
    def test_get_with_string_operators(self):
        self.index_crash({
            'signature': 'js::break_your_browser',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'mozilla::js::function',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'json_Is_Kewl',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'OhILoveMyBrowser',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'foo(bar)',
            'date_processed': self.now,
        })
        self.refresh_index()

        # Test the "contains" operator.
        res = self.api.get(
            signature='~js'  # contains
        )

        eq_(res['total'], 3)
        eq_(len(res['hits']), 3)
        for hit in res['hits']:
            ok_('js' in hit['signature'])

        ok_('signature' in res['facets'])
        eq_(len(res['facets']['signature']), 3)
        for facet in res['facets']['signature']:
            ok_('js' in facet['term'])
            eq_(facet['count'], 1)

        res = self.api.get(
            signature='!~js'  # does not contain
        )

        eq_(res['total'], 2)
        eq_(len(res['hits']), 2)
        for hit in res['hits']:
            ok_('js' not in hit['signature'])

        ok_('signature' in res['facets'])
        eq_(len(res['facets']['signature']), 2)
        for facet in res['facets']['signature']:
            ok_('js' not in facet['term'])
            eq_(facet['count'], 1)

        # Test the "starts with" operator.
        res = self.api.get(
            signature='$js'  # starts with
        )

        eq_(res['total'], 2)
        eq_(len(res['hits']), 2)
        for hit in res['hits']:
            ok_(hit['signature'].startswith('js'))

        ok_('signature' in res['facets'])
        eq_(len(res['facets']['signature']), 2)
        for facet in res['facets']['signature']:
            ok_(facet['term'].startswith('js'))
            eq_(facet['count'], 1)

        res = self.api.get(
            signature='!$js'  # does not start with
        )

        eq_(res['total'], 3)
        eq_(len(res['hits']), 3)
        for hit in res['hits']:
            ok_(not hit['signature'].startswith('js'))

        ok_('signature' in res['facets'])
        eq_(len(res['facets']['signature']), 3)
        for facet in res['facets']['signature']:
            ok_(not facet['term'].startswith('js'))
            eq_(facet['count'], 1)

        # Test the "ends with" operator.
        res = self.api.get(
            signature='^browser'  # ends with
        )

        # Those operators are case-sensitive, so here we expect only 1 result.
        eq_(res['total'], 1)
        eq_(len(res['hits']), 1)
        eq_(res['hits'][0]['signature'], 'js::break_your_browser')

        ok_('signature' in res['facets'])
        eq_(len(res['facets']['signature']), 1)
        eq_(
            res['facets']['signature'][0],
            {'term': 'js::break_your_browser', 'count': 1}
        )

        res = self.api.get(
            signature='^rowser'  # ends with
        )

        eq_(res['total'], 2)
        eq_(len(res['hits']), 2)
        for hit in res['hits']:
            ok_(hit['signature'].endswith('rowser'))

        ok_('signature' in res['facets'])
        eq_(len(res['facets']['signature']), 2)
        for facet in res['facets']['signature']:
            ok_(facet['term'].endswith('rowser'))
            eq_(facet['count'], 1)

        res = self.api.get(
            signature='!^rowser'  # does not end with
        )

        eq_(res['total'], 3)
        eq_(len(res['hits']), 3)
        for hit in res['hits']:
            ok_(not hit['signature'].endswith('rowser'))

        ok_('signature' in res['facets'])
        eq_(len(res['facets']['signature']), 3)
        for facet in res['facets']['signature']:
            ok_(not facet['term'].endswith('rowser'))
            eq_(facet['count'], 1)

    @minimum_es_version('1.0')
    def test_get_with_range_operators(self):
        self.index_crash({
            'build': 2000,
            'date_processed': self.now,
        })
        self.index_crash({
            'build': 2001,
            'date_processed': self.now,
        })
        self.index_crash({
            'build': 1999,
            'date_processed': self.now,
        })
        self.refresh_index()

        # Test the "has terms" operator.
        res = self.api.get(
            build_id='2000'  # has terms
        )

        eq_(res['total'], 1)
        eq_(len(res['hits']), 1)
        eq_(res['hits'][0]['build_id'], 2000)

        res = self.api.get(
            build_id='!2000'  # does not have terms
        )

        eq_(res['total'], 2)
        eq_(len(res['hits']), 2)
        for hit in res['hits']:
            ok_(hit['build_id'] != 2000)

        # Test the "greater than" operator.
        res = self.api.get(
            build_id='>2000'  # greater than
        )

        eq_(res['total'], 1)
        eq_(len(res['hits']), 1)
        eq_(res['hits'][0]['build_id'], 2001)

        # Test the "greater than or equal" operator.
        res = self.api.get(
            build_id='>=2000'  # greater than or equal
        )

        eq_(res['total'], 2)
        eq_(len(res['hits']), 2)
        for hit in res['hits']:
            ok_(hit['build_id'] >= 2000)

        # Test the "lower than" operator.
        res = self.api.get(
            build_id='<2000'  # lower than
        )

        eq_(res['total'], 1)
        eq_(len(res['hits']), 1)
        eq_(res['hits'][0]['build_id'], 1999)

        # Test the "lower than or equal" operator.
        res = self.api.get(
            build_id='<=2000'  # lower than or equal
        )

        eq_(res['total'], 2)
        eq_(len(res['hits']), 2)
        for hit in res['hits']:
            ok_(hit['build_id'] <= 2000)

    @minimum_es_version('1.0')
    def test_get_with_bool_operators(self):
        self.index_crash(
            processed_crash={
                'date_processed': self.now,
            },
            raw_crash={
                'Accessibility': True,
            },
        )
        self.index_crash(
            processed_crash={
                'date_processed': self.now,
            },
            raw_crash={
                'Accessibility': False,
            },
        )
        self.index_crash(
            processed_crash={
                'date_processed': self.now,
            },
            raw_crash={
                'Accessibility': True,
            },
        )
        self.refresh_index()

        # Test the "has terms" operator.
        res = self.api.get(
            accessibility='true'  # is true
        )

        eq_(res['total'], 2)
        eq_(len(res['hits']), 2)
        for hit in res['hits']:
            ok_(hit['accessibility'])

        res = self.api.get(
            accessibility='f'  # is false
        )

        eq_(res['total'], 1)
        eq_(len(res['hits']), 1)
        ok_(not res['hits'][0]['accessibility'])

    @minimum_es_version('1.0')
    def test_get_with_pagination(self):
        number_of_crashes = 21
        processed_crash = {
            'signature': 'something',
            'date_processed': self.now,
        }
        self.index_many_crashes(number_of_crashes, processed_crash)

        kwargs = {
            '_results_number': '10',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], number_of_crashes)
        eq_(len(res['hits']), 10)

        kwargs = {
            '_results_number': '10',
            '_results_offset': '10',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], number_of_crashes)
        eq_(len(res['hits']), 10)

        kwargs = {
            '_results_number': '10',
            '_results_offset': '15',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], number_of_crashes)
        eq_(len(res['hits']), 6)

        kwargs = {
            '_results_number': '10',
            '_results_offset': '30',
        }
        res = self.api.get(**kwargs)
        eq_(res['total'], number_of_crashes)
        eq_(len(res['hits']), 0)

    @minimum_es_version('1.0')
    def test_get_with_facets(self):
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'WaterWolf',
            'os_name': 'Windows NT',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'WaterWolf',
            'os_name': 'Linux',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'NightTrain',
            'os_name': 'Linux',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'foo(bar)',
            'product': 'EarthRacoon',
            'os_name': 'Linux',
            'date_processed': self.now,
        })

        # Index a lot of distinct values to test the results limit.
        number_of_crashes = 51
        processed_crash = {
            'version': '10.%s',
            'date_processed': self.now,
        }
        self.index_many_crashes(
            number_of_crashes,
            processed_crash,
            loop_field='version',
        )
        # Note: index_many_crashes does the index refreshing.

        # Test several facets
        kwargs = {
            '_facets': ['signature', 'platform']
        }
        res = self.api.get(**kwargs)

        ok_('facets' in res)
        ok_('signature' in res['facets'])

        expected_terms = [
            {'term': 'js::break_your_browser', 'count': 3},
            {'term': 'foo(bar)', 'count': 1},
        ]
        eq_(res['facets']['signature'], expected_terms)

        ok_('platform' in res['facets'])
        expected_terms = [
            {'term': 'Linux', 'count': 3},
            {'term': 'Windows NT', 'count': 1},
        ]
        eq_(res['facets']['platform'], expected_terms)

        # Test one facet with filters
        kwargs = {
            '_facets': ['product'],
            'product': 'WaterWolf',
        }
        res = self.api.get(**kwargs)

        ok_('product' in res['facets'])
        expected_terms = [
            {'term': 'WaterWolf', 'count': 2},
        ]
        eq_(res['facets']['product'], expected_terms)

        # Test one facet with a different filter
        kwargs = {
            '_facets': ['product'],
            'platform': 'linux',
        }
        res = self.api.get(**kwargs)

        ok_('product' in res['facets'])

        expected_terms = [
            {'term': 'EarthRacoon', 'count': 1},
            {'term': 'NightTrain', 'count': 1},
            {'term': 'WaterWolf', 'count': 1},
        ]
        eq_(res['facets']['product'], expected_terms)

        # Test the number of results.
        kwargs = {
            '_facets': ['version'],
        }
        res = self.api.get(**kwargs)

        ok_('version' in res['facets'])
        eq_(len(res['facets']['version']), self.api.config.facets_max_number)

        # Test errors
        assert_raises(
            BadArgumentError,
            self.api.get,
            _facets=['unkownfield']
        )

    def test_get_against_nonexistent_index(self):
        config = self.get_mware_config(es_index='socorro_test_reports_%W')
        api = SuperSearch(config=config)
        params = {
            'date': ['>2000-01-01T00:00:00', '<2000-01-10T00:00:00']
        }

        res = api.get(**params)
        eq_(res, {'total': 0, 'hits': [], 'facets': {}})

    def test_get_return_query_mode(self):
        res = self.api.get(
            signature='js',
            _return_query=True
        )
        ok_('query' in res)
        ok_('indices' in res)

        query = res['query']
        ok_('query' in query)
        ok_('aggs' in query)
        ok_('size' in query)
