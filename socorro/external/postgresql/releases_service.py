# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.postgresql.service_base import (
    PostgreSQLWebServiceBase
)
from socorro.external.postgresql.dbapi2_util import (
    execute_no_results,
)
from socorro.lib import external_common


#==============================================================================
class Releases(PostgreSQLWebServiceBase):

    """
    Implement the /releases service with PostgreSQL.
    """

    uri = r'/releases/(featured)/(.*)'

    #--------------------------------------------------------------------------
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

    #--------------------------------------------------------------------------
    def post(self, **kwargs):
        """Update lists of featured versions. """

        products_service = self.config.services.Products.cls(
            config=self.config.services.Products
        )
        products_list = products_service.get()['products']
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

        def do_transaction(connection):
            for p in releases:
                query = sql % ", ".join(
                    "%s" for i in xrange(len(releases[p]))
                )
                sql_params = [p] + releases[p]
                execute_no_results(
                    connection,
                    query,
                    sql_params
                )
        self.transaction(do_transaction)
        return True
