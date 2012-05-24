# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import psycopg2

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import datetimeutil, external_common, util

import socorro.database.database as db

logger = logging.getLogger("webapi")


class Extensions(PostgreSQLBase):
    """Handle extensions of crash reports.
    """

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

        result = {
            "total": 0,
            "hits": []
        }

        try:
            connection = self.database.connection()
            cur = connection.cursor()
            results = db.execute(cur, sql, sql_params)
        except psycopg2.Error:
            logger.error("Failed retrieving extensions data from PostgreSQL",
                         exc_info=True)
        else:
            for crash in results:
                row = dict(zip((
                           "report_id",
                           "date_processed",
                           "extension_key",
                           "extension_id",
                           "extension_version"), crash))
                result["hits"].append(row)
                row["date_processed"] = datetimeutil.date_to_string(row["date_processed"])
            result["total"] = len(result["hits"])
        finally:
            connection.close()

        return result
