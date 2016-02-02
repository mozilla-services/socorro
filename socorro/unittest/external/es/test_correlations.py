# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from nose.tools import eq_, ok_

from socorro.external.es.correlations import Correlations
from socorro.unittest.external.es.base import ElasticsearchTestCase

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


ES_CORRELATIONS_INDEX = 'integration_test_correlations_%Y%m'


class IntegrationTestCorrelations(ElasticsearchTestCase):
    def __init__(self, *args, **kwargs):
        super(IntegrationTestCorrelations, self).__init__(*args, **kwargs)

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

        super(IntegrationTestCorrelations, self).tearDown()

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
