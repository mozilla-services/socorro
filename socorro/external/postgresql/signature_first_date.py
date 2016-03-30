# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.external import MissingArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorrolib.lib import external_common


class SignatureFirstDate(PostgreSQLBase):
    filters = [
        ('signatures', None, ['list', 'str']),
    ]

    def get(self, **kwargs):
        params = external_common.parse_arguments(self.filters, kwargs)

        if not params['signatures']:
            raise MissingArgumentError('signatures')

        sql_params = [tuple(params['signatures'])]
        sql = """
            SELECT
                signature,
                first_report AS first_date,
                first_build
            FROM signatures
            WHERE signature IN %s
        """

        error_message = 'Failed to retrieve signatures from PostgreSQL'
        results = self.query(sql, sql_params, error_message=error_message)

        signatures = results.zipped()
        return {
            'hits': signatures,
            'total': len(signatures)
        }
