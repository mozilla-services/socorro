import logging

from socorro.external.postgresql.base import PostgreSQLBase

import socorro.database.database as db
import socorro.lib.external_common as external_common
import socorro.lib.util as util

logger = logging.getLogger("webapi")


class Util(PostgreSQLBase):

    """
    Implement /util services with PostgreSQL.
    """

    def __init__(self, *args, **kwargs):
        super(Util, self).__init__(*args, **kwargs)

    def versions_info(self, **kwargs):
        """
        Return information about versions of a product.

        See http://socorro.readthedocs.org/en/latest/middleware.html#versions-info

        Keyword arguments:
        versions - List of products and versions.

        Return:
        None if versions is null or empty ;
        Otherwise a dictionary of data about a version, i.e.:
        {
            "product_name:version_string": {
                "version_string": "string",
                "product_name": "string",
                "major_version": "string" or None,
                "release_channel": "string" or None,
                "build_id": [list, of, decimals] or None
            }
        }

        """
        # Parse arguments
        filters = [
            ("versions", None, ["list", "str"])
        ]
        params = external_common.parse_arguments(filters, kwargs)

        if "versions" not in params or not params["versions"]:
            return None

        products_list = []
        (versions_list, products_list) = Util.parse_versions(
                                                            params["versions"],
                                                            products_list)

        if not versions_list:
            return None

        versions = []
        products = []
        for x in xrange(0, len(versions_list), 2):
            products.append(versions_list[x])
            versions.append(versions_list[x + 1])

        params = {}
        params = Util.dispatch_params(params, "product", products)
        params = Util.dispatch_params(params, "version", versions)

        where = []
        for i in range(len(products)):
            where.append(str(i).join(("(pi.product_name = %(product",
                                      ")s AND pi.version_string = %(version",
                                      ")s)")))

        sql = """/* socorro.external.postgresql.util.Util.versions_info */
        SELECT pi.version_string, pi.product_name, which_table,
               pv.release_version, pv.build_type, pvb.build_id
        FROM product_info pi
            LEFT JOIN product_versions pv ON
                (pv.product_version_id = pi.product_version_id)
            JOIN product_version_builds pvb ON
                (pv.product_version_id = pvb.product_version_id)
        WHERE %s
        """ % " OR ".join(where)

        # Creating the connection to the DB
        self.connection = self.database.connection()
        cur = self.connection.cursor()

        try:
            results = db.execute(cur, sql, params)
        except Exception:
            results = []
            util.reportExceptionAndContinue(logger)

        res = {}
        for line in results:
            row = dict(zip(("version_string", "product_name", "which_table",
                            "major_version", "release_channel", "build_id"),
                           line))

            key = ":".join((row["product_name"], row["version_string"]))

            if key in res:
                # That key already exists, just add it the new buildid
                res[key]["build_id"].append(int(row["build_id"]))
            else:
                if row["which_table"] == "old":
                    row["release_channel"] = row["build_id"] = None
                del row["which_table"]

                if row["build_id"]:
                    row["build_id"] = [int(row["build_id"])]

                res[key] = row

        return res
