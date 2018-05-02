# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from socorro.lib import MissingArgumentError, external_common
from socorro.external.postgresql.base import PostgreSQLBase


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
                first_build::VARCHAR
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

    def post(self, **kwargs):
        filters = [
            ('signature', None, str),
            ('first_report', None, datetime.datetime),
            ('first_build', None, str),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        sql_upsert = """
        WITH
        update_signature AS (
            UPDATE signatures
            SET
                first_report = LEAST(
                    %(first_report)s,
                    (SELECT first_report FROM signatures WHERE signature = %(signature)s)
                ),
                first_build = LEAST(
                    %(first_build)s,
                    (SELECT first_build FROM signatures WHERE signature = %(signature)s)
                )
            WHERE
                signature = %(signature)s
            RETURNING 1
        ),
        insert_signature AS (
            INSERT INTO
                signatures
                (signature, first_report, first_build)
            SELECT
                %(signature)s AS signature,
                %(first_report)s AS first_report,
                %(first_build)s AS first_build
            WHERE NOT EXISTS (
                SELECT *
                FROM signatures
                WHERE
                    signature = %(signature)s
                LIMIT 1
            )
            RETURNING 2
        )
        SELECT * FROM update_signature
        UNION ALL
        SELECT * FROM insert_signature
        """

        self.query(sql_upsert, params)
