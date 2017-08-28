# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import datetime
from nose.tools import assert_raises, eq_, ok_

from socorro.lib import BadArgumentError
from socorro.external.es.super_search_fields import SuperSearchFields
from socorro.lib import datetimeutil
from socorro.unittest.external.es.base import (
    SUPERSEARCH_FIELDS,
    ElasticsearchTestCase,
    minimum_es_version,
)

# Uncomment these lines to decrease verbosity of the elasticsearch library
# while running unit tests.
# import logging
# logging.getLogger('elasticsearch').setLevel(logging.ERROR)
# logging.getLogger('requests').setLevel(logging.ERROR)


class IntegrationTestSuperSearchFields(ElasticsearchTestCase):
    """Test SuperSearchFields with an elasticsearch database containing fake
    data. """

    def setUp(self):
        super(IntegrationTestSuperSearchFields, self).setUp()

        self.api = SuperSearchFields(config=self.config)
        self.api.get_fields = lambda: copy.deepcopy(SUPERSEARCH_FIELDS)

    def test_get_fields(self):
        results = self.api.get_fields()
        eq_(results, SUPERSEARCH_FIELDS)

    @minimum_es_version('1.0')
    def test_get_missing_fields(self):
        config = self.get_base_config(
            es_index='socorro_integration_test_%W'
        )

        fake_mappings = [
            {
                'mappings': {
                    config.elasticsearch.elasticsearch_doctype: {
                        'properties': {
                            # Add a bunch of unknown fields.
                            'field_z': {
                                'type': 'string'
                            },
                            'namespace1': {
                                'type': 'object',
                                'properties': {
                                    'field_a': {
                                        'type': 'string'
                                    },
                                    'field_b': {
                                        'type': 'long'
                                    }
                                }
                            },
                            'namespace2': {
                                'type': 'object',
                                'properties': {
                                    'subspace1': {
                                        'type': 'object',
                                        'properties': {
                                            'field_b': {
                                                'type': 'long'
                                            }
                                        }
                                    }
                                }
                            },
                            # Add a few known fields that should not appear.
                            'processed_crash': {
                                'type': 'object',
                                'properties': {
                                    'signature': {
                                        'type': 'string'
                                    },
                                    'product': {
                                        'type': 'string'
                                    },
                                }
                            }
                        }
                    }
                }
            },
            {
                'mappings': {
                    config.elasticsearch.elasticsearch_doctype: {
                        'properties': {
                            'namespace1': {
                                'type': 'object',
                                'properties': {
                                    'subspace1': {
                                        'type': 'object',
                                        'properties': {
                                            'field_d': {
                                                'type': 'long'
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
        ]

        now = datetimeutil.utc_now()
        indices = []

        try:
            # Using "2" here means that an index will be missing, hence testing
            # that it swallows the subsequent error.
            for i in range(2):
                date = now - datetime.timedelta(weeks=i)
                index = date.strftime(config.elasticsearch.elasticsearch_index)
                mapping = fake_mappings[i % len(fake_mappings)]

                self.index_creator.create_index(index, mapping)
                indices.append(index)

            api = SuperSearchFields(config=config)
            missing_fields = api.get_missing_fields()
            expected = [
                'field_z',
                'namespace1.field_a',
                'namespace1.field_b',
                'namespace1.subspace1.field_d',
                'namespace2.subspace1.field_b',
            ]

            eq_(missing_fields['hits'], expected)
            eq_(missing_fields['total'], 5)

        finally:
            for index in indices:
                self.index_client.delete(index=index)

    def test_get_mapping(self):
        mapping = self.api.get_mapping()
        doctype = self.config.elasticsearch.elasticsearch_doctype

        ok_(doctype in mapping)
        properties = mapping[doctype]['properties']

        ok_('processed_crash' in properties)
        ok_('raw_crash' in properties)

        processed_crash = properties['processed_crash']['properties']

        # Check in_database_name is used.
        ok_('os_name' in processed_crash)
        ok_('platform' not in processed_crash)

        # Those fields have no `storage_mapping`.
        ok_('fake_field' not in properties['raw_crash']['properties'])

        # Those fields have a `storage_mapping`.
        eq_(processed_crash['release_channel'], {'type': 'string'})

        # Test nested objects.
        ok_('json_dump' in processed_crash)
        ok_('properties' in processed_crash['json_dump'])
        ok_('write_combine_size' in processed_crash['json_dump']['properties'])
        eq_(
            processed_crash['json_dump']['properties']['write_combine_size'],
            {'type': 'long'}
        )

        # Test overwriting a field.
        mapping = self.api.get_mapping(overwrite_mapping={
            'name': 'fake_field',
            'storage_mapping': {
                'type': 'long'
            }
        })
        properties = mapping[doctype]['properties']

        ok_('fake_field' in properties['raw_crash']['properties'])
        eq_(
            properties['raw_crash']['properties']['fake_field']['type'],
            'long'
        )

    def test_test_mapping(self):
        """Much test. So meta. Wow test_test_. """
        # First test a valid mapping.
        mapping = self.api.get_mapping()
        ok_(self.api.test_mapping(mapping) is None)

        # Insert an invalid storage mapping.
        mapping = self.api.get_mapping({
            'name': 'fake_field',
            'storage_mapping': {
                'type': 'unkwown'
            }
        })
        assert_raises(
            BadArgumentError,
            self.api.test_mapping,
            mapping,
        )

        # Test with a correct mapping but with data that cannot be indexed.
        self.index_crash({
            'date_processed': datetimeutil.utc_now(),
            'product': 'WaterWolf',
        })
        self.refresh_index()
        mapping = self.api.get_mapping({
            'name': 'product',
            'storage_mapping': {
                'type': 'long'
            }
        })
        assert_raises(
            BadArgumentError,
            self.api.test_mapping,
            mapping,
        )
