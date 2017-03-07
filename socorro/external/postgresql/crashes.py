# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging

from socorro.lib import (
    MissingArgumentError,
    BadArgumentError,
    datetimeutil,
    external_common,
)
from socorro.external.postgresql.base import PostgreSQLBase


logger = logging.getLogger("webapi")


class AduBySignature(PostgreSQLBase):

    def get(self, **kwargs):
        """Return a list of ADUs and crash counts by signature and ADU date
        """
        now = datetimeutil.utc_now().date()
        lastweek = now - datetime.timedelta(weeks=1)

        filters = [
            ("start_date", lastweek, "date"),
            ("end_date", now, "date"),
            ("signature", None, "str"),
            ("channel", None, "str"),
            ("product_name", None, "str"),
        ]

        params = external_common.parse_arguments(filters, kwargs)

        for param in ("start_date", "end_date", "signature", "channel"):
            if not params[param]:
                raise MissingArgumentError(param)

        if params.end_date - params.start_date > datetime.timedelta(days=365):
            raise BadArgumentError('Duration too long. Max 365 days.')

        sql_query = """
            SELECT
                product_name,
                signature,
                adu_date::TEXT,
                build_date::TEXT,
                buildid::TEXT,
                crash_count,
                adu_count,
                os_name,
                channel
            FROM crash_adu_by_build_signature
            WHERE adu_date BETWEEN %(start_date)s AND %(end_date)s
            AND product_name = %(product_name)s
            AND channel = %(channel)s
            AND signature = %(signature)s
            ORDER BY buildid
        """

        error_message = (
            "Failed to retrieve crash ADU by build signature from PostgreSQL"
        )
        results = self.query(sql_query, params, error_message=error_message)

        crashes = results.zipped()

        return {
            "hits": crashes,
            "total": len(crashes)
        }
