# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import elasticsearch

from configman import Namespace, RequiredConfig
from configman.converters import list_converter


class ConnectionContext(RequiredConfig):
    """This class represents a connection to Elasticsearch. """

    required_config = Namespace()
    required_config.add_option(
        'elasticsearch_urls',
        default=['localhost:9200'],
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
        super(ConnectionContext, self).__init__()
        self.config = config

    def connection(self):
        """Return a connection to Elasticsearch.

        Returns an instance of elasticsearch-py's Elasticsearch class.
        Documentation: http://elasticsearch-py.readthedocs.org
        """
        return elasticsearch.Elasticsearch(
            hosts=self.config.elasticsearch_urls,
            timeout=self.config.elasticsearch_timeout,
            connection_class=elasticsearch.connection.RequestsHttpConnection,
        )

    @contextlib.contextmanager
    def __call__(self):
        conn = self.connection()
        try:
            yield conn
        finally:
            self.close_connection(conn)

    def close_connection(self, connection, force=False):
        pass
