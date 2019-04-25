# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import pytest

from crashstats.crashstats.configman_utils import config_from_configman
from socorro.external.es.connection_context import ConnectionContext


@pytest.fixture
def es_conn():
    """Create an Elasticsearch ConnectionContext and clean up indices afterwards."""
    conn = ConnectionContext(config_from_configman()['elasticsearch'])
    yield conn
    for index in conn.get_indices():
        conn.delete_index(index)
