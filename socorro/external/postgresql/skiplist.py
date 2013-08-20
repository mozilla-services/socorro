# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import psycopg2

from socorro.external import DatabaseError, MissingOrBadArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common

logger = logging.getLogger("webapi")


class SkipList(PostgreSQLBase):

    filters = [
        ("category", None, ["str"]),
        ("rule", None, ["str"]),
    ]

    def get(self, **kwargs):
        params = external_common.parse_arguments(self.filters, kwargs)
        sql_params = []
        sql = """
            /* socorro.external.postgresql.skiplist.SkipList.get */
            SELECT category,
                   rule
            FROM skiplist
            WHERE 1=1
        """
        if params.category:
            sql += 'AND category=%s'
            sql_params.append(params.category)
        if params.rule:
            sql += 'AND rule=%s'
            sql_params.append(params.rule)
        sql += """
            ORDER BY category ASC, rule ASC
        """

        error_message = "Failed to retrieve skip list data from PostgreSQL"
        sql_results = self.query(sql, sql_params, error_message=error_message)

        results = [dict(zip(("category", "rule"), x)) for x in sql_results]

        return {'hits': results, 'total': len(results)}

    def post(self, **kwargs):
        params = external_common.parse_arguments(self.filters, kwargs)
        if not params.category:
            raise MissingOrBadArgumentError(
                "Mandatory parameter 'category' is missing or empty"
            )
        if not params.rule:
            raise MissingOrBadArgumentError(
                "Mandatory parameter 'rule' is missing or empty"
            )

        sql = """
            /* socorro.external.postgresql.skiplist.SkipList.post */
            INSERT INTO skiplist (category, rule)
            VALUES (%s, %s);
        """

        sql_params = [params.category, params.rule]
        try:
            connection = self.database.connection()
            cur = connection.cursor()
            cur.execute(sql, sql_params)
            connection.commit()
        except psycopg2.Error:
            connection.rollback()
            error_message = "Failed updating skip list in PostgreSQL"
            logger.error(error_message)
            raise DatabaseError(error_message)
        finally:
            connection.close()

        return True

    def delete(self, **kwargs):
        params = external_common.parse_arguments(self.filters, kwargs)
        if not params.category:
            raise MissingOrBadArgumentError(
                "Mandatory parameter 'category' is missing or empty"
            )
        if not params.rule:
            raise MissingOrBadArgumentError(
                "Mandatory parameter 'rule' is missing or empty"
            )

        sql_params = [params.category, params.rule]
        count_sql = """
            /* socorro.external.postgresql.skiplist.SkipList.delete */
            SELECT COUNT(*) FROM skiplist
            WHERE category=%s AND rule=%s
        """
        sql = """
            /* socorro.external.postgresql.skiplist.SkipList.delete */
            DELETE FROM skiplist
            WHERE category=%s AND rule=%s
        """

        connection = self.database.connection()
        try:
            cur = connection.cursor()
            cur.execute(count_sql, sql_params)
            count, = cur.fetchone()
            if not count:
                return False
            cur.execute(sql, sql_params)
            connection.commit()
        except psycopg2.Error:
            connection.rollback()
            error_message = "Failed delete skip list in PostgreSQL"
            logger.error(error_message)
            raise DatabaseError(error_message)
        finally:
            connection.close()

        return True
