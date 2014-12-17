# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import elasticsearch

from nose.plugins.attrib import attr
from nose.tools import ok_

from socorro.external.es.connection_context import (
    ConnectionContext
)
from socorro.unittest.external.es.base import ElasticsearchTestCase


@attr(integration='elasticsearch')  # for nosetests
class IntegrationTestConnectionContext(ElasticsearchTestCase):

    def test_connection_context(self):
        """Instantiate the context and ensure that it quacks like a duck.
        """
        # The context is effectively a connection factory.
        es_context = ConnectionContext(config=self.config.elasticsearch)

        # The connection context *must* have specific elements.
        ok_(es_context.config)
        ok_(es_context.connection)

        # There is one operational exception.
        ok_(
            elasticsearch.exceptions.ConnectionError in
            es_context.operational_exceptions
        )

        # Currently there are no conditional exceptions.
        ok_(len(es_context.conditional_exceptions) == 0)

    def test_connection_context_client(self):
        """Instantiate the client and ensure that it quacks like a duck.
        """
        es_context = ConnectionContext(config=self.config.elasticsearch)
        client = es_context.connection()

        # The client *must* have specific elements.
        ok_(client._connection)
        ok_(client.close)
        ok_(client.commit)
        ok_(client.config)
        ok_(client.rollback)

        # The underlying ES interface is exposed by _connection. This API is
        # exhaustive and well outside of the scope of this test suite; in the
        # interest of safety however, we'll check one here.
        ok_(client._connection.index)
