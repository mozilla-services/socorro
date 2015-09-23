# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.external import MissingArgumentError
from socorro.lib import external_common

logger = logging.getLogger("webapi")


class ADI(PostgreSQLBase):

    def get(self, **kwargs):
        yesterday = datetime.datetime.utcnow() - datetime.timedelta(1)
        tomorrow = yesterday + datetime.timedelta(2)
        yesterday = yesterday.date()
        tomorrow = tomorrow.date()
        filters = [
            ('start_date', yesterday, 'date'),
            ('end_date', tomorrow, 'date'),
            ('product', '', 'str'),
            ('versions', [], 'list'),
            ('platforms', [], 'list'),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        required = (
            'start_date',
            'end_date',
            'product',
            'versions',
            'platforms',
        )
        missing = []
        for each in required:
            if not params.get(each):
                missing.append(each)
        if missing:
            raise MissingArgumentError(', '.join(missing))

        SQL = """
            SELECT
                SUM(adu_count) AS adi_count,
                adu_date AS date,
                pv.build_type,
                pv.version_string AS version
            FROM
                product_adu
            LEFT OUTER JOIN product_versions pv USING (product_version_id)
            WHERE
                pv.product_name = %(product)s
                AND pv.version_string IN %(versions)s
                AND os_name IN %(platforms)s
                AND adu_date BETWEEN %(start_date)s AND %(end_date)s
            GROUP BY
                adu_date,
                build_type,
                version_string
        """

        params['versions'] = tuple(params['versions'])
        params['platforms'] = tuple(params['platforms'])
        results = self.query(SQL, params)

        fields = (
            'adi_count',
            'date',
            'build_type',
            'version',
        )
        rows = []
        for record in results:
            row = dict(zip(fields, record))
            row['date'] = row['date'].strftime('%Y-%m-%d')
            # BIGINTs become Decimal which becomes floating point in JSON
            row['adi_count'] = long(row['adi_count'])
            rows.append(row)
        return {'hits': rows, 'total': len(rows)}
