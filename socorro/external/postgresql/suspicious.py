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
    signatures.signature, scs.report_date
FROM
    suspicious_crash_signatures scs
JOIN signatures ON
    scs.signature_id=signatures.signature_id
WHERE
    scs.report_date >= DATE %(start_date)s AND
    scs.report_date < DATE %(end_date)s
"""


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

        results = self.query(SQL, params)

        suspicious_stats = {}
        for signature, date in results:
            suspicious_stats.setdefault(date.strftime('%Y-%m-%d'), []).append(
                signature
            )

        return suspicious_stats
