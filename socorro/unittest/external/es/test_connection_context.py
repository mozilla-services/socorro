# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import elasticsearch

from nose.plugins.attrib import attr
from nose.tools import eq_

from socorro.external.es.connection_context import (
    ConnectionContext
)
from socorro.unittest.external.es.base import ElasticsearchTestCase


@attr(integration='elasticsearch')  # for nosetests
class IntegrationTestConnectionContext(ElasticsearchTestCase):
    def __init__(self, *args, **kwargs):
        super(IntegrationTestConnectionContext, self).__init__(
            *args, **kwargs
        )

        self.config = self.get_tuned_config(ConnectionContext)
        self.es_context = ConnectionContext(config=self.config)

    def tearDown(self):
        with self.es_context() as conn:
            index_client = elasticsearch.client.IndicesClient(conn)
            index_client.delete(self.config.elasticsearch_index)

    def test_connection(self):
        with self.es_context() as conn:
            conn.index(
                index=self.config.elasticsearch_index,
                doc_type='test_doc',
                body={'foo': 'bar'},
                refresh=True,
            )

            docs = conn.search(
                index=self.config.elasticsearch_index,
                doc_type='test_doc',
            )

            eq_(len(docs['hits']['hits']), 1)
