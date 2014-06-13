# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from socorro.external.postgresql.service_base import (
    PostgreSQLWebServiceBase
)
from socorro.lib import external_common

SQL = """
SELECT
    signatures.signature, scs.report_date
FROM
    suspicious_crash_signatures scs
JOIN signatures ON
    scs.signature_id=signatures.signature_id
WHERE
    scs.report_date >= %(start_date)s AND
    scs.report_date::date < %(end_date)s
"""


#==============================================================================
class SuspiciousCrashSignatures(PostgreSQLWebServiceBase):
    """Implement /suspicious with postgres"""

    uri = r'/suspicious/(.*)'

    #--------------------------------------------------------------------------
    def get(self, **kwargs):
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(1)
        tomorrow = yesterday + datetime.timedelta(2)
        yesterday = yesterday.date()
        tomorrow = tomorrow.date()
        filters = [
            ('start_date', yesterday, 'date'),
            ('end_date', tomorrow, 'date')
        ]

        params = external_common.parse_arguments(filters, kwargs)
        results = self.query(SQL, params)

        suspicious_stats = {}
        for signature, date in results:
            suspicious_stats.setdefault(date.strftime('%Y-%m-%d'), []).append(
                signature
            )

        hits = []
        for date, signatures in suspicious_stats.iteritems():
            hits.append({'date': date, 'signatures': signatures})

        return {'hits': hits, 'total': len(hits)}
