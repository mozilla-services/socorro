# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json

from nose.tools import eq_, ok_

from socorro.external.es.correlations import (
    Correlations,
    CoreCounts,
    InterestingModules,
)
from socorro.unittest.external.es.base import ElasticsearchTestCase

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


ES_CORRELATIONS_INDEX = 'integration_test_correlations_%Y%m'


sample_core_counts_summary = {
    'notes': 'Some notes',
    '': {
        'count': 4,
        'signatures': {},
    },
    'Linux': {
        'count': 1,
        'signatures': {},
    },
    'Windows NT': {
        'count': 493,
        'signatures': {
            'my__special__signature': {
                'cores': {
                    'amd64 with 4 cores': {
                        'in_os_count': 1,
                        'in_os_ratio': 0.002028397565922921,
                        'in_sig_count': 0,
                        'in_sig_ratio': 0.0,
                        'rounded_in_os_ratio': 0,
                        'rounded_in_sig_ratio': 0
                    }
                }
            }
        }

    }
}

sample_interesting_modules_summary = {
    'notes': [],
    'os_counters': {
        '': {
            'count': 4,
            'signatures': {},
        },
        'Windows NT': {
            'count': 493,
            'signatures': {
                'F1398665248_|EXCEPTION_BREAKPOINT': {
                    'count': 19,
                    'modules': {
                        "{82AF8DCA-6DE9-405D-BD5E-43525BDAD38A}": {
                            "in_os_count": 43,
                            "in_os_ratio": 9,
                            "in_sig_count": 8,
                            "in_sig_ratio": 22,
                            "osys_count": 493,
                        }
                    }
                }
            }
        }
    }
}


class BaseTestCorrelations(ElasticsearchTestCase):
    def __init__(self, *args, **kwargs):
        super(BaseTestCorrelations, self).__init__(*args, **kwargs)

        self.config = self.get_tuned_config(Correlations, {
            'elasticsearch_correlations_index': ES_CORRELATIONS_INDEX
        })

        # Indices that will be created during the tests and should be
        # deleted in tearDown.
        self.indices_for_deletion = []

    def tearDown(self):
        # Clear the test indices.
        for index in self.indices_for_deletion:
            self.index_client.delete(index)

        super(BaseTestCorrelations, self).tearDown()


class IntegrationTestCorrelations(BaseTestCorrelations):

    def test_create_correlations_index(self):
        today = datetime.datetime.utcnow().date()

        correlations = Correlations(config=self.config)

        es_index = correlations.get_index_for_date(today)
        correlations.create_correlations_index(es_index)
        self.indices_for_deletion.append(es_index)

        expected_index = today.strftime(ES_CORRELATIONS_INDEX)
        eq_(es_index, expected_index)
        ok_(self.index_client.exists(expected_index))

        # We should be able to create that index again without any errors.
        correlations.create_correlations_index(es_index)


class TestCoreCounts(BaseTestCorrelations):

    def test_store(self):
        correlations = CoreCounts(config=self.config)
        today = datetime.datetime.utcnow()
        correlations.store(
            sample_core_counts_summary,
            today.strftime('%Y%m%d'),
            'core-counts',
            'Firefox_43.0.1'
        )
        es_index = correlations.get_index_for_date(today.date())
        correlations.create_correlations_index(es_index)
        self.indices_for_deletion.append(es_index)
        self.refresh_index(es_index)
        result = self.connection.search(
            index=es_index,
            doc_type='correlations',
        )['hits']
        eq_(result['total'], 1)
        hit, = result['hits']
        _source = hit['_source']
        eq_(
            _source['count'],
            sample_core_counts_summary['Windows NT']['count']
        )
        eq_(
            _source['signature'],
            sample_core_counts_summary['Windows NT']['signatures'].keys()[0]
        )
        eq_(_source['date'], today.strftime('%Y-%m-%d'))
        eq_(_source['notes'], sample_core_counts_summary['notes'])
        eq_(_source['key'], 'core-counts')
        eq_(_source['platform'], 'Windows NT')
        eq_(_source['product'], 'Firefox')
        eq_(_source['version'], '43.0.1')
        payload, = (
            sample_core_counts_summary['Windows NT']['signatures'].values()
        )
        eq_(_source['payload'], json.dumps(payload))


class TestInterestingModules(BaseTestCorrelations):

    def test_store(self):
        correlations = InterestingModules(config=self.config)
        today = datetime.datetime.utcnow()
        correlations.store(
            sample_interesting_modules_summary,
            today.strftime('%Y%m%d'),
            'interesting-addons',
            'Firefox_45.0b1'
        )
        es_index = correlations.get_index_for_date(today.date())
        correlations.create_correlations_index(es_index)
        self.indices_for_deletion.append(es_index)
        self.refresh_index(es_index)
        result = self.connection.search(
            index=es_index,
            doc_type='correlations',
        )['hits']
        eq_(result['total'], 1)
        hit, = result['hits']
        _source = hit['_source']
        eq_(
            _source['count'],
            sample_interesting_modules_summary
            ['os_counters']['Windows NT']['count']
        )
        eq_(
            _source['signature'],
            sample_interesting_modules_summary
            ['os_counters']['Windows NT']['signatures'].keys()[0]
        )
        eq_(_source['date'], today.strftime('%Y-%m-%d'))
        eq_(_source['notes'], sample_interesting_modules_summary['notes'])
        eq_(_source['key'], 'interesting-addons')
        eq_(_source['platform'], 'Windows NT')
        eq_(_source['product'], 'Firefox')
        eq_(_source['version'], '45.0b1')
        payload, = (
            sample_interesting_modules_summary
            ['os_counters']['Windows NT']['signatures'].values()
        )
        eq_(_source['payload'], json.dumps(payload))
