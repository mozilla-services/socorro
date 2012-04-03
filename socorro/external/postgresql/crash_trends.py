import logging
import psycopg2

from socorro.external.postgresql.base import PostgreSQLBase
import socorro.database.database as db
from socorro.lib import datetimeutil, external_common

logger = logging.getLogger("webapi")


class CrashTrends(PostgreSQLBase):
    def __init__(self, *args, **kwargs):
        super(CrashTrends, self).__init__(*args, **kwargs)
    
    def get(self, **kwargs):
        filters = [
            ("start_date", None, "datetime"),
            ("end_date", None, "datetime"),
            ("product", None, "str"),
            ("version", None, "str"),
            ]
    
        params = external_common.parse_arguments(filters, kwargs)
        results = [] # So we have something to return.

        query_string = """SELECT product_name, 
                    version_string, 
                    product_version_id, 
                    nightly_builds.build_date, 
                    days_out,
                    sum(report_count) as report_count 
                FROM nightly_builds 
                JOIN product_versions USING ( product_version_id ) 
                WHERE report_date <= %(end_date)s
                AND report_date >= %(start_date)s
                AND product_name = %(product)s
                AND version_string = %(version)s
                GROUP BY product_name, 
                         version_string, 
                         product_version_id, 
                         nightly_builds.build_date, 
                         days_out"""
  
        try:                 
            self.connection = self.database.connection()
            cursor = self.connection.cursor()                 
            sql_results = db.execute(cursor, query_string, params)
        except psycopg2.Error:
            logger.error("Failed retrieving crashtrends data from PostgreSQL",
                         exc_info=True)
        else:
            for trend in sql_results:
                row = dict(zip((
                              "product_name",
                              "version_string",
                              "product_version_id",
                              "build_date",
                              "days_out",
                              "report_count"), trend))
                row['build_date'] = datetimeutil.date_to_string(row['build_date'])
                results.append(row)
        finally:
            self.connection.close()
        
        return results