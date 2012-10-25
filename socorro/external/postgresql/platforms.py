# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external import MissingOrBadArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import datetimeutil, external_common

logger = logging.getLogger("webapi")


class Platforms(PostgreSQLBase):
    """Implement the /platforms service with PostgreSQL. """

    def get(self, **kwargs):
        """Return data about all platforms. """
        sql = """/* socorro.external.postgresql.platforms.Platforms.get */
            SELECT *
            FROM os_names
        """

        error_message = "Failed to retrieve platforms data from PostgreSQL"
        results = self.query(sql, error_message=error_message)

        platforms = [dict(zip(("name", "code"), p)) for p in results]

        return {
            "hits": platforms,
            "total": len(platforms)
        }
