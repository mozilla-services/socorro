# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import psycopg2

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common

import socorro.database.database as db

logger = logging.getLogger("webapi")


class MissingOrBadArgumentError(Exception):
    pass


class Bugs(PostgreSQLBase):
    """Implement the /bugs service with PostgreSQL. """

    def get(self, **kwargs):
        """Return a list of signature - bug id associations. """
        filters = [
            ("signature_ids", None, ["list", "int"]),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if not params.signature_ids:
            raise MissingOrBadArgumentError(
                        "Mandatory parameter 'signature_ids' is missing or empty")

        sql = """/* socorro.external.postgresql.bugs.Bugs.get */
            SELECT bug_associations.signature, bug_id
            FROM bug_associations
                join signatures
                on bug_associations.signature = signatures.signature
            WHERE signatures.signature_id IN %s
        """


        try:
            connection = self.database.connection()
            cur = connection.cursor()
            #logger.debug(cur.mogrify(sql, (tuple(params.signature_ids),)))
            results = db.execute_now(cur, sql, (tuple(params.signature_ids),))
        except psycopg2.Error:
            logger.error("Failed retrieving bug associations from PostgreSQL",
                         exc_info=True)
            raise
        finally:
            connection.close()

        result = {
            "total": 0,
            "hits": []
        }

        for crash in results:
            row = dict(zip(("signature", "id"), crash))
            result["hits"].append(row)
        result["total"] = len(result["hits"])

        return result
