# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from pkg_resources import resource_string

from socorro.external.postgresql.base import PostgreSQLBase

logger = logging.getLogger("webapi")


def get_file(fn):
    """Retrieves the contents of the specified resource file

    Doing this as a separate function makes it easier to mock in the tests.

    :arg str fn: the file name to retrieve

    :returns: the contents as a string

    """
    return resource_string('socorro', fn)


class ServerStatus(PostgreSQLBase):
    """Implement the /server_status service with PostgreSQL. """

    def get(self, **kwargs):
        """Return the revisions of Socorro and Breakpad. """
        # Find the current database version
        sql = """
            /* socorro.external.postgresql.server_status.ServerStatus.get */
            SELECT
                version_num
            FROM alembic_version
        """

        error_message = "Failed to retrieve database version from PostgreSQL"
        results = self.query(sql, error_message=error_message)
        if results:
            schema_revision, = results[0]
        else:
            logger.warning("No version_num was found in table alembic_version")
            schema_revision = "Unknown"

        # Find the current breakpad and socorro revisions
        socorro_revision = get_file('socorro_revision.txt')
        breakpad_revision = get_file('breakpad_revision.txt')

        return {
            "socorro_revision": socorro_revision.strip(),
            "breakpad_revision": breakpad_revision.strip(),
            "schema_revision": schema_revision.strip(),
        }
