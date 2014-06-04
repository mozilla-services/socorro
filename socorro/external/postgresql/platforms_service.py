# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external.postgresql.service_base import (
    PostgreSQLWebServiceBase
)


#==============================================================================
class Platforms(PostgreSQLWebServiceBase):
    """Implement the /platforms service with PostgreSQL. """

    uri = r'/platforms/(.*)'

    #--------------------------------------------------------------------------
    def get(self, **kwargs):
        """Return data about all platforms. """
        sql = \
        """/* socorro.external.postgresql.platforms_service.Platforms.get */
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
