# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import datetimeutil, external_common

logger = logging.getLogger("webapi")


class CrashTrends(PostgreSQLBase):

    def get(self, **kwargs):
        filters = [
            ("start_date", None, "datetime"),
            ("end_date", None, "datetime"),
            ("product", None, "str"),
            ("version", None, "str"),
        ]

        params = external_common.parse_arguments(filters, kwargs)

        sql = """
        /* socorro.external.postgresql.crash_trends.CrashTrends.get */
        SELECT product_name,
               version_string,
               product_version_id,
               report_date,
               nightly_builds.build_date,
               days_out,
               sum(report_count) as report_count
        FROM nightly_builds
            JOIN product_versions USING ( product_version_id )
        WHERE report_date <= %(end_date)s
        AND report_date >= %(start_date)s
        AND product_name = %(product)s
        AND version_string = %(version)s
        GROUP BY product_name,
                 version_string,
                 product_version_id,
                 report_date,
                 nightly_builds.build_date,
                 days_out
        """

        error_message = "Failed to retrieve crash trends data from PostgreSQL"
        sql_results = self.query(sql, params, error_message=error_message)

        results = []
        for row in sql_results:
            trend = dict(zip((
                "product_name",
                "version_string",
                "product_version_id",
                "report_date",
                "build_date",
                "days_out",
                "report_count"
            ), row))
            trend['report_date'] = datetimeutil.date_to_string(
                trend['report_date'])
            trend['build_date'] = datetimeutil.date_to_string(
                trend['build_date'])
            results.append(trend)

        return {'crashtrends': results}
