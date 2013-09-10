# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external.postgresql.util import Util
import socorro.database.database as db
from socorro.lib import external_common
from socorro.external import MissingOrBadArgumentError


logger = logging.getLogger("webapi")

report_type_sql = {
    'uptime': {
        "first_col": 'uptime_string',
        "first_col_format": 'category',
        "extra_join": ''' JOIN uptime_levels ON
            reports_clean.uptime >= min_uptime AND
            reports_clean.uptime < max_uptime ''',
    },

    'os': {
        'first_col': 'os_version_string',
        'first_col_format': 'category',
        'extra_join': ' JOIN os_versions USING ( os_version_id ) ',
    },

    'process_type': {
        'first_col': 'process_type',
        'first_col_format': 'category',
    },

    'architecture': {
        'first_col': 'architecture',
        'first_col_format': 'category',
    },

    'flash_version': {
        'first_col': 'flash_version',
        'first_col_format': '''CASE WHEN category = ''
            THEN 'Unknown/No Flash' ELSE category END''',
        'extra_join': ''' LEFT OUTER JOIN flash_versions
            USING (flash_version_id) ''',
    },
}


report_type_columns = {
    'uptime': 'uptime_string',
    'os': 'os_version_string',
    'process_type': 'process_type',
    'architecture': 'architecture',
    'flash_version': 'flash_version'
}


class SignatureSummary(PostgreSQLBase):

    def get(self, **kwargs):
        filters = [
            ("report_type", None, "str"),
            ("signature", None, "str"),
            ("start_date", None, "datetime"),
            ("end_date", None, "datetime"),
            ("versions", None, ["list", "str"]),
        ]

        params = external_common.parse_arguments(filters, kwargs)

        products = []
        versions = []

        # Get information about the versions
        util_service = Util(config=self.context)
        versions_info = util_service.versions_info(**params)
        if versions_info:
            for i, elem in enumerate(versions_info):
                products.append(versions_info[elem]["product_name"])
                versions.append(str(versions_info[elem]["version_string"]))

        # This MUST be a tuple otherwise it gets cast to an array
        params['product'] = tuple(products)
        params['version'] = tuple(versions)

        if params['product'] and params['report_type'] is not 'products':
            product_list = ' AND product_name IN %s '
        else:
            product_list = ''

        if params['version'] and params['report_type'] is not 'products':
            version_list = ' AND version_string IN %s '
        else:
            version_list = ''

        query_params = report_type_sql.get(params['report_type'], {})
        if (params['report_type'] not in
            ('products', 'distinct_install', 'exploitability', 'devices')
            and 'first_col' not in query_params):
            raise MissingOrBadArgumentError('Invalid report type')

        self.connection = self.database.connection()
        cursor = self.connection.cursor()

        if params['report_type'] == 'products':
            result_cols = ['product_name',
                           'version_string',
                           'report_count',
                           'percentage']
            query_string = """
            WITH crashes as (
                SELECT
                    product_name as category
                    , version_string
                    , SUM(report_count) as report_count
                FROM signature_summary_products
                    JOIN signatures USING (signature_id)
                WHERE signatures.signature = %s
                    AND report_date >= %s
                    AND report_date < %s
                GROUP BY product_name, version_string
            ),
            totals as (
                SELECT
                    category
                    , version_string
                    , report_count
                    , SUM(report_count) OVER () as total_count
                FROM crashes
            )
            SELECT category
                , version_string
                , report_count
                , round((report_count * 100::numeric)/total_count,3)::TEXT
                as percentage
            FROM totals
            ORDER BY report_count DESC"""
            query_parameters = (params['signature'],
                                params['start_date'],
                                params['end_date'])

        elif params['report_type'] == 'distinct_install':
            result_cols = ['product_name',
                           'version_string',
                           'crashes',
                           'installations']
            query_string = """
                SELECT product_name
                    , version_string
                    , crash_count AS crashes
                    , install_count AS installations
                FROM signature_summary_installations
                    JOIN signatures USING (signature_id)
                WHERE
                    signatures.signature = %s
                    AND report_date >= %s
                    AND report_date < %s
            """
            query_string += product_list
            query_string += version_list
            query_string += """
                ORDER BY crashes DESC
            """
            query_parameters = (
                params['signature'],
                params['start_date'],
                params['end_date']
            )

            if product_list:
                query_parameters += (params['product'],)
            if version_list:
                query_parameters += (params['version'],)

        elif params['report_type'] == 'exploitability':
            # Note, even if params['product'] is something we can't use
            # that in this query
            result_cols = [
                'report_date',
                'null_count',
                'none_count',
                'low_count',
                'medium_count',
                'high_count',
            ]
            query_string = """
                SELECT
                    cast(report_date as TEXT),
                    null_count,
                    none_count,
                    low_count,
                    medium_count,
                    high_count
                FROM exploitability_reports
                    JOIN signatures USING (signature_id)
                WHERE
                    signatures.signature = %s
                    AND report_date >= %s
                    AND report_date < %s
            """
            query_string += """
                ORDER BY report_date DESC
            """
            query_parameters = (
                params['signature'],
                params['start_date'],
                params['end_date'],
            )
        elif params['report_type'] == 'devices':
            result_cols = [
                'cpu_abi',
                'manufacturer',
                'model',
                'version',
                'report_count',
                'percentage',
            ]
            query_string = """
                WITH crashes as (
                    SELECT
                        android_devices.android_cpu_abi as cpu_abi,
                        android_devices.android_manufacturer as manufacturer,
                        android_devices.android_model as model,
                        android_devices.android_version as version,
                        SUM(report_count) as report_count
                    FROM signature_summary_device
                        JOIN signatures USING (signature_id)
                        JOIN android_devices ON
                            signature_summary_device.android_device_id =
                            android_devices.android_device_id
                    WHERE signatures.signature = %s
                        AND report_date >= %s
                        AND report_date < %s
                    GROUP BY
                        android_devices.android_device_id
                ),
                totals as (
                    SELECT
                        cpu_abi,
                        manufacturer,
                        model,
                        version,
                        report_count,
                        SUM(report_count) OVER () as total_count
                    FROM crashes
                )
                SELECT
                    cpu_abi,
                    manufacturer,
                    model,
                    version,
                    report_count,
                    round((report_count * 100::numeric)/total_count,3)::TEXT
                        as percentage
                FROM totals
                ORDER BY report_count DESC
            """
            query_parameters = (
                params['signature'],
                params['start_date'],
                params['end_date'],
            )
        elif params['report_type'] in report_type_columns:
            result_cols = ['category', 'report_count', 'percentage']
            query_string = """
                WITH crashes AS (
                    SELECT """
            query_string += report_type_columns[params['report_type']]
            query_string += """ AS category
                        , sum(report_count) AS report_count
                    FROM signature_summary_"""
            query_string += params['report_type']
            query_string += """
                        JOIN signatures USING (signature_id)
                    WHERE
                        signatures.signature = %s
                        AND report_date >= %s
                        AND report_date < %s
            """
            query_string += product_list
            query_string += version_list
            query_string += """
                    GROUP BY category
                ),
                totals AS (
                    SELECT
                        category
                        , report_count
                        , sum(report_count) OVER () as total_count
                    FROM crashes
                )
                SELECT category
                    , report_count
                    , round((report_count * 100::numeric)/total_count,3)::TEXT
                as percentage
                FROM totals
                ORDER BY report_count DESC
            """
            query_parameters = (
                params['signature'],
                params['start_date'],
                params['end_date']
            )

            if product_list:
                query_parameters += (params['product'],)
            if version_list:
                query_parameters += (params['version'],)

        sql_results = db.execute(cursor, query_string, query_parameters)
        results = []
        for row in sql_results:
            newrow = dict(zip(result_cols, row))
            results.append(newrow)

        # Closing the connection here because we're not using
        # the parent class' query()
        self.connection.close()
        return results
