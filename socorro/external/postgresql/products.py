# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external.postgresql.base import add_param_to_dict, PostgreSQLBase
from socorro.lib import datetimeutil, external_common

logger = logging.getLogger("webapi")


class Products(PostgreSQLBase):

    def get(self, **kwargs):
        """ Return product information, or version information for one
         or more product:version combinations """
        filters = [
            ("versions", None, ["list", "str"])
        ]

        params = external_common.parse_arguments(filters, kwargs)

        if not params.versions or params.versions[0] == '':
            return self._get_products()
        else:
            return self._get_versions(params)

    def _get_versions(self, params):
        """ Return product information for one or more product:version
        combinations """
        products = []
        (params["products_versions"],
         products) = self.parse_versions(params["versions"], [])

        sql_select = """
            SELECT product_name as product,
                   version_string as version,
                   start_date,
                   end_date,
                   is_featured,
                   build_type,
                   throttle::float,
                   has_builds
            FROM product_info
        """

        sql_where = []
        versions_list = []
        products_list = []
        for x in range(0, len(params["products_versions"]), 2):
            products_list.append(params["products_versions"][x])
            versions_list.append(params["products_versions"][x + 1])

        sql_where = ["(product_name = %(product" + str(x) +
                     ")s AND version_string = %(version" + str(x) + ")s)"
                                  for x in range(len(products_list))]

        sql_params = {}
        sql_params = add_param_to_dict(sql_params, "product", products_list)
        sql_params = add_param_to_dict(sql_params, "version", versions_list)

        if len(sql_where) > 0:
            sql_query = " WHERE ".join((sql_select, " OR ".join(sql_where)))
        else:
            sql_query = sql_select

        sql_query = """
            /* socorro.external.postgresql.Products.get_versions */
            %s
        """ % sql_query

        error_message = "Failed to retrieve products versions from PostgreSQL"
        results = self.query(sql_query, sql_params,
                             error_message=error_message)

        products = []
        for row in results:
            product = dict(zip((
                "product",
                "version",
                "start_date",
                "end_date",
                "is_featured",
                "build_type",
                "throttle",
                "has_builds"
            ), row))
            product["start_date"] = datetimeutil.date_to_string(
                                                        product["start_date"])
            product["end_date"] = datetimeutil.date_to_string(
                                                        product["end_date"])
            products.append(product)

        return {
            "hits": products,
            "total": len(products)
        }

    def _get_products(self):
        """ Return a list of products and their default versions. """
        sql_query = """
            /* socorro.external.postgresql.products.Products._get_products */
            SELECT *
            FROM products
            ORDER BY sort
        """

        default_versions = self.get_default_version()["hits"]

        error_message = "Failed to retrieve products list from PostgreSQL"
        results = self.query(sql_query, error_message=error_message)

        products = []
        for row in results:
            product = dict(zip((
                "product_name",
                "sort",
                "rapid_release_version",
                "release_name"
            ), row))
            product["default_version"] = default_versions[
                                                    product["product_name"]]
            products.append(product)

        return {
            "hits": products,
            "total": len(products)
        }

    def get_default_version(self, **kwargs):
        """Return the default version of one or several products. """
        filters = [
            ("products", None, ["list", "str"])
        ]
        params = external_common.parse_arguments(filters, kwargs)

        sql = """
            /* socorro.external.postgresql.products.get_default_version */
            SELECT product_name, version_string
            FROM default_versions
        """

        if params.products and params.products[0] != "":
            params.products = tuple(params.products)
            sql = "%s WHERE product_name IN %%(products)s" % sql

        error_message = "Failed to retrieve default versions from PostgreSQL"
        results = self.query(sql, params, error_message=error_message)

        products = {}
        for row in results:
            product = dict(zip(("product", "version"), row))
            products[product["product"]] = product["version"]

        return {
            "hits": products
        }
