# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import datetimeutil, external_common

logger = logging.getLogger("webapi")


class ServerStatus(PostgreSQLBase):
    """Implement the /server_status service with PostgreSQL. """

    def get(self, **kwargs):
        """Return the current state of the server and the revisions of Socorro
        and Breakpad. """
        filters = [
            ("duration", 12, "int"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        sql = """
            /* socorro.external.postgresql.server_status.ServerStatus.get */
            SELECT
                id,
                date_recently_completed,
                date_oldest_job_queued,
                avg_process_sec,
                avg_wait_sec,
                waiting_job_count,
                processors_count,
                date_created
            FROM server_status
            ORDER BY date_created DESC
            LIMIT %(duration)s
        """

        error_message = "Failed to retrieve server status data from PostgreSQL"
        results = self.query(sql, params, error_message=error_message)

        stats = []
        for row in results:
            stat = dict(zip((
                "id",
                "date_recently_completed",
                "date_oldest_job_queued",
                "avg_process_sec",
                "avg_wait_sec",
                "waiting_job_count",
                "processors_count",
                "date_created"
            ), row))

            # Turn dates into strings for later JSON encoding
            for i in ("date_recently_completed",
                      "date_oldest_job_queued",
                      "date_created"):
                try:
                    stat[i] = datetimeutil.date_to_string(stat[i])
                except TypeError:
                    pass

            stats.append(stat)

        if hasattr(self.context, 'revisions'):
            revisions = self.context.revisions
        else:
            # old middleware
            revisions = self.context

        return {
            "hits": stats,
            "total": len(stats),
            "socorro_revision": revisions.socorro_revision,
            "breakpad_revision": revisions.breakpad_revision
        }
