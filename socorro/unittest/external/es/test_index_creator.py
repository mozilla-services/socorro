# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import elasticsearch

from nose.plugins.attrib import attr
from nose.tools import ok_

from socorro.external.es.index_creator import IndexCreator
from socorro.unittest.external.es.base import ElasticsearchTestCase

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


@attr(integration='elasticsearch')  # for nosetests
class IntegrationTestIndexCreator(ElasticsearchTestCase):
    def __init__(self, *args, **kwargs):
        super(IntegrationTestIndexCreator, self).__init__(*args, **kwargs)

        self.config = self.get_tuned_config(IndexCreator)

    def tearDown(self):
        """Remove any indices that may have been created for a given test.
        """
        try:
            self.index_client.delete(
                self.config.elasticsearch.elasticsearch_emails_index
            )
        # "Missing" indices simply weren't created, so ignore.
        except elasticsearch.exceptions.NotFoundError:
            pass

        super(IntegrationTestIndexCreator, self).tearDown()

    def test_create_index(self):
        index_creator = IndexCreator(config=self.config)
        index_creator.create_index(
            self.config.elasticsearch.elasticsearch_index,
            {'foo': 'bar'}
        )

        ok_(
            self.index_client.exists(
                self.config.elasticsearch.elasticsearch_index
            )
        )

    def test_create_emails_index(self):
        index_creator = IndexCreator(config=self.config)
        index_creator.create_emails_index()

        ok_(
            self.index_client.exists(
                self.config.elasticsearch.elasticsearch_emails_index
            )
        )

    def test_create_socorro_index(self):
        index_creator = IndexCreator(config=self.config)
        index_creator.create_socorro_index(
            self.config.elasticsearch.elasticsearch_index
        )

        ok_(
            self.index_client.exists(
                self.config.elasticsearch.elasticsearch_index
            )
        )
