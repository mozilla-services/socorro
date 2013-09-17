# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external.postgresql.base import PostgreSQLBase

import socorro.lib.external_common as external_common

logger = logging.getLogger("webapi")


class Util(PostgreSQLBase):

    """
    Implement /util services with PostgreSQL.
    """

    def versions_info(self, **kwargs):
        """
        Return information about versions of a product.

        See http://socorro.readthedocs.org/en/latest/middleware.html

        Keyword arguments:
        versions - List of products and versions.

        Return:
        None if versions is null or empty ;
        Otherwise a dictionary of data about a version, i.e.:
        {
            "product_name:version_string": {
                "product_version_id": integer,
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

        # Check to see whether or not the item is a rapid beta.
        where = []
        args = {}
        for i in range(0, len(versions_list), 2):
            where.append(str(i).join(("product_name = %(product",
                                      ")s AND version_string = %(version",
                                      ")s AND is_rapid_beta = TRUE")))
            args['product%s' % i] = versions_list[i]
            args['version%s' % i] = versions_list[i + 1]

        rapid_beta_sql = """SELECT product_version_id FROM product_versions
            WHERE %s""" % " OR ".join(where)
        rapid_results = self.query(rapid_beta_sql, args, error_message="")

        if(rapid_results):
            rapid_betas = []
            for row in rapid_results:
                rapid_betas.append(dict(zip(('rapid_beta_id',), row)))
            beta_id_list = []
            for beta in rapid_betas:
                beta_id_list.append(str(beta['rapid_beta_id']))

            rapid_beta_sql = """SELECT product_name, version_string FROM
                product_versions WHERE rapid_beta_id IN (%s)
                """ % ",".join(beta_id_list)
            full_version_list = self.query(rapid_beta_sql)

            for row in full_version_list:
                versions_list.append(row[0])
                versions_list.append(row[1])

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
        SELECT pv.product_version_id, pi.version_string, pi.product_name,
               which_table, pv.release_version, pv.build_type, pvb.build_id
        FROM product_info pi
            LEFT JOIN product_versions pv ON
                (pv.product_version_id = pi.product_version_id)
            JOIN product_version_builds pvb ON
                (pv.product_version_id = pvb.product_version_id)
        WHERE %s
        ORDER BY pv.version_sort
        """ % " OR ".join(where)

        error_message = "Failed to retrieve versions data from PostgreSQL"
        results = self.query(sql, params, error_message=error_message)

        res = {}
        for row in results:
            version = dict(zip((
                "product_version_id",
                "version_string",
                "product_name",
                "which_table",
                "major_version",
                "release_channel",
                "build_id"), row))

            key = ":".join((version["product_name"],
                            version["version_string"]))

            if key in res:
                # That key already exists, just add it the new buildid
                res[key]["build_id"].append(int(version["build_id"]))
            else:
                if version["which_table"] == "old":
                    version["release_channel"] = version["build_id"] = None
                del version["which_table"]

                if version["build_id"]:
                    version["build_id"] = [int(version["build_id"])]

                res[key] = version

        return res
