from socorro.external.postgresql.base import PostgreSQLBase
import socorro.database.database as db
from socorro.lib import external_common

report_type_sql = {
    'uptime': {
        "first_col": 'uptime_string',
        "first_col_format": 'category',
        "extra_join": """ JOIN uptime_levels ON
                            reports_clean.uptime >= min_uptime AND
                            reports_clean.uptime < max_uptime""",
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


class SignatureSummary(PostgreSQLBase):
    def __init__(self, *args, **kwargs):
        super(SignatureSummary, self).__init__(*args, **kwargs)

    def get(self, **kwargs):
        filters = [
            ("report_type", None, "str"),
            ("signature", None, "str"),
            ("start_date", None, "datetime"),
            ("end_date", None, "datetime"),
            ("product", None, ["list", "str"]),
            ("versions", None, ["list", "str"]),
            ]

        params = external_common.parse_arguments(filters, kwargs)

        # Decode double-encoded slashes in signature
        if params["signature"] is not None:
            params["signature"] = params["signature"].replace("%2F", "/")

        if params['versions'] and params['report_type'] is not 'products':
            glue = ','
            version_search = ' AND reports_clean.product_version_id IN (%s)'
            version_search = version_search % glue.join(params['versions'])
        else:
            version_search = ''

        if params['product'] and params['report_type'] is not 'products':
            glue = ','
            product_list = ' AND product_name IN %s'
        else:
            product_list = ''

        query_params = report_type_sql.get(params['report_type'], {})
        if (params['report_type'] != 'products' and
                'first_col' not in query_params):
            raise Exception('Invalid report type')

        self.connection = self.database.connection()
        cursor = self.connection.cursor()

        if params['report_type'] == 'products':
            result_cols = ['product_name', 'version_string',
                            'report_count', 'percentage']
            query_string = """WITH counts AS (
                SELECT product_version_id, product_name, version_string,
                    count(*) AS report_count
                FROM reports_clean
                    JOIN product_versions USING (product_version_id)
                WHERE
                    signature_id = (SELECT signature_id FROM signatures
                     WHERE signature = %s)
                    AND date_processed >= %s
                    AND date_processed < %s
                GROUP BY product_version_id, product_name, version_string
            ),
            totals as (
                SELECT product_version_id, product_name, version_string,
                    report_count,
                    sum(report_count) OVER () as total_count
                FROM counts
            )
            SELECT product_name, version_string,
                report_count::INT,
                round((report_count * 100::numeric)/total_count,3)::TEXT
                as percentage
            FROM totals
            ORDER BY report_count DESC"""
            query_parameters = (params['signature'],
                                params['start_date'],
                                params['end_date'])
        else:
            result_cols = ['category', 'report_count', 'percentage']
            query_string = ["""WITH counts AS ( SELECT """]
            query_string.append(query_params['first_col'])
            query_string.append(""" as category, count(*) AS report_count
                FROM reports_clean
                    JOIN product_versions USING (product_version_id)
                    """)
            query_string.append(query_params.get('extra_join', ''))
            query_string.append("""
                WHERE
                    signature_id = (SELECT signature_id FROM signatures
                                    WHERE signature = %s)
                    AND date_processed >= %s
                    AND date_processed < %s
                    """)
            query_string.append(product_list)
            query_string.append(version_search)
            query_string.append(""" GROUP BY """)
            query_string.append(query_params['first_col'])
            query_string.append("""),
            totals as (
                SELECT category, report_count,
                    sum(report_count) OVER () as total_count
                FROM counts
            )
            SELECT  """)
            query_string.append(query_params['first_col_format'])
            query_string.append(""",
                report_count::INT,
                round((report_count::numeric)/total_count,5)::TEXT
                    as percentage
            FROM totals
            ORDER BY report_count DESC""")
            query_string = " ".join(query_string)

            query_parameters = [params['signature'],
                                params['start_date'],
                                params['end_date'],
                                ]

            if(product_list):
                # This MUST be a tuple otherwise it gets cast to an array.
                query_parameters.append(tuple(params['product']))

            query_parameters = tuple(query_parameters)
        sql_results = db.execute(cursor, query_string, query_parameters)
        results = []
        for row in sql_results:
            newrow = dict(zip(result_cols, row))
            results.append(newrow)

        return results
