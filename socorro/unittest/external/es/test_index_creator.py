# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import elasticsearch

from nose.plugins.attrib import attr
from nose.tools import ok_

from socorro.external.es.index_creator import IndexCreator
from socorro.unittest.external.es.base import ElasticsearchTestCase


@attr(integration='elasticsearch')  # for nosetests
class IntegrationTestIndexCreator(ElasticsearchTestCase):
    def __init__(self, *args, **kwargs):
        super(IntegrationTestIndexCreator, self).__init__(*args, **kwargs)

        self.config = self.get_tuned_config(IndexCreator)

    def setUp(self):
        super(IntegrationTestIndexCreator, self).setUp()

        # Create the supersearch fields.
        self.index_super_search_fields()

    def tearDown(self):
        index_client = IndexCreator(config=self.config).get_index_client()
        try:
            index_client.delete(self.config.elasticsearch.elasticsearch_index)
        except elasticsearch.exceptions.NotFoundError:
            pass

        try:
            index_client.delete(
                self.config.elasticsearch.elasticsearch_emails_index
            )
        except elasticsearch.exceptions.NotFoundError:
            pass

        super(IntegrationTestIndexCreator, self).tearDown()

    def test_create_index(self):
        index_creator = IndexCreator(config=self.config)

        index_creator.create_index(
            self.config.elasticsearch.elasticsearch_index,
            {}
        )

        ok_(
            index_creator.get_index_client().exists(
                self.config.elasticsearch.elasticsearch_index
            )
        )

    def test_create_emails_index(self):
        index_creator = IndexCreator(config=self.config)
        index_creator.create_emails_index()

        ok_(
            index_creator.get_index_client().exists(
                self.config.elasticsearch.elasticsearch_emails_index
            )
        )

    def test_create_socorro_index(self):
        index_creator = IndexCreator(config=self.config)
        index_creator.create_socorro_index(
            self.config.elasticsearch.elasticsearch_index
        )

        ok_(
            index_creator.get_index_client().exists(
                self.config.elasticsearch.elasticsearch_index
            )
        )
