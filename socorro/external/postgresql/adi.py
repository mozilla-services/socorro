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
            ('version', '', 'str'),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        required = (
            'start_date',
            'end_date',
            'product',
            'version',
        )
        missing = []
        for each in required:
            if not params.get(each):
                missing.append(each)
        if missing:
            raise MissingArgumentError(', '.join(missing))

        SQL = """
        SELECT
            SUM(adi_count) AS adi_count,
            date::DATE,
            product_name AS product,
            product_version AS version,
            product_os_platform AS platform,
            update_channel AS release_channel
        FROM
            raw_adi
        WHERE
            product_name = %(product)s AND
            product_version = %(version)s AND
            date BETWEEN %(start_date)s::DATE AND %(end_date)s::DATE
        GROUP BY
            date::DATE,
            product_name,
            product_os_platform,
            product_version,
            update_channel
        """

        results = self.query(SQL, params)

        fields = (
            'adi_count',
            'date',
            'product',
            'version',
            'platform',
            'release_channel',
        )
        rows = []
        for record in results:
            row = dict(zip(fields, record))
            row['date'] = row['date'].strftime('%Y-%m-%d')
            rows.append(row)
        return {'hits': rows}
