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
        (versions_list, products_list) = self.parse_versions(
            params["versions"],
            products_list
        )

        if not versions_list:
            return None

        versions = []
        products = []
        for x in xrange(0, len(versions_list), 2):
            products.append(versions_list[x])
            versions.append(versions_list[x + 1])

        params = {}
        params = self.dispatch_params(params, "product", products)
        params = self.dispatch_params(params, "version", versions)

        where = []
        for i in range(len(products)):
            where.append("""
                (
                    i1.product_name = %%(product%(i)s)s
                    AND i1.version_string = %%(version%(i)s)s
                    AND i1.version_string = i2.version_string
                ) OR (
                    i1.rapid_beta_id = i2.product_version_id
                    AND i2.product_name = %%(product%(i)s)s
                    AND i2.version_string = %%(version%(i)s)s
                    AND i2.is_rapid_beta IS TRUE
                )
            """ % {'i': i})

        sql = """
            /* socorro.external.postgresql.util.Util.versions_info */
            WITH infos AS (
                SELECT
                    pv.product_version_id,
                    pi.version_string,
                    pi.product_name,
                    which_table,
                    pv.release_version,
                    pv.build_type,
                    pvb.build_id,
                    pv.is_rapid_beta,
                    pv.rapid_beta_id,
                    pv.version_sort
                FROM product_info pi
                    LEFT JOIN product_versions pv ON
                        (pv.product_version_id = pi.product_version_id)
                    LEFT JOIN product_version_builds pvb ON
                        (pv.product_version_id = pvb.product_version_id)
            )
            SELECT DISTINCT
                i1.product_version_id,
                i1.product_name,
                i1.version_string,
                i1.which_table,
                i1.release_version,
                i1.build_type,
                i1.build_id,
                i1.is_rapid_beta,
                i2.is_rapid_beta AS is_from_rapid_beta,
                (i2.product_name || ':' || i2.version_string)
                    AS from_beta_version,
                i1.version_sort
            FROM infos i1 LEFT JOIN infos i2 ON (
                i1.product_name = i2.product_name
                AND i1.release_version = i2.release_version
                AND i1.build_type = i2.build_type
            )
            WHERE %s
            ORDER BY i1.version_sort
        """ % " OR ".join(where)

        error_message = "Failed to retrieve versions data from PostgreSQL"
        results = self.query(sql, params, error_message=error_message)

        res = {}
        for row in results:
            version = dict(zip((
                "product_version_id",
                "product_name",
                "version_string",
                "which_table",
                "major_version",
                "release_channel",
                "build_id",
                "is_rapid_beta",
                "is_from_rapid_beta",
                "from_beta_version",
                "version_sort",
            ), row))

            key = ":".join((
                version["product_name"],
                version["version_string"]
            ))

            del version["version_sort"]  # no need to send this back

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
