# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import psycopg2

from socorro.external import DatabaseError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.products import Products
from socorro.lib import external_common

logger = logging.getLogger("webapi")


class Releases(PostgreSQLBase):

    """
    Implement the /releases service with PostgreSQL.
    """

    def get_featured(self, **kwargs):
        """Return a list of featured versions for one, several or all products.
        """
        filters = [
            ("products", None, ["list", "str"]),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        sql = """
            SELECT product_name, version_string
            FROM product_info
            WHERE is_featured = true
        """
        sql_params = {}

        if params.products and params.products[0]:
            sql += " AND product_name IN %(product)s"
            sql_params['product'] = tuple(params.products)

        error_message = "Failed to retrieve featured versions from PostgreSQL"
        sql_results = self.query(sql, sql_params, error_message=error_message)

        hits = {}
        total = 0

        for row in sql_results:
            total += 1
            version = dict(zip(("product", "version"), row))
            if version["product"] not in hits:
                hits[version["product"]] = [version["version"]]
            else:
                hits[version["product"]].append(version["version"])

        return {
            "total": total,
            "hits": hits
        }

    def update_featured(self, **kwargs):
        """Update lists of featured versions. """
        products_list = Products(config=self.context).get()['products']
        releases = {}

        for p in kwargs:
            if p in products_list:
                if isinstance(kwargs[p], basestring):
                    # Assuming `,` for now, see
                    # https://bugzilla.mozilla.org/show_bug.cgi?id=787233
                    releases[p] = kwargs[p].split(',')
                else:
                    releases[p] = kwargs[p]

        if len(releases) == 0:
            return False

        sql = """/* socorro.external.postgresql.releases.update_featured */
            SELECT edit_featured_versions(%%s, %s)
        """
        error_message = "Failed updating featured versions in PostgreSQL"

        with self.get_connection() as connection:
            try:
                cursor = connection.cursor()

                for p in releases:
                    query = sql % ", ".join(
                        "%s" for i in xrange(len(releases[p]))
                    )
                    sql_params = [p] + releases[p]
                    # logger.debug(cursor.mogrify(query, sql_params))
                    cursor.execute(query, sql_params)

                connection.commit()
            except psycopg2.Error:
                connection.rollback()
                logger.error(error_message)
                raise DatabaseError(error_message)

        return True
