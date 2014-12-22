# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import contextlib
import elasticsearch

from configman import Namespace, RequiredConfig
from configman.converters import list_converter


#==============================================================================
class Connection(object):
    """A facade in front of the ES class that standardises certain gross
    elements of its API with those of other database connection types.
    The Elasticsearch interface is a simple HTTP API, and as such, does not
    maintain open connections (i.e. no persistence). Accordingly, the commit,
    rollback, and close mechanisms cannot have any useful meaning.
    """

    #--------------------------------------------------------------------------
    def __init__(self, config, connection):
        self.config = config
        self._connection = connection

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._connection, name)


#==============================================================================
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
    required_config.add_option(
        name='elasticsearch_connection_wrapper_class',
        default=Connection,
        doc='a classname for the type of wrapper for ES connections',
        reference_value_from='resource.elasticsearch',
    )

    # Operational exceptions are retryable, conditionals require futher
    # analysis to determine if they can be retried or not.
    operational_exceptions = (
        elasticsearch.exceptions.ConnectionError,
    )
    conditional_exceptions = ()

    #--------------------------------------------------------------------------
    def __init__(self, config):
        super(ConnectionContext, self).__init__()
        self.config = config

    def connection(self, name=None, timeout=None):
        """Returns an instance of elasticsearch-py's Elasticsearch class as
        encapsulated by the Connection class above.
        Documentation: http://elasticsearch-py.readthedocs.org
        """
        if timeout is None:
            timeout = self.config.elasticsearch_timeout

        return Connection(
            self.config,
            elasticsearch.Elasticsearch(
                hosts=self.config.elasticsearch_urls,
                timeout=timeout,
                connection_class=\
                    elasticsearch.connection.RequestsHttpConnection
            )
        )

    def indices_client(self, name=None):
        """Returns an instance of elasticsearch-py's Index client class as
        encapsulated by the Connection class above.
        http://elasticsearch-py.readthedocs.org/en/master/api.html#indices
        """

        return Connection(
            self.config,
            elasticsearch.client.IndicesClient(self.connection())
        )

    def force_reconnect(self):
        pass

    @contextlib.contextmanager
    def __call__(self, name=None, timeout=None):
        conn = self.connection(name, timeout)
        yield conn
