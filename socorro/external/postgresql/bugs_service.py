# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external import MissingArgumentError, BadArgumentError
from socorro.external.postgresql.service_base import (
    PostgreSQLWebServiceBase
)
from socorro.lib import external_common


#==============================================================================
class Bugs(PostgreSQLWebServiceBase):
    """Implement the /bugs service with PostgreSQL. """

    uri = r'/bugs/(.*)'

    filters = [
        ("signatures", None, ["list", "str"]),
        ("bug_ids", None, ["list", "str"]),
    ]

    #--------------------------------------------------------------------------
    def get(self, **kwargs):
        import warnings
        warnings.warn("You should use the POST method to access bugs")
        return self.post(**kwargs)

    #--------------------------------------------------------------------------
    def post(self, **kwargs):
        """Return a list of signatures-to-bug_ids or bug_ids-to-signatures
           associations. """
        params = external_common.parse_arguments(self.filters, kwargs)

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

        bugs = []
        for row in results:
            bug = dict(zip(("signature", "id"), row))
            bugs.append(bug)

        return {
            "hits": bugs,
            "total": len(bugs)
        }
