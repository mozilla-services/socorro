# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import elasticsearch

from configman import Namespace, RequiredConfig
from configman.converters import list_converter


class ConnectionContext(RequiredConfig):
    """This class represents a connection to Elasticsearch"""
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
