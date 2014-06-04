# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from socorro.external.postgresql.service_base import (
    PostgreSQLWebServiceBase
)
from socorro.lib import datetimeutil


#==============================================================================
class CrontabberState(PostgreSQLWebServiceBase):
    """Implement the /crontabber_state_service with PostgreSQL. """

    uri = r'/crontabber_state/(.*)'

    #--------------------------------------------------------------------------
    def get(self, **kwargs):
        """Return the current state of all Crontabber jobs"""

        sql = """
/* socorro.external.postgresql.crontabber_state_service.CrontabberState.get */
            SELECT
                app_name,
                next_run,
                first_run,
                last_run,
                last_success,
                error_count,
                depends_on,
                last_error
            FROM crontabber
            ORDER BY app_name
        """

        error_message = (
            "Failed to retrieve crontabber state data from PostgreSQL"
        )
        results = self.query(sql, error_message=error_message)
        state = {}
        for row in results:
            app_name = row[0]
            state[app_name] = dict(zip((
                'next_run',
                'first_run',
                'last_run',
                'last_success',
                'error_count',
                'depends_on',
                'last_error'
            ), row[1:]))
            for key in ('next_run', 'first_run', 'last_run', 'last_success'):
                value = state[app_name][key]
                if value is None:
                    continue
                state[app_name][key] = datetimeutil.date_to_string(value)
            state[app_name]['last_error'] = json.loads(
                state[app_name]['last_error']
            )

        return {"state": state}
