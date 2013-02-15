# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import datetimeutil

logger = logging.getLogger("webapi")


class CrontabberState(PostgreSQLBase):
    """Implement the /crontabber_state service with PostgreSQL. """

    def get(self, **kwargs):
        """Return the current state of the server and the revisions of Socorro
        and Breakpad. """
        sql = (
            '/* socorro.external.postgresql.crontabber_state.CrontabberState'
            '.get */\n'
            'SELECT state, last_updated FROM crontabber_state;'
        )

        error_message = (
            "Failed to retrieve crontabber state data from PostgreSQL"
        )
        results = self.query(sql, error_message=error_message)
        result, = results
        state, last_updated = result
        return {
            "state": json.loads(state),
            "last_updated": datetimeutil.date_to_string(last_updated)
        }
