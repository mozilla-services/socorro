# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import elasticsearch
from elasticsearch.helpers import bulk

from configman import Namespace, RequiredConfig
from configman.converters import list_converter


class ConnectionContext(RequiredConfig):
    """Abstraction layer for Elasticsearch interactions.

    This is used to create connections to Elasticsearch, and contains some
    utility functions to interact with it.
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
        'elasticsearch_default_index',
        default='socorro',
        doc='the default index used to store data',
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

    def __init__(self, config):
        self.config = config
        super(self.__class__, self).__init__()

    def get_connection(self):
        """Return a connection to Elasticsearch.

        Returns an instance of elasticsearch-py's Elasticsearch class.
        Documentation: http://elasticsearch-py.readthedocs.org
        """
        return elasticsearch.Elasticsearch(
            hosts=self.config.elasticsearch_urls,
            timeout=self.config.elasticsearch_timeout,
        )

    def bulk_index(
        self,
        index,
        doc_type,
        docs,
        id_field,
        refresh=False,
        connection=None
    ):
        """Index a list of documents into Elasticsearch all at once.

        This is a utility function primarily created as an abstraction of
        the pyelasticsearch library's bulk_index function, with the goal of
        simplifying the transition to the elasticsearch-py library.
        See bug 1051839 for context.
        """
        if connection is None:
            connection = self.get_connection()

        actions = []
        for doc in docs:
            actions.append({
                '_index': index,
                '_type': doc_type,
                '_id': doc.get(id_field),
                '_source': doc,
            })

        return bulk(connection, actions, refresh=refresh)
