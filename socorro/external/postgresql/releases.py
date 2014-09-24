# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import psycopg2

from socorro.external import DatabaseError, MissingArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.products import Products
from socorro.lib import external_common
from .dbapi2_util import execute_no_results, single_row_sql

logger = logging.getLogger("webapi")


class Releases(PostgreSQLBase):

    """
    Implement the /releases service with PostgreSQL.
    """

    def get_channels(self, **kwargs):
        """Return a list of release channels for one, several or all products.
        """
        filters = [
            ("products", None, ["list", "str"]),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        sql = """
            SELECT build_type, product_name
            FROM product_info
        """
        sql_params = {}

        if params.products and params.products[0]:
            sql += " WHERE product_name IN %(products)s"
            sql_params['products'] = tuple(params.products)

        error_message = "Failed to retrieve release channels from PostgreSQL"
        sql_results = self.query(sql, sql_params, error_message=error_message)

        channels = {}
        for row in sql_results:
            res = dict(zip(("channel", "product"), row))
            if res["product"] not in channels:
                channels[res["product"]] = [res["channel"]]
            else:
                channels[res["product"]].append(res["channel"])

        return channels

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

    def create_release(self, **kwargs):
        filters = [
            ('product', None, 'str'),
            ('version', None, 'str'),
            ('update_channel', None, 'str'),
            ('build_id', None, 'str'),
            ('platform', None, 'str'),
            ('beta_number', None, 'int'),
            ('release_channel', None, 'str'),
            ('throttle', None, 'int'),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        # all fields are mandatory
        for key in [x[0] for x in filters if x[1] is None]:
            if key == 'beta_number':
                # exception because this can either be a non-zero integer
                # or a None
                if params.get(key) is not None:
                    if not params.get(key):
                        raise MissingArgumentError(key)

            elif not params.get(key) and params.get(key) != 0:
                raise MissingArgumentError(key)

        with self.get_connection() as connection:
            try:
                single_row_sql(
                    connection,
                    # product, version, update_channel, build_id, platform,
                    # beta_number
                    "SELECT add_new_release(%s, %s, %s, %s, %s, %s)",
                    (
                        params['product'],
                        params['version'],
                        params['update_channel'],
                        params['build_id'],
                        params['platform'],
                        params['beta_number']
                    ),
                )
                execute_no_results(
                    connection,
                    """
                        INSERT INTO product_release_channels
                        (product_name, release_channel, throttle)
                        SELECT %s, %s, %s
                        WHERE NOT EXISTS (
                            SELECT product_name, release_channel
                            FROM product_release_channels
                            WHERE
                            product_name = %s
                            AND
                            release_channel = %s
                        )
                    """,
                    (
                        params['product'],
                        params['release_channel'],
                        params['throttle'],
                        params['product'],
                        params['release_channel'],
                    ),
                )
                single_row_sql(
                    connection,
                    "SELECT update_product_versions()"
                )
            except psycopg2.Error:
                connection.rollback()
                raise
            else:
                connection.commit()

        return True
