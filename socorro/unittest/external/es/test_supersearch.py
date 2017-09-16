# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json

import requests_mock
import pytest

from socorro.lib import BadArgumentError, datetimeutil, search_common
from socorro.unittest.external.es.base import (
    ElasticsearchTestCase,
    SuperSearchWithFields,
    minimum_es_version,
)

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


class IntegrationTestSuperSearch(ElasticsearchTestCase):
    """Test SuperSearch with an elasticsearch database containing fake
    data. """

    def setUp(self):
        super(IntegrationTestSuperSearch, self).setUp()

        self.api = SuperSearchWithFields(config=self.config)
        self.now = datetimeutil.utc_now()

        # Wait until the cluster is yellow before proceeding.
        self.health_check()

    def test_get_indices(self):
        now = datetime.datetime(2001, 1, 2, 0, 0)
        lastweek = now - datetime.timedelta(weeks=1)
        lastmonth = now - datetime.timedelta(weeks=4)

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastweek, '>'),
        ]

        res = self.api.get_indices(dates)
        assert res == ['socorro_integration_test_reports']

        config = self.get_base_config(es_index='socorro_%Y%W')
        api = SuperSearchWithFields(config=config)

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastweek, '>'),
        ]

        res = api.get_indices(dates)
        assert res == ['socorro_200052', 'socorro_200101']

        dates = [
            search_common.SearchParam('date', now, '<'),
            search_common.SearchParam('date', lastmonth, '>'),
        ]

        res = api.get_indices(dates)
        expected = [
            'socorro_200049', 'socorro_200050', 'socorro_200051', 'socorro_200052',
            'socorro_200101'
        ]
        assert res == expected

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

        res = self.api.get(_columns=[
            'date', 'build_id', 'platform', 'signature', 'write_combine_size'
        ])

        assert 'hits' in res
        assert 'total' in res
        assert 'facets' in res

        assert res['total'] == 1
        assert len(res['hits']) == 1
        assert res['hits'][0]['signature'] == 'js::break_your_browser'

        assert res['facets'].keys() == ['signature']
        assert res['facets']['signature'][0] == {'term': 'js::break_your_browser', 'count': 1}

        # Test fields are being renamed.
        assert 'date' in res['hits'][0]  # date_processed -> date
        assert 'build_id' in res['hits'][0]  # build -> build_id
        assert 'platform' in res['hits'][0]  # os_name -> platform

        # Test namespaces are correctly removed.
        # processed_crash.json_dump.write_combine_size > write_combine_size
        assert 'write_combine_size' in res['hits'][0]

    @minimum_es_version('1.0')
    def test_get_with_root_field(self):
        """Verify that querying fields at the root of the crash document works.
        """
        self.index_crash({
            'signature': 'js::break_your_browser',
            'date_processed': self.now,
        }, root_doc={
            'removed_fields': 'foo bar',
        })
        self.refresh_index()

        res = self.api.get(_columns=[
            'date', 'signature', 'removed_fields'
        ], _facets=['removed_fields'])

        assert 'removed_fields' in res['hits'][0]
        assert res['hits'][0]['removed_fields'] == 'foo bar'

        assert 'removed_fields' in res['facets']
        assert len(res['facets']['removed_fields']) == 2

    @minimum_es_version('1.0')
    def test_get_with_bad_results_number(self):
        """Run a very basic test, just to see if things work. """
        with pytest.raises(BadArgumentError):
            self.api.get(_columns=['date'], _results_number=-1)

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

        assert res['total'] == 1
        assert len(res['hits']) == 1
        assert res['hits'][0]['product'] == 'WaterWolf'

        # Not a term that exists.
        res = self.api.get(
            product='!WaterWolf'  # does not have terms
        )

        assert res['total'] == 2
        assert len(res['hits']) == 2
        assert res['hits'][0]['product'] == 'NightTrain'

        # A term that does not exist.
        res = self.api.get(
            product='EarthRacoon'  # has terms
        )

        assert res['total'] == 0

        # A phrase instead of a term.
        res = self.api.get(
            app_notes='that I used',  # has terms
            _columns=['app_notes'],
        )

        assert res['total'] == 2
        assert len(res['hits']) == 2
        for hit in res['hits']:
            assert 'that I used' in hit['app_notes']

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

        assert res['total'] == 3
        assert len(res['hits']) == 3
        for hit in res['hits']:
            assert 'js' in hit['signature']

        assert 'signature' in res['facets']
        assert len(res['facets']['signature']) == 3
        for facet in res['facets']['signature']:
            assert 'js' in facet['term']
            assert facet['count'] == 1

        res = self.api.get(
            signature='!~js'  # does not contain
        )

        assert res['total'] == 2
        assert len(res['hits']) == 2
        for hit in res['hits']:
            assert 'js' not in hit['signature']

        assert 'signature' in res['facets']
        assert len(res['facets']['signature']) == 2
        for facet in res['facets']['signature']:
            assert 'js' not in facet['term']
            assert facet['count'] == 1

        # Test the "starts with" operator.
        res = self.api.get(
            signature='^js'  # starts with
        )

        assert res['total'] == 2
        assert len(res['hits']) == 2
        for hit in res['hits']:
            assert hit['signature'].startswith('js')

        assert 'signature' in res['facets']
        assert len(res['facets']['signature']) == 2
        for facet in res['facets']['signature']:
            assert facet['term'].startswith('js')
            assert facet['count'] == 1

        res = self.api.get(
            signature='!^js'  # does not start with
        )

        assert res['total'] == 3
        assert len(res['hits']) == 3
        for hit in res['hits']:
            assert not hit['signature'].startswith('js')

        assert 'signature' in res['facets']
        assert len(res['facets']['signature']) == 3
        for facet in res['facets']['signature']:
            assert not facet['term'].startswith('js')
            assert facet['count'] == 1

        # Test the "ends with" operator.
        res = self.api.get(
            signature='$browser'  # ends with
        )

        # Those operators are case-sensitive, so here we expect only 1 result.
        assert res['total'] == 1
        assert len(res['hits']) == 1
        assert res['hits'][0]['signature'] == 'js::break_your_browser'

        assert 'signature' in res['facets']
        assert len(res['facets']['signature']) == 1
        assert res['facets']['signature'][0] == {'term': 'js::break_your_browser', 'count': 1}

        res = self.api.get(
            signature='$rowser'  # ends with
        )

        assert res['total'] == 2
        assert len(res['hits']) == 2
        for hit in res['hits']:
            assert hit['signature'].endswith('rowser')

        assert 'signature' in res['facets']
        assert len(res['facets']['signature']) == 2
        for facet in res['facets']['signature']:
            assert facet['term'].endswith('rowser')
            assert facet['count'] == 1

        res = self.api.get(
            signature='!$rowser'  # does not end with
        )

        assert res['total'] == 3
        assert len(res['hits']) == 3
        for hit in res['hits']:
            assert not hit['signature'].endswith('rowser')

        assert 'signature' in res['facets']
        assert len(res['facets']['signature']) == 3
        for facet in res['facets']['signature']:
            assert not facet['term'].endswith('rowser')
            assert facet['count'] == 1

        # Test the "regex" operator.
        res = self.api.get(
            signature='@mozilla::.*::function'  # regex
        )
        assert res['total'] == 1
        assert len(res['hits']) == 1
        assert res['hits'][0]['signature'] == 'mozilla::js::function'

        res = self.api.get(
            signature='@f.."(bar)"'  # regex
        )
        assert res['total'] == 1
        assert len(res['hits']) == 1
        assert res['hits'][0]['signature'] == 'foo(bar)'

        res = self.api.get(
            signature='!@mozilla::.*::function'  # regex
        )
        assert res['total'] == 4
        assert len(res['hits']) == 4
        for hit in res['hits']:
            assert hit['signature'] != 'mozilla::js::function'

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
            build_id='2000',  # has terms
            _columns=['build_id'],
        )

        assert res['total'] == 1
        assert len(res['hits']) == 1
        assert res['hits'][0]['build_id'] == 2000

        res = self.api.get(
            build_id='!2000',  # does not have terms
            _columns=['build_id'],
        )

        assert res['total'] == 2
        assert len(res['hits']) == 2
        for hit in res['hits']:
            assert hit['build_id'] != 2000

        # Test the "greater than" operator.
        res = self.api.get(
            build_id='>2000',  # greater than
            _columns=['build_id'],
        )

        assert res['total'] == 1
        assert len(res['hits']) == 1
        assert res['hits'][0]['build_id'] == 2001

        # Test the "greater than or equal" operator.
        res = self.api.get(
            build_id='>=2000',  # greater than or equal
            _columns=['build_id'],
        )

        assert res['total'] == 2
        assert len(res['hits']) == 2
        for hit in res['hits']:
            assert hit['build_id'] >= 2000

        # Test the "lower than" operator.
        res = self.api.get(
            build_id='<2000',  # lower than
            _columns=['build_id'],
        )

        assert res['total'] == 1
        assert len(res['hits']) == 1
        assert res['hits'][0]['build_id'] == 1999

        # Test the "lower than or equal" operator.
        res = self.api.get(
            build_id='<=2000',  # lower than or equal
            _columns=['build_id'],
        )

        assert res['total'] == 2
        assert len(res['hits']) == 2
        for hit in res['hits']:
            assert hit['build_id'] <= 2000

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
        self.index_crash(
            processed_crash={
                'date_processed': self.now,
            },
            raw_crash={
                # Missing value should also be considered as "false".
            },
        )
        self.refresh_index()

        # Test the "has terms" operator.
        res = self.api.get(
            accessibility='__true__',  # is true
            _columns=['accessibility'],
        )

        assert res['total'] == 2
        assert len(res['hits']) == 2
        for hit in res['hits']:
            assert hit['accessibility']

        res = self.api.get(
            accessibility='!__true__',  # is false
            _columns=['accessibility'],
        )

        assert res['total'] == 2
        assert len(res['hits']) == 2
        assert not res['hits'][0]['accessibility']

    @minimum_es_version('1.0')
    def test_get_with_combined_operators(self):
        sigs = (
            'js::break_your_browser',
            'mozilla::js::function',
            'js<isKewl>',
            'foo(bar)',
        )

        self.index_crash({
            'signature': sigs[0],
            'app_notes': 'foo bar mozilla',
            'product': 'WaterWolf',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': sigs[1],
            'app_notes': 'foo bar',
            'product': 'WaterWolf',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': sigs[2],
            'app_notes': 'foo mozilla',
            'product': 'EarthRacoon',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': sigs[3],
            'app_notes': 'mozilla bar',
            'product': 'EarthRacoon',
            'date_processed': self.now,
        })
        self.refresh_index()

        res = self.api.get(
            signature=['js', '~::'],
        )
        assert res['total'] == 3
        assert sorted([x['signature'] for x in res['hits']]), sorted([sigs[0], sigs[1], sigs[2]])

        res = self.api.get(
            signature=['js', '~::'],
            product=['Unknown'],
        )
        assert res['total'] == 0
        assert len(res['hits']) == 0

        res = self.api.get(
            signature=['js', '~::'],
            product=['WaterWolf', 'EarthRacoon'],
        )
        assert res['total'] == 3
        assert sorted([x['signature'] for x in res['hits']]) == sorted([sigs[0], sigs[1], sigs[2]])

        res = self.api.get(
            signature=['js', '~::'],
            app_notes=['foo bar'],
        )
        assert res['total'] == 2
        assert sorted([x['signature'] for x in res['hits']]) == sorted([sigs[0], sigs[1]])

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
        assert res['total'] == number_of_crashes
        assert len(res['hits']) == 10

        kwargs = {
            '_results_number': '10',
            '_results_offset': '10',
        }
        res = self.api.get(**kwargs)
        assert res['total'] == number_of_crashes
        assert len(res['hits']) == 10

        kwargs = {
            '_results_number': '10',
            '_results_offset': '15',
        }
        res = self.api.get(**kwargs)
        assert res['total'] == number_of_crashes
        assert len(res['hits']) == 6

        kwargs = {
            '_results_number': '10',
            '_results_offset': '30',
        }
        res = self.api.get(**kwargs)
        assert res['total'] == number_of_crashes
        assert len(res['hits']) == 0

    @minimum_es_version('1.0')
    def test_get_with_sorting(self):
        """Test a search with sort returns expected results. """
        self.index_crash({
            'product': 'WaterWolf',
            'os_name': 'Windows NT',
            'date_processed': self.now,
        })
        self.index_crash({
            'product': 'WaterWolf',
            'os_name': 'Linux',
            'date_processed': self.now,
        })
        self.index_crash({
            'product': 'NightTrain',
            'os_name': 'Linux',
            'date_processed': self.now,
        })
        self.refresh_index()

        res = self.api.get(_sort='product')
        assert res['total'] > 0

        last_item = ''
        for hit in res['hits']:
            assert last_item <= hit['product']
            last_item = hit['product']

        # Descending order.
        res = self.api.get(_sort='-product')
        assert res['total'] > 0

        last_item = 'zzzzz'
        for hit in res['hits']:
            assert last_item >= hit['product']
            last_item = hit['product']

        # Several fields.
        res = self.api.get(
            _sort=['product', 'platform'],
            _columns=['product', 'platform'],
        )
        assert res['total'] > 0

        last_product = ''
        last_platform = ''
        for hit in res['hits']:
            if hit['product'] != last_product:
                last_platform = ''

            assert last_product <= hit['product']
            last_product = hit['product']

            assert last_platform <= hit['platform']
            last_platform = hit['platform']

        # Invalid field--"something" is invalid
        with pytest.raises(BadArgumentError):
            self.api.get(_sort='something')

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

        assert 'facets' in res
        assert 'signature' in res['facets']

        expected_terms = [
            {'term': 'js::break_your_browser', 'count': 3},
            {'term': 'foo(bar)', 'count': 1},
        ]
        assert res['facets']['signature'] == expected_terms

        assert 'platform' in res['facets']
        expected_terms = [
            {'term': 'Linux', 'count': 3},
            {'term': 'Windows NT', 'count': 1},
        ]
        assert res['facets']['platform'] == expected_terms

        # Test one facet with filters
        kwargs = {
            '_facets': ['product'],
            'product': 'WaterWolf',
        }
        res = self.api.get(**kwargs)

        assert 'product' in res['facets']
        expected_terms = [
            {'term': 'WaterWolf', 'count': 2},
        ]
        assert res['facets']['product'] == expected_terms

        # Test one facet with a different filter
        kwargs = {
            '_facets': ['product'],
            'platform': 'linux',
        }
        res = self.api.get(**kwargs)

        assert 'product' in res['facets']

        expected_terms = [
            {'term': 'EarthRacoon', 'count': 1},
            {'term': 'NightTrain', 'count': 1},
            {'term': 'WaterWolf', 'count': 1},
        ]
        assert res['facets']['product'] == expected_terms

        # Test the number of results.
        kwargs = {
            '_facets': ['version'],
        }
        res = self.api.get(**kwargs)

        assert 'version' in res['facets']
        assert len(res['facets']['version']) == 50  # 50 is the default value

        # Test with a different number of facets results.
        kwargs = {
            '_facets': ['version'],
            '_facets_size': 20
        }
        res = self.api.get(**kwargs)

        assert 'version' in res['facets']
        assert len(res['facets']['version']) == 20

        kwargs = {
            '_facets': ['version'],
            '_facets_size': 100
        }
        res = self.api.get(**kwargs)

        assert 'version' in res['facets']
        assert len(res['facets']['version']) == number_of_crashes

        # Test errors
        with pytest.raises(BadArgumentError):
            self.api.get(_facets=['unknownfield'])

    @minimum_es_version('1.0')
    def test_get_with_too_many_facets(self):
        # Some crazy big number
        with pytest.raises(BadArgumentError):
            self.api.get(_facets=['signature'], _facets_size=999999)

        # 10,000 is the max,
        # should not raise an error
        self.api.get(
            _facets=['signature'],
            _facets_size=10000,
        )

    @minimum_es_version('1.0')
    def test_get_with_no_facets(self):
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
        number_of_crashes = 5
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

        # Test 0 facets
        kwargs = {
            '_facets': ['signature'],
            '_aggs.product': ['version'],
            '_aggs.platform': ['_histogram.date'],
            '_facets_size': 0
        }
        res = self.api.get(**kwargs)
        assert res['facets'] == {}
        # hits should still work as normal
        assert res['hits']
        assert len(res['hits']) == res['total']

    @minimum_es_version('1.0')
    def test_get_with_cardinality(self):
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

        # Index a lot of distinct values.
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

        # Test a simple cardinality.
        kwargs = {
            '_facets': ['_cardinality.platform']
        }
        res = self.api.get(**kwargs)

        assert 'facets' in res
        assert 'cardinality_platform' in res['facets']
        assert res['facets']['cardinality_platform'] == {'value': 2}

        # Test more distinct values.
        kwargs = {
            '_facets': ['_cardinality.version']
        }
        res = self.api.get(**kwargs)

        assert 'facets' in res
        assert 'cardinality_version' in res['facets']
        assert res['facets']['cardinality_version'] == {'value': 51}

        # Test as a level 2 aggregation.
        kwargs = {
            '_aggs.signature': ['_cardinality.platform']
        }
        res = self.api.get(**kwargs)

        assert 'facets' in res
        assert 'signature' in res['facets']
        for facet in res['facets']['signature']:
            assert 'cardinality_platform' in facet['facets']

        # Test errors
        with pytest.raises(BadArgumentError):
            self.api.get(_facets=['_cardinality.unknownfield'])

    @minimum_es_version('1.0')
    def test_get_with_sub_aggregations(self):
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'WaterWolf',
            'version': '2.1',
            'os_name': 'Windows NT',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'WaterWolf',
            'version': '2.1',
            'os_name': 'Linux',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'NightTrain',
            'version': '2.1',
            'os_name': 'Linux',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'foo(bar)',
            'product': 'EarthRacoon',
            'version': '2.1',
            'os_name': 'Linux',
            'date_processed': self.now,
        })

        # Index a lot of distinct values to test the results limit.
        number_of_crashes = 51
        processed_crash = {
            'version': '10.%s',
            'signature': 'crash_me_I_m_famous',
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
            '_aggs.signature': ['product', 'platform'],
            'signature': '!=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        assert 'facets' in res
        assert 'signature' in res['facets']

        expected_terms = [
            {
                'term': 'js::break_your_browser',
                'count': 3,
                'facets': {
                    'product': [
                        {
                            'term': 'WaterWolf',
                            'count': 2
                        },
                        {
                            'term': 'NightTrain',
                            'count': 1
                        },
                    ],
                    'platform': [
                        {
                            'term': 'Linux',
                            'count': 2
                        },
                        {
                            'term': 'Windows NT',
                            'count': 1
                        },
                    ]
                }
            },
            {
                'term': 'foo(bar)',
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'EarthRacoon',
                            'count': 1
                        }
                    ],
                    'platform': [
                        {
                            'term': 'Linux',
                            'count': 1
                        }
                    ],
                }
            },
        ]
        assert res['facets']['signature'] == expected_terms

        # Test a different field.
        kwargs = {
            '_aggs.platform': ['product'],
        }
        res = self.api.get(**kwargs)

        assert 'facets' in res
        assert 'platform' in res['facets']

        expected_terms = [
            {
                'term': 'Linux',
                'count': 3,
                'facets': {
                    'product': [
                        {
                            'term': 'EarthRacoon',
                            'count': 1
                        },
                        {
                            'term': 'NightTrain',
                            'count': 1
                        },
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        },
                    ],
                }
            },
            {
                'term': 'Windows NT',
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        }
                    ],
                }
            },
        ]
        assert res['facets']['platform'] == expected_terms

        # Test one facet with filters
        kwargs = {
            '_aggs.signature': ['product'],
            'product': 'WaterWolf',
        }
        res = self.api.get(**kwargs)

        assert 'signature' in res['facets']
        expected_terms = [
            {
                'term': 'js::break_your_browser',
                'count': 2,
                'facets': {
                    'product': [
                        {
                            'term': 'WaterWolf',
                            'count': 2
                        },
                    ]
                }
            },
        ]
        assert res['facets']['signature'] == expected_terms

        # Test one facet with a different filter
        kwargs = {
            '_aggs.signature': ['product'],
            'platform': 'linux',
        }
        res = self.api.get(**kwargs)

        assert 'signature' in res['facets']

        expected_terms = [
            {
                'term': 'js::break_your_browser',
                'count': 2,
                'facets': {
                    'product': [
                        {
                            'term': 'NightTrain',
                            'count': 1
                        },
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        },
                    ],
                }
            },
            {
                'term': 'foo(bar)',
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'EarthRacoon',
                            'count': 1
                        }
                    ],
                }
            },
        ]
        assert res['facets']['signature'] == expected_terms

        # Test the number of results.
        kwargs = {
            '_aggs.signature': ['version'],
            'signature': '=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        assert 'signature' in res['facets']
        assert 'version' in res['facets']['signature'][0]['facets']

        version_sub_facet = res['facets']['signature'][0]['facets']['version']
        assert len(version_sub_facet) == 50  # 50 is the default

        # Test with a different number of facets results.
        kwargs = {
            '_aggs.signature': ['version'],
            '_facets_size': 20,
            'signature': '=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        assert 'signature' in res['facets']
        assert 'version' in res['facets']['signature'][0]['facets']

        version_sub_facet = res['facets']['signature'][0]['facets']['version']
        assert len(version_sub_facet) == 20

        kwargs = {
            '_aggs.signature': ['version'],
            '_facets_size': 100,
            'signature': '=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        version_sub_facet = res['facets']['signature'][0]['facets']['version']
        assert len(version_sub_facet) == number_of_crashes

        # Test with a third level aggregation.
        kwargs = {
            '_aggs.product.version': ['_cardinality.signature'],
        }
        res = self.api.get(**kwargs)

        assert 'product' in res['facets']
        product_facet = res['facets']['product']
        for pf in product_facet:
            assert 'version' in pf['facets']
            version_facet = pf['facets']['version']
            for vf in version_facet:
                assert 'cardinality_signature' in vf['facets']

        # Test with a fourth level aggregation.
        kwargs = {
            '_aggs.product.version.platform': ['_cardinality.signature'],
        }
        res = self.api.get(**kwargs)

        assert 'product' in res['facets']
        product_facet = res['facets']['product']
        for pf in product_facet:
            assert 'version' in pf['facets']
            version_facet = pf['facets']['version']
            for vf in version_facet:
                assert 'platform' in vf['facets']
                platform_facet = vf['facets']['platform']
                for lf in platform_facet:
                    assert 'cardinality_signature' in lf['facets']

        # Test errors
        args = {}
        args['_aggs.signature'] = ['unknownfield']
        with pytest.raises(BadArgumentError):
            self.api.get(**args)

    @minimum_es_version('1.0')
    def test_get_with_date_histogram(self):
        yesterday = self.now - datetime.timedelta(days=1)
        the_day_before = self.now - datetime.timedelta(days=2)

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
            'date_processed': yesterday,
        })
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'NightTrain',
            'os_name': 'Linux',
            'date_processed': the_day_before,
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
            'signature': 'crash_me_I_m_famous',
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
            '_histogram.date': ['product', 'platform'],
            'signature': '!=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        assert 'facets' in res
        assert 'histogram_date' in res['facets']

        def dt_to_midnight(date):
            return date.replace(hour=0, minute=0, second=0, microsecond=0)

        today_str = dt_to_midnight(self.now).isoformat()
        yesterday_str = dt_to_midnight(yesterday).isoformat()
        day_before_str = dt_to_midnight(the_day_before).isoformat()

        expected_terms = [
            {
                'term': day_before_str,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'NightTrain',
                            'count': 1
                        },
                    ],
                    'platform': [
                        {
                            'term': 'Linux',
                            'count': 1
                        }
                    ],
                }
            },
            {
                'term': yesterday_str,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        }
                    ],
                    'platform': [
                        {
                            'term': 'Linux',
                            'count': 1
                        }
                    ],
                }
            },
            {
                'term': today_str,
                'count': 2,
                'facets': {
                    'product': [
                        {
                            'term': 'EarthRacoon',
                            'count': 1
                        },
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        },
                    ],
                    'platform': [
                        {
                            'term': 'Linux',
                            'count': 1
                        },
                        {
                            'term': 'Windows NT',
                            'count': 1
                        }
                    ],
                }
            }
        ]
        assert res['facets']['histogram_date'] == expected_terms

        # Test one facet with filters
        kwargs = {
            '_histogram.date': ['product'],
            'product': 'WaterWolf',
        }
        res = self.api.get(**kwargs)

        assert 'histogram_date' in res['facets']
        expected_terms = [
            {
                'term': yesterday_str,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        },
                    ]
                }
            },
            {
                'term': today_str,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        },
                    ]
                }
            },
        ]
        assert res['facets']['histogram_date'] == expected_terms

        # Test one facet with a different filter
        kwargs = {
            '_histogram.date': ['product'],
            'platform': 'linux',
        }
        res = self.api.get(**kwargs)

        assert 'histogram_date' in res['facets']

        expected_terms = [
            {
                'term': day_before_str,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'NightTrain',
                            'count': 1
                        }
                    ],
                }
            },
            {
                'term': yesterday_str,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        }
                    ],
                }
            },
            {
                'term': today_str,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'EarthRacoon',
                            'count': 1
                        }
                    ],
                }
            }
        ]
        assert res['facets']['histogram_date'] == expected_terms

        # Test the number of results.
        kwargs = {
            '_histogram.date': ['version'],
            'signature': '=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        assert 'histogram_date' in res['facets']
        assert 'version' in res['facets']['histogram_date'][0]['facets']

        version_facet = res['facets']['histogram_date'][0]['facets']['version']
        assert len(version_facet) == 50  # 50 is the default

        # Test with a different number of facets results.
        kwargs = {
            '_histogram.date': ['version'],
            '_facets_size': 20,
            'signature': '=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        assert 'histogram_date' in res['facets']
        assert 'version' in res['facets']['histogram_date'][0]['facets']

        version_facet = res['facets']['histogram_date'][0]['facets']['version']
        assert len(version_facet) == 20

        kwargs = {
            '_histogram.date': ['version'],
            '_facets_size': 100,
            'signature': '=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        version_facet = res['facets']['histogram_date'][0]['facets']['version']
        assert len(version_facet) == number_of_crashes

        # Test errors
        args = {}
        args['_histogram.date'] = ['unknownfield']
        with pytest.raises(BadArgumentError):
            self.api.get(**args)

    @minimum_es_version('1.0')
    def test_get_with_date_histogram_with_bad_interval(self):
        kwargs = {
            '_histogram.date': ['product', 'platform'],
            'signature': '!=crash_me_I_m_famous',
            '_histogram_interval.date': 'xdays',  # Note! It's just wrong
        }

        # Not using assert_raises here so we can do a check on the exception
        # object when it does raise.
        try:
            self.api.get(**kwargs)
            raise AssertionError('The line above is supposed to error out')
        except BadArgumentError as exception:
            assert exception.param == '_histogram_interval.date'

    @minimum_es_version('1.0')
    def test_get_with_number_histogram(self):
        yesterday = self.now - datetime.timedelta(days=1)
        the_day_before = self.now - datetime.timedelta(days=2)

        time_str = '%Y%m%d%H%M%S'
        today_int = int(self.now.strftime(time_str))
        yesterday_int = int(yesterday.strftime(time_str))
        day_before_int = int(the_day_before.strftime(time_str))

        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'WaterWolf',
            'os_name': 'Windows NT',
            'build': today_int,
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'WaterWolf',
            'os_name': 'Linux',
            'build': yesterday_int,
            'date_processed': yesterday,
        })
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'NightTrain',
            'os_name': 'Linux',
            'build': day_before_int,
            'date_processed': the_day_before,
        })
        self.index_crash({
            'signature': 'foo(bar)',
            'product': 'EarthRacoon',
            'os_name': 'Linux',
            'build': today_int,
            'date_processed': self.now,
        })

        # Index a lot of distinct values to test the results limit.
        number_of_crashes = 51
        processed_crash = {
            'version': '10.%s',
            'signature': 'crash_me_I_m_famous',
            'build': today_int,
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
            '_histogram.build_id': ['product', 'platform'],
            'signature': '!=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        assert 'facets' in res

        expected_terms = [
            {
                'term': day_before_int,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'NightTrain',
                            'count': 1
                        },
                    ],
                    'platform': [
                        {
                            'term': 'Linux',
                            'count': 1
                        }
                    ],
                }
            },
            {
                'term': yesterday_int,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        }
                    ],
                    'platform': [
                        {
                            'term': 'Linux',
                            'count': 1
                        }
                    ],
                }
            },
            {
                'term': today_int,
                'count': 2,
                'facets': {
                    'product': [
                        {
                            'term': 'EarthRacoon',
                            'count': 1
                        },
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        },
                    ],
                    'platform': [
                        {
                            'term': 'Linux',
                            'count': 1
                        },
                        {
                            'term': 'Windows NT',
                            'count': 1
                        }
                    ],
                }
            }
        ]
        assert res['facets']['histogram_build_id'] == expected_terms

        # Test one facet with filters
        kwargs = {
            '_histogram.build_id': ['product'],
            'product': 'WaterWolf',
        }
        res = self.api.get(**kwargs)

        expected_terms = [
            {
                'term': yesterday_int,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        },
                    ]
                }
            },
            {
                'term': today_int,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        },
                    ]
                }
            },
        ]
        assert res['facets']['histogram_build_id'] == expected_terms

        # Test one facet with a different filter
        kwargs = {
            '_histogram.build_id': ['product'],
            'platform': 'linux',
        }
        res = self.api.get(**kwargs)

        expected_terms = [
            {
                'term': day_before_int,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'NightTrain',
                            'count': 1
                        }
                    ],
                }
            },
            {
                'term': yesterday_int,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'WaterWolf',
                            'count': 1
                        }
                    ],
                }
            },
            {
                'term': today_int,
                'count': 1,
                'facets': {
                    'product': [
                        {
                            'term': 'EarthRacoon',
                            'count': 1
                        }
                    ],
                }
            }
        ]
        assert res['facets']['histogram_build_id'] == expected_terms

        # Test the number of results.
        kwargs = {
            '_histogram.build_id': ['version'],
            'signature': '=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        assert 'version' in res['facets']['histogram_build_id'][0]['facets']

        version_facet = (
            res['facets']['histogram_build_id'][0]['facets']['version']
        )
        assert len(version_facet) == 50  # 50 is the default

        # Test with a different number of facets results.
        kwargs = {
            '_histogram.build_id': ['version'],
            '_facets_size': 20,
            'signature': '=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        assert 'version' in res['facets']['histogram_build_id'][0]['facets']

        version_facet = (
            res['facets']['histogram_build_id'][0]['facets']['version']
        )
        assert len(version_facet) == 20

        kwargs = {
            '_histogram.build_id': ['version'],
            '_facets_size': 100,
            'signature': '=crash_me_I_m_famous',
        }
        res = self.api.get(**kwargs)

        version_facet = (
            res['facets']['histogram_build_id'][0]['facets']['version']
        )
        assert len(version_facet) == number_of_crashes

        # Test errors
        args = {}
        args['_histogram.build_id'] = ['unknownfield']
        with pytest.raises(BadArgumentError):
            self.api.get(**args)

    @minimum_es_version('1.0')
    def test_get_with_columns(self):
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'WaterWolf',
            'os_name': 'Windows NT',
            'date_processed': self.now,
        })
        self.refresh_index()

        # Test several facets
        kwargs = {
            '_columns': ['signature', 'platform']
        }
        res = self.api.get(**kwargs)

        assert 'signature' in res['hits'][0]
        assert 'platform' in res['hits'][0]
        assert 'date' not in res['hits'][0]

        # Test a synonyme field returns the correct name.
        kwargs = {
            '_columns': ['product_2']
        }
        res = self.api.get(**kwargs)

        assert 'product_2' in res['hits'][0]
        assert 'product' not in res['hits'][0]

        # Test with 2 synonyme fields.
        kwargs = {
            '_columns': ['product', 'product_2']
        }
        res = self.api.get(**kwargs)

        assert 'product_2' in res['hits'][0]
        assert 'product' in res['hits'][0]

        # Test errors
        with pytest.raises(BadArgumentError):
            self.api.get(_columns=['unknownfield'])

        with pytest.raises(BadArgumentError):
            self.api.get(_columns=['fake_field'])

    @minimum_es_version('1.0')
    def test_get_with_beta_version(self):
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'WaterWolf',
            'version': '4.0b2',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'WaterWolf',
            'version': '4.0b3',
            'date_processed': self.now,
        })
        self.index_crash({
            'signature': 'js::break_your_browser',
            'product': 'WaterWolf',
            'version': '5.0a1',
            'date_processed': self.now,
        })
        self.refresh_index()

        # Test several facets
        kwargs = {
            'version': ['4.0b']
        }
        res = self.api.get(**kwargs)

        assert res['total'] == 2

        for hit in res['hits']:
            assert '4.0b' in hit['version']

    def test_get_against_nonexistent_index(self):
        config = self.get_base_config(es_index='socorro_test_reports_%W')
        api = SuperSearchWithFields(config=config)
        params = {
            'date': ['>2000-01-01T00:00:00', '<2000-01-10T00:00:00']
        }

        res = api.get(**params)
        assert res['total'] == 0
        assert len(res['hits']) == 0
        assert len(res['errors']) == 3  # 3 weeks are missing

    def test_get_too_large_date_range(self):
        # this is a whole year apart
        params = {
            'date': ['>2000-01-01T00:00:00', '<2001-01-10T00:00:00']
        }
        with pytest.raises(BadArgumentError):
            self.api.get(**params)

    def test_get_return_query_mode(self):
        res = self.api.get(
            signature='js',
            _return_query=True
        )
        assert 'query' in res
        assert 'indices' in res

        query = res['query']
        assert 'query' in query
        assert 'aggs' in query
        assert 'size' in query

    @minimum_es_version('1.0')
    def test_get_with_zero(self):
        res = self.api.get(
            _results_number=0,
        )
        assert len(res['hits']) == 0

    @minimum_es_version('1.0')
    def test_get_with_too_many(self):
        with pytest.raises(BadArgumentError):
            self.api.get(_results_number=1001)

    @minimum_es_version('1.0')
    @requests_mock.Mocker(real_http=True)
    def test_get_with_failing_shards(self, mock_requests):
        # Test with one failing shard.
        es_results = {
            'hits': {
                'hits': [],
                'total': 0,
                'max_score': None,
            },
            'timed_out': False,
            'took': 194,
            '_shards': {
                'successful': 9,
                'failed': 1,
                'total': 10,
                'failures': [
                    {
                        'status': 500,
                        'index': 'fake_index',
                        'reason': 'foo bar gone bad',
                        'shard': 3,
                    }
                ]
            },
        }

        mock_requests.get(
            '{url}/{index}/crash_reports/_search'.format(
                url=self.get_url(),
                index=self.config.elasticsearch.elasticsearch_index
            ),
            text=json.dumps(es_results)
        )

        res = self.api.get()
        assert 'errors' in res

        errors_exp = [
            {
                'type': 'shards',
                'index': 'fake_index',
                'shards_count': 1,
            }
        ]
        assert res['errors'] == errors_exp

        # Test with several failures.
        es_results = {
            'hits': {
                'hits': [],
                'total': 0,
                'max_score': None,
            },
            'timed_out': False,
            'took': 194,
            '_shards': {
                'successful': 9,
                'failed': 3,
                'total': 10,
                'failures': [
                    {
                        'status': 500,
                        'index': 'fake_index',
                        'reason': 'foo bar gone bad',
                        'shard': 2,
                    },
                    {
                        'status': 500,
                        'index': 'fake_index',
                        'reason': 'foo bar gone bad',
                        'shard': 3,
                    },
                    {
                        'status': 500,
                        'index': 'other_index',
                        'reason': 'foo bar gone bad',
                        'shard': 1,
                    },
                ]
            },
        }

        mock_requests.get(
            '{url}/{index}/crash_reports/_search'.format(
                url=self.get_url(),
                index=self.config.elasticsearch.elasticsearch_index
            ),
            text=json.dumps(es_results)
        )

        res = self.api.get()
        assert 'errors' in res

        errors_exp = [
            {
                'type': 'shards',
                'index': 'fake_index',
                'shards_count': 2,
            },
            {
                'type': 'shards',
                'index': 'other_index',
                'shards_count': 1,
            },
        ]
        assert res['errors'] == errors_exp
