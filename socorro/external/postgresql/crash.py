# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external import MissingArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import datetimeutil, external_common

logger = logging.getLogger("webapi")


class Crash(PostgreSQLBase):

    """
    Implement the /crash service with PostgreSQL.
    """

    def get(self, **kwargs):
        """Return a single crash report from its UUID. """
        filters = [
            ("uuid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        if params.uuid is None:
            raise MissingArgumentError("uuid")
        crash_date = datetimeutil.uuid_to_date(params.uuid)
        logger.debug("Looking for crash %s during day %s" % (params.uuid,
                                                             crash_date))

        sql = """/* socorro.external.postgresql.crash.Crash.get */
            SELECT
                reports.signature,
                reports.email,
                reports.url,
                reports.addons_checked,
                reports.exploitability,
                (   SELECT reports_duplicates.duplicate_of
                    FROM reports_duplicates
                    WHERE reports_duplicates.uuid = reports.uuid
                ) as duplicate_of
            FROM reports
            WHERE reports.uuid=%(uuid)s
            AND reports.success IS NOT NULL
            AND utc_day_is( reports.date_processed,  %(crash_date)s)
        """
        sql_params = {
            "uuid": params.uuid,
            "crash_date": crash_date
        }

        error_message = "Failed to retrieve crash data from PostgreSQL"
        results = self.query(sql, sql_params, error_message=error_message)

        crashes = []
        for row in results:
            crash = dict(zip((
                       "signature",
                       "email",
                       "url",
                       "addons_checked",
                       "exploitability",
                       "duplicate_of"), row))
            crashes.append(crash)

        return {
            "hits": crashes,
            "total": len(crashes)
        }
