# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
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
    date >= DATE %(start_date)s AND date < DATE %(end_date)s
"""

ERROR_MESSAGE = "Error getting data from Postgres."


class SuspiciousCrashSignatures(PostgreSQLBase):
    """Implement /suspicious with postgres"""

    def get(self, **kwargs):
        filters = [
            ('start_date', None, 'string'),
            ('end_date', None, 'string')
        ]

        params = external_common.parse_arguments(filters, kwargs)
        if params['start_date'] is None:
            now = datetime.datetime.utcnow()
            params['start_date'] = now.strftime('%Y-%m-%d')

        if params['end_date'] is None:
            tomorrow = datetime.datetime.utcnow() + datetime.timedelta(1)
            params['end_date'] = tomorrow.strftime('%Y-%m-%d')

        results = self.query(SQL, params, ERROR_MESSAGE)

        suspicious_stats = {}
        for signature, date in results:
            suspicious_stats.setdefault(date.strftime('%Y-%m-%d'), []).append(
                signature
            )

        return suspicious_stats
