# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from datetime import datetime, timedelta
import logging

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common

logger = logging.getLogger("webapi")

SQL = """
SELECT
    signature, date
FROM
    suspicious_crash_signatures
WHERE
    date >= DATE %(start)s AND date < DATE %(end)s
"""

ERROR_MESSAGE = "Error getting data from Postgres."


class SuspiciousCrashSignatures(PostgreSQLBase):
    """Implement /suspicious with postgres"""

    def get(self, **kwargs):
        filters = [
            ('start', None, 'string'),
            ('end', None, 'string')
        ]

        params = external_common.parse_arguments(filters, kwargs)
        if params['start'] is None:
            now = datetime.utcnow()
            today = datetime(now.year, now.month, now.day)
            params['start'] = today.strftime('%Y-%m-%d')

        if params['end'] is None:
            now1= datetime.utcnow() + timedelta(1)
            tomorrow = datetime(now1.year, now1.month, now1.day)
            params['end'] = tomorrow.strftime('%Y-%m-%d')

        results = self.query(SQL, params, ERROR_MESSAGE)

        suspicious_stats = {}
        for signature, date in results:
            suspicious_stats.setdefault(date.strftime('%Y-%m-%d'), []).append(
                signature
            )

        return suspicious_stats
