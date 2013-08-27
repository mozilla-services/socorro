# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.postgresql.base import PostgreSQLBase


class SchemaRevision(PostgreSQLBase):
    """Implement the /schema_revision service with PostgreSQL. """

    def get(self, **kwargs):
        """Return the current schema revision of the Socorro Database. """
        sql = """
            /* socorro.external.postgresql.server_status.ServerStatus.get */
            SELECT
                version_num
            FROM alembic_version
        """

        error_message = "Failed to retrieve server status data from PostgreSQL"
        results = self.query(sql, error_message=error_message)

        version_num, = results[0]

        return {
            "schema_revision": version_num
        }
