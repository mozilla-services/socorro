# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import logging

from configman import Namespace, RequiredConfig
from configman.converters import list_converter
import elasticsearch

from socorro.external.es.super_search_fields import SuperSearchFields


logger = logging.getLogger(__name__)


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

    def create_socorro_index(self, index_name, mappings=None, log_result=False):
        """Create an index that will receive crash reports.

        Note: This function can get called in two contexts: when the processor
        is saving crash reports and also in the local dev environment scripts.
        The former wants to ignore index-existing errors quietly but the latter
        wants to log the result. Hence the fickle nature of this function.

        """
        if mappings is None:
            mappings = SuperSearchFields(context=self).get_mapping()

        es_settings = self.get_socorro_index_settings(mappings)
        self.create_index(index_name, es_settings, log_result)

    def create_index(self, index_name, es_settings, log_result=False):
        """Create an index in elasticsearch, with specified settings.

        If the index already exists or is created concurrently during the
        execution of this function, nothing will happen.

        """
        try:
            client = self.indices_client()
            client.create(index=index_name, body=es_settings,)
            if log_result:
                logger.info('Created new elasticsearch index: %s', index_name)
        except elasticsearch.exceptions.RequestError as e:
            # If this index already exists, swallow the error.
            # NOTE! This is NOT how the error looks like in ES 2.x
            if 'IndexAlreadyExistsException' not in str(e):
                raise
            if log_result:
                logger.info('Index exists: %s', index_name)
