# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external import MissingArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common

logger = logging.getLogger("webapi")


class Bugs(PostgreSQLBase):
    """Implement the /bugs service with PostgreSQL. """
    filters = [
        ("signatures", None, ["list", "str"]),
    ]

    def get(self, **kwargs):
        import warnings
        warnings.warn("You should use the POST method to access bugs")
        return self.post(**kwargs)

    def post(self, **kwargs):
        """Return a list of signature - bug id associations. """
        params = external_common.parse_arguments(self.filters, kwargs)
        if not params.signatures:
            raise MissingArgumentError('signatures')

        # Preparing variables for the SQL query
        signatures = []
        sql_params = {}
        for i, elem in enumerate(params.signatures):
            signatures.append("%%(signature%s)s" % i)
            sql_params["signature%s" % i] = elem

        sql = """/* socorro.external.postgresql.bugs.Bugs.get */
            SELECT ba.signature, bugs.id
            FROM bugs
                JOIN bug_associations AS ba ON bugs.id = ba.bug_id
            WHERE EXISTS(
                SELECT 1 FROM bug_associations
                WHERE bug_associations.bug_id = bugs.id
                AND signature IN (%s)
            )
        """ % ", ".join(signatures)
        sql = str(" ".join(sql.split()))  # better formatting of the sql string

        error_message = "Failed to retrieve bugs associations from PostgreSQL"
        results = self.query(sql, sql_params, error_message=error_message)

        bugs = []
        for row in results:
            bug = dict(zip(("signature", "id"), row))
            bugs.append(bug)

        return {
            "hits": bugs,
            "total": len(bugs)
        }
