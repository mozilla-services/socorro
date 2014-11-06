# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from nose.plugins.attrib import attr
from nose.tools import eq_, ok_

from socorro.external.es.super_search_fields import SuperSearchFields
from socorro.unittest.external.es.base import (
    SUPERSEARCH_FIELDS,
    ElasticsearchTestCase,
)

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)


@attr(integration='elasticsearch')  # for nosetests
class IntegrationTestSuperSearchFields(ElasticsearchTestCase):
    """Test SuperSearchFields with an elasticsearch database containing fake
    data. """

    def setUp(self):
        super(IntegrationTestSuperSearchFields, self).setUp()

        # Create the supersearch fields.
        self.index_super_search_fields()

        self.api = SuperSearchFields(config=self.config)

    def tearDown(self):
        # Clear the test indices.
        self.index_client.delete(
            self.config.elasticsearch.elasticsearch_default_index
        )

        super(IntegrationTestSuperSearchFields, self).tearDown()

    def test_get_fields(self):
        results = self.api.get_fields()
        eq_(results, SUPERSEARCH_FIELDS)

    def test_get_mapping(self):
        mapping = self.api.get_mapping()['mappings']
        doctype = self.config.elasticsearch.elasticsearch_doctype

        ok_(doctype in mapping)
        properties = mapping[doctype]['properties']

        ok_('processed_crash' in properties)
        ok_('raw_crash' in properties)

        # Check in_database_name is used.
        ok_('os_name' in properties['processed_crash']['properties'])
        ok_('platform' not in properties['processed_crash']['properties'])

        # Those fields have no `storage_mapping`.
        ok_('fake_field' not in properties['raw_crash']['properties'])

        # Test overwriting a field.
        mapping = self.api.get_mapping(overwrite_mapping={
            'name': 'fake_field',
            'storage_mapping': {
                'type': 'long'
            }
        })['mappings']
        properties = mapping[doctype]['properties']

        ok_('fake_field' in properties['raw_crash']['properties'])
        eq_(
            properties['raw_crash']['properties']['fake_field']['type'],
            'long'
        )
