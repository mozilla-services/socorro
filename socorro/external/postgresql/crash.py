import logging
import psycopg2
import datetime

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common, util

import socorro.database.database as db

logger = logging.getLogger("webapi")


class Crash(PostgreSQLBase):

    """
    Implement the /crash service with PostgreSQL.
    """

    def __init__(self, *args, **kwargs):
        super(Crash, self).__init__(*args, **kwargs)

    def get(self, **kwargs):
        """Return a single crash report from it's UUID. """
        filters = [
            ("uuid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        day = int(params.uuid[-2:])
        month = int(params.uuid[-4:-2])
        # assuming we won't use this after year 2099
        year = int("20%s" % params.uuid[-6:-4])

        crash_date = datetime.date(year=year, month=month, day=day)
        logger.debug("Looking for crash %s during day %s" % (params.uuid,
                                                             crash_date))

        sql = """/* socorro.external.postgresql.crash.Crash.get */
            SELECT reports.email, reports.url, reports.addons_checked,
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

        results = []

        # Creating the connection to the DB
        self.connection = self.database.connection()
        cur = self.connection.cursor()

        try:
            results = db.execute(cur, sql, sql_params)
        except psycopg2.Error:
            util.reportExceptionAndContinue(logger)

        json_result = {
            "total": 0,
            "hits": []
        }

        for crash in results:
            row = dict(zip((
                       "email",
                       "url",
                       "addons_checked",
                       "duplicate_of"), crash))
            json_result["hits"].append(row)
        json_result["total"] = len(json_result["hits"])

        self.connection.close()

        return json_result
