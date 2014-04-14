# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external import MissingArgumentError
from socorro.lib import datetimeutil, external_common


class GCCrashes(PostgreSQLBase):

    def get(self, **kwargs):
        """ return GC crashes per build ID """

        for arg in ['product', 'version']:
            if not kwargs.get(arg):
                raise MissingArgumentError(arg)

        now = datetimeutil.utc_now().date()
        lastweek = now - datetime.timedelta(weeks=1)

        filters = [
            ("product", None, "str"),
            ("version", None, "str"),
            ("from_date", lastweek, "date"),
            ("to_date", now, "date"),
        ]

        params = external_common.parse_arguments(filters, kwargs)

        result = self.query("""
            /* socorro.external.postgresql.gccrashes.GCCrashes.get */
            SELECT
                build::text,
                sum(gc_count_madu)
            FROM gccrashes
            JOIN product_versions
            USING (product_version_id)
            WHERE product_name = %(product)s
            AND version_string = %(version)s
            AND report_date BETWEEN %(from_date)s AND %(to_date)s
            AND build IS NOT NULL
            GROUP BY build
            ORDER BY build
        """, params)

        return {'hits': result, 'total': len(result)}
