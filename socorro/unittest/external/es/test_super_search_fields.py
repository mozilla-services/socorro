# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy
import datetime

import pytest

from socorro.lib import BadArgumentError
from socorro.external.es.super_search_fields import FIELDS, SuperSearchFields
from socorro.lib import datetimeutil
from socorro.unittest.external.es.base import (
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
        self.api.get_fields = lambda: copy.deepcopy(FIELDS)

    def test_get_fields(self):
        results = self.api.get_fields()
        assert results == FIELDS

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

            assert missing_fields['hits'] == expected
            assert missing_fields['total'] == 5

        finally:
            for index in indices:
                self.index_client.delete(index=index)

    def test_get_mapping(self):
        mapping = self.api.get_mapping()
        doctype = self.config.elasticsearch.elasticsearch_doctype

        assert doctype in mapping
        properties = mapping[doctype]['properties']

        assert 'processed_crash' in properties
        assert 'raw_crash' in properties

        processed_crash = properties['processed_crash']['properties']

        # Check in_database_name is used.
        assert 'os_name' in processed_crash
        assert 'platform' not in processed_crash

        # Those fields have no `storage_mapping`.
        assert 'fake_field' not in properties['raw_crash']['properties']

        # Those fields have a `storage_mapping`.
        assert processed_crash['release_channel'] == {'analyzer': 'keyword', 'type': 'string'}

        # Test nested objects.
        assert 'json_dump' in processed_crash
        assert 'properties' in processed_crash['json_dump']
        assert 'write_combine_size' in processed_crash['json_dump']['properties']
        assert processed_crash['json_dump']['properties']['write_combine_size'] == {'type': 'long'}

        # Test overwriting a field.
        mapping = self.api.get_mapping(overwrite_mapping={
            'name': 'fake_field',
            'namespace': 'raw_crash',
            'in_database_name': 'fake_field',
            'storage_mapping': {
                'type': 'long'
            }
        })
        properties = mapping[doctype]['properties']

        assert 'fake_field' in properties['raw_crash']['properties']
        assert properties['raw_crash']['properties']['fake_field']['type'] == 'long'

    def test_test_mapping(self):
        """Much test. So meta. Wow test_test_. """
        # First test a valid mapping.
        mapping = self.api.get_mapping()
        assert self.api.test_mapping(mapping) is None

        # Insert an invalid storage mapping.
        mapping = self.api.get_mapping({
            'name': 'fake_field',
            'namespace': 'raw_crash',
            'in_database_name': 'fake_field',
            'storage_mapping': {
                'type': 'unkwown'
            }
        })
        with pytest.raises(BadArgumentError):
            self.api.test_mapping(mapping)

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
        with pytest.raises(BadArgumentError):
            self.api.test_mapping(mapping)


def get_fields():
    return FIELDS.items()


@pytest.mark.parametrize('name, properties', get_fields())
def test_validate_super_search_fields(name, properties):
    """Validates the contents of socorro.external.es.super_search_fields.FIELDS"""

    # FIXME(willkg): When we start doing schema stuff in Python, we should
    # switch this to a schema validation.

    property_keys = [
        'data_validation_type',
        'default_value',
        'description',
        'form_field_choices',
        'has_full_version',
        'in_database_name',
        'is_exposed',
        'is_mandatory',
        'is_returned',
        'name',
        'namespace',
        'permissions_needed',
        'query_type',
        'storage_mapping',
    ]

    # Assert it has all the keys
    assert sorted(properties.keys()) == sorted(property_keys)

    # Assert boolean fields have boolean values
    for key in ['has_full_version', 'is_exposed', 'is_mandatory', 'is_returned']:
        assert properties[key] in (True, False)

    # Assert data_validation_type has a valid value
    assert properties['data_validation_type'] in ('bool', 'datetime', 'enum', 'int', 'str')

    # Assert query_type has a valid value
    assert properties['query_type'] in ('bool', 'date', 'enum', 'flag', 'number', 'string')

    # The name in the mapping should be the same as the name in properties
    assert properties['name'] == name
