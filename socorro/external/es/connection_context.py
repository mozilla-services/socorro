# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from contextlib import contextmanager

from elasticsearch import Elasticsearch, RequestError


class ConnectionContext:
    """Elasticsearch connection manager.

    Used for accessing Elasticsearch and managing indexes.

    """

    def __init__(
        self,
        url="http://localhost:9200",
        timeout=30,
        ca_certs=None,
        **kwargs,
    ):
        """
        :arg url: the url to the elasticsearch instances
        :arg timeout: the time in seconds before a query to elasticsearch fails
        :arg ca_certs: path to a certs.pem file for verifying self-issued certs
        """
        self.url = url
        self.timeout = timeout
        self.ca_certs = ca_certs

    def connection(self, name=None, timeout=None):
        """Returns an instance of elasticsearch-py's Elasticsearch class as
        encapsulated by the Connection class above.

        Documentation: http://elasticsearch-py.readthedocs.org

        """
        if timeout is None:
            timeout = self.timeout

        return Elasticsearch(
            hosts=self.url,
            request_timeout=timeout,
            verify_certs=True,
            ca_certs=self.ca_certs,
        )

    def indices_client(self, name=None):
        """Returns an instance of elasticsearch-py's Index client class as
        encapsulated by the Connection class above.

        http://elasticsearch-py.readthedocs.org/en/latest/api.html#indices

        """
        return self.connection().indices

    @contextmanager
    def __call__(self, name=None, timeout=None):
        conn = self.connection(name, timeout)
        yield conn

    def create_index(self, index_name, index_settings):
        """Create an index that will receive crash reports.

        :arg index_name: the name of the index to create
        :arg index_settings: index settings including the mapping

        :returns: True if the index was created, False if it already existed

        """
        try:
            client = self.indices_client()
            client.create(index=index_name, body=index_settings)
            return True

        except RequestError as exc:
            # If this index already exists, swallow the error.
            if "resource_already_exists_exception" not in str(exc):
                raise
            return False

    def get_indices(self):
        """Return list of all indices in Elasticsearch cluster.

        :returns: list of str

        """
        return self.indices_client().get_alias().keys()

    def delete_index(self, index_name):
        """Delete an index."""
        self.indices_client().delete(index=index_name)

    def get_mapping(self, index_name):
        """Return the mapping for the specified index."""
        resp = self.indices_client().get_mapping(index=index_name)
        return resp[index_name]["mappings"]["properties"]

    def refresh(self, index_name=None):
        self.indices_client().refresh(index=index_name or "_all")

    def health_check(self):
        with self() as conn:
            conn.options(request_timeout=5).cluster.health(wait_for_status="yellow")
