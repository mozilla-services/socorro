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
        ("bug_ids", None, ["list", "str"]),
    ]

    def get(self, **kwargs):
        import warnings
        warnings.warn("You should use the POST method to access bugs")
        return self.post(**kwargs)

    def post(self, **kwargs):
        """Return a list of signatures-to-bug_ids or bug_ids-to-signatures
           associations. """
        params = external_common.parse_arguments(self.filters, kwargs)

        if not params['signatures'] and not params['bug_ids']:
            raise MissingArgumentError('specify one of signatures or bug_ids')
        elif params['signatures'] and params['bug_ids']:
            raise BadArgumentError('specify only one of signatures or bug_ids')

        sql_params = {}
        if params['signatures']:
            signatures = []
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
        elif params['bug_ids']:
            bug_ids = []
            for i, elem in enumerate(params.bug_ids):
                bug_ids.append("%%(bugs%s)s" % i)
                sql_params["bugs%s" % i] = elem

            sql = """/* socorro.external.postgresql.bugs.Bugs.get */
                SELECT ba.signature, bugs.id
                FROM bugs
                    JOIN bug_associations AS ba ON bugs.id = ba.bug_id
                WHERE bugs.id IN (%s)
            """ % ", ".join(bug_ids)


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

