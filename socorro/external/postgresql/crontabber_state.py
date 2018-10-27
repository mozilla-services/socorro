# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from socorro.external.postgresql.base import PostgreSQLBase


class CrontabberState(PostgreSQLBase):
    """Implement the /crontabber_state service with PostgreSQL"""

    def get(self, **kwargs):
        """Return the current state of all Crontabber jobs"""

        sql = """
            SELECT
                app_name,
                next_run,
                first_run,
                last_run,
                last_success,
                error_count,
                depends_on,
                last_error,
                ongoing
            FROM cron_job
            ORDER BY app_name
        """

        error_message = (
            "Failed to retrieve crontabber state data from PostgreSQL"
        )
        results = self.query(sql, error_message=error_message)
        state = {}
        for row in results.zipped():
            app_name = row.pop('app_name')
            row['last_error'] = json.loads(row['last_error'])
            state[app_name] = row

        return {"state": state}
