# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging

from socorro.external.postgresql.base import PostgreSQLBase
from socorrolib.lib import external_common


logger = logging.getLogger("webapi")


class MissingSymbols(PostgreSQLBase):

    def _get_sql_params(self, **kwargs):
        filters = [
            (
                'date',
                (
                    datetime.datetime.utcnow() - datetime.timedelta(days=1)
                ).date(),
                'date'
            ),
            (
                'limit',
                None,
                int
            ),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        sql = """
        SELECT debug_file, debug_id, code_file, code_id
        FROM missing_symbols
        WHERE
            date_processed = %(date)s AND
            debug_file != '' AND
            debug_id != ''
        GROUP BY debug_file, debug_id, code_file, code_id
        """
        if params['limit'] is not None:
            sql += '\nLIMIT %(limit)s'
        return sql, params

    def iter(self, **kwargs):
        """return an iterator that yields dicts that look like this:
            {
                'debug_file': ...,
                'debug_id': ...,
                'code_file': ...,
                'code_id': ...,
            }

        The reason this is important and useful to have is that missing
        symbols recordsets tend to be very very large so it's not
        a good idea to allocate it into one massive big list.
        """
        sql, params = self._get_sql_params(**kwargs)
        with self.cursor(sql, params) as cursor:
            names = [x.name for x in cursor.description]
            for row in cursor:
                yield dict(zip(names, row))
