# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib

from configman import Namespace, RequiredConfig
from configman.converters import list_converter
import elasticsearch

from socorro.external.es.super_search_fields import SuperSearchFields


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


class ConnectionContext(RequiredConfig):
    """Elasticsearch connection manager.

    Used for accessing Elasticsearch and managing indexes.

    """

    required_config = Namespace()
    required_config.add_option(
        'elasticsearch_urls',
        default=['http://localhost:9200'],
        doc='the urls to the elasticsearch instances',
        from_string_converter=list_converter,
        reference_value_from='resource.elasticsearch',
    )
    required_config.add_option(
        'elasticsearch_timeout',
        default=30,
        doc='the time in seconds before a query to elasticsearch fails',
        reference_value_from='resource.elasticsearch',
    )
    required_config.add_option(
        'elasticsearch_timeout_extended',
        default=120,
        doc='the time in seconds before a query to elasticsearch fails in '
            'restricted sections',
        reference_value_from='resource.elasticsearch',
    )
    required_config.add_option(
        'elasticsearch_index',
        default='socorro%Y%W',
        doc='an index format to pull crashes from elasticsearch '
            "(use datetime's strftime format to have "
            'daily, weekly or monthly indexes)',
        reference_value_from='resource.elasticsearch',
    )
    required_config.add_option(
        'elasticsearch_doctype',
        default='crash_reports',
        doc='the default doctype to use in elasticsearch',
        reference_value_from='resource.elasticsearch',
    )
    required_config.add_option(
        'elasticsearch_shards_per_index',
        default=10,
        doc=(
            'number of shards to set in newly created indices. Elasticsearch '
            'default is 5.'
        )
    )

    def __init__(self, config):
        super().__init__()
        self.config = config

    def connection(self, name=None, timeout=None):
        """Returns an instance of elasticsearch-py's Elasticsearch class as
        encapsulated by the Connection class above.

        Documentation: http://elasticsearch-py.readthedocs.org

        """
        if timeout is None:
            timeout = self.config.elasticsearch_timeout

        return elasticsearch.Elasticsearch(
            hosts=self.config.elasticsearch_urls,
            timeout=timeout,
            connection_class=elasticsearch.connection.RequestsHttpConnection,
            verify_certs=True
        )

    def get_index_template(self):
        """Return template for index names."""
        return self.config.elasticsearch_index

    def get_doctype(self):
        """Return doctype."""
        return self.config.elasticsearch_doctype

    def get_timeout_extended(self):
        """Return timeout_extended."""
        return self.config.elasticsearch_timeout_extended

    def indices_client(self, name=None):
        """Returns an instance of elasticsearch-py's Index client class as
        encapsulated by the Connection class above.

        http://elasticsearch-py.readthedocs.org/en/master/api.html#indices

        """
        return elasticsearch.client.IndicesClient(self.connection())

    @contextlib.contextmanager
    def __call__(self, name=None, timeout=None):
        conn = self.connection(name, timeout)
        yield conn

    def get_socorro_index_settings(self, mappings):
        """Return a dictionary containing settings for an Elasticsearch index.
        """
        return {
            'settings': {
                'index': {
                    'number_of_shards': self.config.elasticsearch_shards_per_index,
                    'query': ES_QUERY_SETTINGS,
                    'analysis': ES_CUSTOM_ANALYZERS,
                },
            },
            'mappings': mappings,
        }

    def create_index(self, index_name, mappings=None):
        """Create an index that will receive crash reports.

        :arg index_name: the name of the index to create
        :arg mappings: dict of doctype->ES mapping

        :returns: True if the index was created, False if it already
            existed

        """
        if mappings is None:
            mappings = SuperSearchFields(context=self).get_mapping()

        es_settings = self.get_socorro_index_settings(mappings)

        try:
            client = self.indices_client()
            client.create(index=index_name, body=es_settings,)
            return True

        except elasticsearch.exceptions.RequestError as e:
            # If this index already exists, swallow the error.
            # NOTE! This is NOT how the error looks like in ES 2.x
            if 'IndexAlreadyExistsException' not in str(e):
                raise
            return False
