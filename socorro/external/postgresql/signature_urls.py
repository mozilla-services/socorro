# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import psycopg2

from socorro.external.postgresql.base import add_param_to_dict, PostgreSQLBase
from socorro.lib import external_common

import socorro.database.database as db

logger = logging.getLogger("webapi")


class MissingOrBadArgumentException(Exception):
    pass


class SignatureURLs(PostgreSQLBase):

    def get(self, **kwargs):
        """ Return urls for signature """
        filters = [
            ("signature", None, "str"),
            ("start_date", None, "datetime"),
            ("end_date", None, "datetime"),
            ("products", None, ["list", "str"]),
            ("versions", None, ["list", "str"]),
        ]

        params = external_common.parse_arguments(filters, kwargs)

        #Because no parameters are optional, we need to loop through
        #all parameters to ensure each has been set and is not None
        missingParams = []
        for param in params:
            if not params[param]:
                missingParams.append(param)

        if len(missingParams) > 0:
            raise MissingOrBadArgumentException(
                    "Mandatory parameter(s) '%s' is missing or empty"
                        % ", ".join(missingParams))

        all_products_versions_sql = """
        /* socorro.external.postgresql.signature_urls.SignatureURLs.get */
            SELECT url, count(*) as crash_count FROM reports_clean
            JOIN reports_user_info USING ( UUID )
            JOIN signatures USING ( signature_id )
            WHERE reports_clean.date_processed
                BETWEEN %(start_date)s AND %(end_date)s
            AND reports_user_info.date_processed
                BETWEEN %(start_date)s AND %(end_date)s
            AND signature = %(signature)s
            AND url <> ''
        """

        sql = """
        /* socorro.external.postgresql.signature_urls.SignatureURLs.get */
            SELECT url, count(*) as crash_count FROM reports_clean
            JOIN reports_user_info USING ( UUID )
            JOIN signatures USING ( signature_id )
            JOIN product_versions USING ( product_version_id )
            WHERE reports_clean.date_processed
                BETWEEN %(start_date)s AND %(end_date)s
            AND reports_user_info.date_processed
                BETWEEN %(start_date)s AND %(end_date)s
            AND signature = %(signature)s
            AND url <> ''
            AND (
        """

        sql_group_order = """ GROUP BY url
            ORDER BY crash_count DESC LIMIT 100"""
        sql_params = {
            "start_date": params.start_date,
            "end_date": params.end_date,
            "signature": params.signature
        }

        # if this query is for all products the 'ALL' keyword will be
        # the only item in the products list and this will then also
        # be for all versions.
        if 'ALL' in params['products']:
            sql_query = " ".join((all_products_versions_sql, sql_group_order))
        # if this query is for all versions the 'ALL' keyword will be
        # the only item in the versions list.
        elif 'ALL' in params['versions']:
            sql_products = " product_name IN ('%s') )" % (
                    "', '".join([product for product in params.products]))

            sql_date_range_limit = """AND '%s' BETWEEN
                product_versions.build_date
                    AND product_versions.sunset_date""" % params.end_date

            sql_query = " ".join((sql, sql_products,
                                  sql_date_range_limit, sql_group_order))
        else:
            products = []
            (params["products_versions"],
             products) = self.parse_versions(params["versions"], [])

            versions_list = []
            products_list = []
            for x in range(0, len(params["products_versions"]), 2):
                products_list.append(params["products_versions"][x])
                versions_list.append(params["products_versions"][x + 1])

            product_version_list = []
            for prod in params["products"]:
                versions = []
                [versions.append(versions_list[i])
                 for i, x in enumerate(products_list)
                 if x == prod]
                product_version_list.append(tuple(versions))

            sql_product_version_ids = [
                """( product_name = %%(product%s)s
                    AND version_string IN %%(version%s)s ) """
                        % (x, x) for x in range(len(product_version_list))]

            sql_params = add_param_to_dict(sql_params, "version",
                                       product_version_list)

            sql_params = add_param_to_dict(sql_params, "product",
                                       params.products)

            sql_query = " ".join((sql, " OR ".join(sql_product_version_ids),
                              " ) " + sql_group_order))

        json_result = {
            "total": 0,
            "hits": []
        }

        connection = None
        try:
            connection = self.database.connection()
            cur = connection.cursor()
            results = db.execute(cur, sql_query, sql_params)
        except psycopg2.Error:
            logger.error(
                "Failed retrieving urls for signature data from PostgreSQL",
                    exc_info=True)
        else:
            for url in results:
                row = dict(zip((
                            "url",
                            "crash_count"), url))
                json_result["hits"].append(row)

            json_result["total"] = len(json_result["hits"])

            return json_result
        finally:
            if connection:
                connection.close()
