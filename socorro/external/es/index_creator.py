# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import elasticsearch
import os

from configman import Namespace, RequiredConfig
from configman.converters import class_converter


DIRECTORY = os.path.dirname(os.path.abspath(__file__))


# Elasticsearch indices configuration.
ES_CUSTOM_ANALYZERS = {
    'analyzer': {
        'semicolon_keywords': {
            'type': 'pattern',
            'pattern': ';',
        },
    }
}
ES_QUERY_SETTINGS = {
    'default_field': 'signature'
}


class IndexCreator(RequiredConfig):
    """The elasticsearch-py library is split into a handful of functional
    areas; this class is concerned with IndicesClient only.
    """

    required_config = Namespace()

    required_config.elasticsearch = Namespace()
    required_config.elasticsearch.add_option(
        'elasticsearch_class',
        default='socorro.external.es.connection_context.ConnectionContext',
        from_string_converter=class_converter,
        reference_value_from='resource.elasticsearch',
    )
    required_config.elasticsearch.add_option(
        'shards_per_index',
        default=10,
        doc='number of shards to set in newly created indices. Elasticsearch '
            'default is 5.',
    )

    def __init__(self, config):
        super(IndexCreator, self).__init__()
        self.config = config
        self.es_context = self.config.elasticsearch.elasticsearch_class(
            config=self.config.elasticsearch
        )

    def get_index_client(self):
        """Maintained for interoperability purposes elsewhere in the codebase.
        """
        return self.es_context.indices_client()

    def get_socorro_index_settings(self, mappings):
        """Return a dictionary containing settings for an Elasticsearch index.
        """
        return {
            'settings': {
                'index': {
                    'number_of_shards': (
                        self.config.elasticsearch.shards_per_index
                    ),
                    'query': ES_QUERY_SETTINGS,
                    'analysis': ES_CUSTOM_ANALYZERS,
                },
            },
            'mappings': mappings,
        }

    def create_socorro_index(self, es_index, mappings=None):
        """Create an index that will receive crash reports. """
        if mappings is None:
            # Import at runtime to avoid dependency circle.
            from socorro.external.es.super_search_fields import (
                SuperSearchFields
            )
            mappings = SuperSearchFields(config=self.config).get_mapping()

        es_settings = self.get_socorro_index_settings(mappings)
        self.create_index(es_index, es_settings)

    def create_index(self, es_index, es_settings):
        """Create an index in elasticsearch, with specified settings.

        If the index already exists or is created concurrently during the
        execution of this function, nothing will happen.
        """
        try:
            client = self.es_context.indices_client()
            client.create(
                index=es_index,
                body=es_settings,
            )
            self.config.logger.info(
                'Created new elasticsearch index: %s', es_index
            )
        except elasticsearch.exceptions.RequestError, e:
            # If this index already exists, swallow the error.
            # NOTE! This is NOT how the error looks like in ES 2.x
            if 'IndexAlreadyExistsException' not in str(e):
                raise
