import logging
import psycopg2

from socorro.external.postgresql.base import PostgreSQLBase, add_param_to_dict
from socorro.external.postgresql.products import Products
from socorro.lib import external_common

import socorro.database.database as db

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
            sql_where = []
            for i in xrange(len(params.products)):
                sql_where.append("%%(product%s)s" % i)

            sql = "%s AND product_name IN (%s)" % (sql, ", ".join(sql_where))
            sql_params = add_param_to_dict(sql_params, "product",
                                           params.products)

        connection = None
        try:
            connection = self.database.connection()
            cur = connection.cursor()

            sql_results = db.execute(cur, sql, sql_params)
        except psycopg2.Error:
            logger.error("Failed updating featured versions in PostgreSQL",
                         exc_info=True)
            raise
        else:
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
        finally:
            if connection:
                connection.close()

    def update_featured(self, **kwargs):
        """Update lists of featured versions. """
        products_dict = Products(config=self.context).get()
        products_list = [i["product_name"] for i in products_dict["hits"]]
        logger.debug(products_list)
        releases = {}

        for p in kwargs:
            if p in products_list:
                releases[p] = kwargs[p]

        if len(releases) == 0:
            return False

        sql = """/* socorro.external.postgresql.releases.update_featured */
            SELECT edit_featured_versions(%%s, %s)
        """

        connection = None
        try:
            connection = self.database.connection()
            cur = connection.cursor()

            for p in releases:
                query = sql % ", ".join("%s" for i in xrange(len(releases[p])))
                sql_params = [p] + releases[p]
                logger.debug(cur.mogrify(query, sql_params))
                cur.execute(query, sql_params)

            connection.commit()
        except psycopg2.Error:
            if connection:
                connection.rollback()
            logger.error("Failed updating featured versions in PostgreSQL",
                         exc_info=True)
            raise
        finally:
            if connection:
                connection.close()

        return True
