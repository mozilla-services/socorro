# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorrolib.lib import (
    MissingArgumentError,
    BadArgumentError,
    external_common,
)
from socorro.external.postgresql.base import PostgreSQLBase

logger = logging.getLogger("webapi")


class Bugs(PostgreSQLBase):
    """Implement the /bugs service with PostgreSQL. """
    filters = [
        ("signatures", None, [str]),
        ("bug_ids", None, [int]),
    ]

    def get(self, **kwargs):
        """Return a list of signatures-to-bug_ids or bug_ids-to-signatures
           associations. """
        params = external_common.parse_arguments(
            self.filters,
            kwargs,
            modern=True
        )

        if not params['signatures'] and not params['bug_ids']:
            raise MissingArgumentError('specify one of signatures or bug_ids')
        elif params['signatures'] and params['bug_ids']:
            raise BadArgumentError('specify only one of signatures or bug_ids')

        sql_params = []
        if params['signatures']:
            sql_params.append(tuple(params.signatures))

            sql = """/* socorro.external.postgresql.bugs.Bugs.get */
                SELECT ba.signature, bugs.id
                FROM bugs
                    JOIN bug_associations AS ba ON bugs.id = ba.bug_id
                WHERE EXISTS(
                    SELECT 1 FROM bug_associations
                    WHERE bug_associations.bug_id = bugs.id
                    AND signature IN %s
                )
            """
        elif params['bug_ids']:
            sql_params.append(tuple(params.bug_ids))

            sql = """/* socorro.external.postgresql.bugs.Bugs.get */
                SELECT ba.signature, bugs.id
                FROM bugs
                    JOIN bug_associations AS ba ON bugs.id = ba.bug_id
                WHERE bugs.id IN %s
            """

        error_message = "Failed to retrieve bug associations from PostgreSQL"
        results = self.query(sql, sql_params, error_message=error_message)

        bugs = results.zipped()

        return {
            "hits": bugs,
            "total": len(bugs)
        }
