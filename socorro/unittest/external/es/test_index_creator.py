# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.es.index_creator import IndexCreator
from socorro.unittest.external.es.base import ElasticsearchTestCase

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


class IntegrationTestIndexCreator(ElasticsearchTestCase):
    def __init__(self, *args, **kwargs):
        super(IntegrationTestIndexCreator, self).__init__(*args, **kwargs)

        self.config = self.get_tuned_config(IndexCreator)

    def test_create_index(self):
        index_creator = IndexCreator(config=self.config)
        index_creator.create_index(
            self.config.elasticsearch.elasticsearch_index,
            {'foo': 'bar'}
        )

        assert self.index_client.exists(
            self.config.elasticsearch.elasticsearch_index
        )

    def test_create_socorro_index(self):
        index_creator = IndexCreator(config=self.config)
        index_creator.create_socorro_index(
            self.config.elasticsearch.elasticsearch_index
        )

        assert self.index_client.exists(
            self.config.elasticsearch.elasticsearch_index
        )
