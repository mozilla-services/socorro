# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging
import psycopg2

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external import MissingOrBadArgumentError
from socorro.lib import datetimeutil, external_common

import socorro.database.database as db

logger = logging.getLogger("webapi")



class Job(PostgreSQLBase):
    """Implement the /job service with PostgreSQL. """

    def get(self, **kwargs):
        """Return a job in the job queue. """
        filters = [
            ("uuid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params.uuid:
            raise MissingOrBadArgumentError(
                        "Mandatory parameter 'uuid' is missing or empty")

        fields = [
            "id",
            "pathname",
            "uuid",
            "owner",
            "priority",
            "queueddatetime",
            "starteddatetime",
            "completeddatetime",
            "success",
            "message"
        ]
        sql = """
            /* socorro.external.postgresql.job.Job.get */
            SELECT %s FROM jobs WHERE uuid=%%(uuid)s
        """ % ", ".join(fields)

        json_result = {
            "total": 0,
            "hits": []
        }

        connection = None
        try:
            # Creating the connection to the DB
            connection = self.database.connection()
            cur = connection.cursor()
            results = db.execute(cur, sql, params)
        except psycopg2.Error:
            logger.error("Failed retrieving jobs data from PostgreSQL",
                         exc_info=True)
        else:
            for job in results:
                row = dict(zip(fields, job))

                # Make sure all dates are turned into strings
                for i in row:
                    if isinstance(row[i], datetime.datetime):
                        row[i] = datetimeutil.date_to_string(row[i])

                json_result["hits"].append(row)
            json_result["total"] = len(json_result["hits"])
        finally:
            if connection:
                connection.close()

        return json_result
