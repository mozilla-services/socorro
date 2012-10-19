# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import datetimeutil, external_common

logger = logging.getLogger("webapi")


class Extensions(PostgreSQLBase):
    """Handle extensions of crash reports. """

    def get(self, **kwargs):
        """Return a list of extensions associated with a crash's UUID."""
        filters = [
            ("uuid", None, "str"),
            ("date", None, "datetime"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        sql = """/* socorro.external.postgresql.extensions.Extensions.get */
            SELECT extensions.*
            FROM extensions
            INNER JOIN reports ON extensions.report_id = reports.id
            WHERE reports.uuid = %(uuid)s
            AND reports.date_processed = %(crash_date)s
            AND extensions.date_processed = %(crash_date)s
        """
        sql_params = {
            "uuid": params.uuid,
            "crash_date": params.date
        }

        error_message = "Failed to retrieve extensions data from PostgreSQL"
        results = self.query(sql, sql_params, error_message=error_message)

        crashes = []
        for row in results:
            crash = dict(zip((
                       "report_id",
                       "date_processed",
                       "extension_key",
                       "extension_id",
                       "extension_version"), row))
            crash["date_processed"] = datetimeutil.date_to_string(
                crash["date_processed"])
            crashes.append(crash)

        return {
            "hits": crashes,
            "total": len(crashes)
        }
