import logging
import psycopg2

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common, util

import socorro.database.database as db

logger = logging.getLogger("webapi")


class Extensions(PostgreSQLBase):

    """
    Implement the /extensions service with PostgreSQL.
    """

    def __init__(self, *args, **kwargs):
        super(Extensions, self).__init__(*args, **kwargs)

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

        results = []

        # Creating the connection to the DB
        self.connection = self.database.connection()
        cur = self.connection.cursor()

        try:
            logger.debug(cur.mogrify(sql, sql_params))
            results = db.execute(cur, sql, sql_params)
        except psycopg2.Error:
            util.reportExceptionAndContinue(logger)

        json_result = {
            "total": 0,
            "hits": []
        }

        for crash in results:
            row = dict(zip((
                       "report_id",
                       "date_processed",
                       "extension_key",
                       "extension_id",
                       "extension_version"), crash))
            json_result["hits"].append(row)
            row["date_processed"] = str(row["date_processed"])
        json_result["total"] = len(json_result["hits"])

        self.connection.close()

        return json_result
