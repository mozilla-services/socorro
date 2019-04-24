# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.unittest.external.es.base import ElasticsearchTestCase

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


class TestIntegrationIndexCreator(ElasticsearchTestCase):
    def test_create_index(self):
        context = self.es_context
        context.create_index(context.get_index_template())
        assert self.index_client.exists(context.get_index_template())
