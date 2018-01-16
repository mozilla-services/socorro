# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.crash_data_base import CrashDataBase
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common, MissingArgumentError


class CrashData(CrashDataBase):
    """
    Implement the /crash_data service with PostgreSQL.
    """
    def get_storage(self):
        return self.config.database.crashstorage_class(self.config.database)


class RawCrash(PostgreSQLBase):
    """Implement RawCrash data service with PostgreSQL"""
    def get(self, **kwargs):
        filters = [
            ('uuid', None, str)
        ]
        params = external_common.parse_arguments(filters, kwargs, modern=True)
        if not params.uuid:
            raise MissingArgumentError('uuid')

        sql_query = """
            SELECT
                uuid
            FROM raw_crashes
            WHERE uuid=%(uuid)s
        """
        results = self.query(sql_query, params)
        hits = results.zipped()

        return {
            'hits': hits
        }


class ProcessedCrash(PostgreSQLBase):
    """Implement ProcessedCrash  data service with PostgreSQL"""
    def get(self, **kwargs):
        filters = [
            ('uuid', None, str)
        ]
        params = external_common.parse_arguments(filters, kwargs, modern=True)
        if not params.uuid:
            raise MissingArgumentError('uuid')

        sql_query = """
            SELECT
                uuid
            FROM processed_crashes
            WHERE uuid=%(uuid)s
        """
        results = self.query(sql_query, params)
        hits = results.zipped()

        return {
            'hits': hits
        }
