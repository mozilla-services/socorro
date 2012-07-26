# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import psycopg2

from socorro.external.postgresql.base import add_param_to_dict, PostgreSQLBase
from socorro.lib import datetimeutil, external_common

import socorro.database.database as db

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
                   throttle::float
            FROM product_info WHERE
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

        sql_query = " ".join(
                    ("/* socorro.external.postgresql.Products.get_versions */",
                    sql_select, " OR ".join(sql_where)))

        json_result = {
            "total": 0,
            "hits": []
        }

        try:
            connection = self.database.connection()
            cur = connection.cursor()
            results = db.execute(cur, sql_query, sql_params)
        except psycopg2.Error:
            logger.error(
                    "Failed retrieving products_versions data from PostgreSQL",
                    exc_info=True)
        else:
            for product in results:
                row = dict(zip((
                            "product",
                            "version",
                            "start_date",
                            "end_date",
                            "is_featured",
                            "build_type",
                            "throttle"), product))
                json_result["hits"].append(row)
                row["start_date"] = datetimeutil.date_to_string(
                                                    row["start_date"])
                row["end_date"] = datetimeutil.date_to_string(
                                                    row["end_date"])
            json_result["total"] = len(json_result["hits"])

            return json_result
        finally:
            connection.close()

    def _get_products(self):
        """ Return a list of product names """

        sql_query = "SELECT * FROM products"

        json_result = {
            "total": 0,
            "hits": []
        }

        default_versions = self.get_default_version()["hits"]

        try:
            connection = self.database.connection()
            cur = connection.cursor()
            results = db.execute(cur, sql_query)
        except psycopg2.Error:
            logger.error("Failed to retrieve products list from PostgreSQL",
                         exc_info=True)
        else:
            for product in results:
                row = dict(zip((
                            "product_name",
                            "sort",
                            "rapid_release_version",
                            "release_name"), product))
                row["default_version"] = default_versions[row["product_name"]]
                json_result["hits"].append(row)
                json_result["total"] = len(json_result["hits"])

            return json_result
        finally:
            connection.close()

    def get_default_version(self, **kwargs):
        """Return the default version of one or several products. """
        filters = [
            ("products", None, ["list", "str"])
        ]
        params = external_common.parse_arguments(filters, kwargs)

        sql = """
            /* socorro.external.postgresql.products.Products.get_default_version */
            SELECT product_name, version_string
            FROM default_versions
        """

        if params.products and params.products[0] != "":
            params.products = tuple(params.products)
            sql = "%s WHERE product_name IN %%(products)s" % sql

        try:
            connection = self.database.connection()
            cursor = connection.cursor()
            cursor.execute(sql, params)
            results = cursor.fetchall()
        except psycopg2.Error:
            results = []
            logger.error("Failed to retrieve default versions from PostgreSQL",
                         exc_info=True)
        finally:
            connection.close()

        products = {}
        for row in results:
            product = dict(zip(("product", "version"), row))
            products[product["product"]] = product["version"]

        return {
            "hits": products
        }
