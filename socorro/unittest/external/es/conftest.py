# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import ConfigurationManager
from configman.environment import environment
import pytest

from socorro.external.es.connection_context import ConnectionContext


@pytest.fixture
def es_conn():
    """Create an Elasticsearch ConnectionContext and clean up indices afterwards."""
    cm = ConfigurationManager(
        ConnectionContext.get_required_config(),
        values_source_list=[environment]
    )
    config = cm.get_config()
    conn = ConnectionContext(config)
    yield conn
    for index in conn.get_indices():
        conn.delete_index(index)
