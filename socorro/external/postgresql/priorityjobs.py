# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import psycopg2

from socorro.external import MissingArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common

logger = logging.getLogger("webapi")


class Priorityjobs(PostgreSQLBase):
    """Implement the /priorityjobs service with PostgreSQL. """

    def post(self, *args, **kwargs):
        # because this implementation can accept both
        return self.get(*args, **kwargs)

    def get(self, **kwargs):
        """Return a job in the priority queue. """
        filters = [
            ("uuid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params.uuid:
            raise MissingArgumentError('uuid')

        sql = """
            /* socorro.external.postgresql.priorityjobs.Priorityjobs.get */
            SELECT uuid FROM priorityjobs WHERE uuid=%(uuid)s
        """

        error_message = "Failed to retrieve priorityjobs data from PostgreSQL"
        results = self.query(sql, params, error_message=error_message)

        jobs = []
        for row in results:
            job = dict(zip(("uuid",), row))
            jobs.append(job)

        return {
            "hits": jobs,
            "total": len(jobs)
        }

    def create(self, **kwargs):
        """Add a new job to the priority queue if not already in that queue.
        """
        filters = [
            ("uuid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params.uuid:
            raise MissingArgumentError('uuid')

        sql = """
            /* socorro.external.postgresql.priorityjobs.Priorityjobs.create */
            INSERT INTO priorityjobs (uuid) VALUES (%(uuid)s)
        """

        sql_exists = """
            /* socorro.external.postgresql.priorityjobs.Priorityjobs.create */
            SELECT 1 FROM priorityjobs WHERE uuid=%(uuid)s
        """

        connection = None
        try:
            connection = self.database.connection()
            cur = connection.cursor()

            # Verifying that the uuid is not already in the queue
            cur.execute(sql_exists, params)
            if cur.rowcount:
                logger.debug('The uuid %s is already in the priorityjobs '
                             'table' % params.uuid)
                return False

            logger.debug('Adding the uuid %s to the priorityjobs table' %
                         params.uuid)
            cur.execute(sql, params)
        except psycopg2.Error:
            logger.error("Failed inserting priorityjobs data into PostgreSQL",
                         exc_info=True)
            connection.rollback()
            return False
        else:
            connection.commit()
            return bool(cur.rowcount)
        finally:
            if connection:
                connection.close()

        return True
