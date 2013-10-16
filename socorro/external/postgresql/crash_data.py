import json

from socorro.external import (
    MissingArgumentError,
    BadArgumentError,
    ResourceNotFound,
    DatabaseError
)
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common


class CrashData(PostgreSQLBase):
    """
    Implement the /crash_data service with PostgreSQL.
    """
    def get(self, **kwargs):
        """Return a single crash report from its UUID. """
        filters = [
            ("uuid", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        if params.uuid is None:
            raise MissingArgumentError("uuid")

        sql = """/* socorro.external.postgresql.crash_data.CrashData.get */
            SELECT raw_crash
            FROM raw_crashes
            WHERE
                uuid = UUID(%(uuid)s)
        """
        try:
            for result in self.query(sql, params):
                return json.loads(result[0])
        except DatabaseError:
            raise BadArgumentError(params.uuid)

        raise ResourceNotFound(params.uuid)
