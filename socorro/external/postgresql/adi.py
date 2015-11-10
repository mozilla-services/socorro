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

        sql_versions = []
        for i, version in enumerate(params['versions'], start=1):
            key = 'version{}'.format(i)
            # We make a very special exception for versions that end with
            # the letter 'b'. It means it's a beta version and when some
            # queries on that version they actually mean all
            # the "sub-versions". For example version="19.0b" actually
            # means "all versions starting with '19.0b'".
            # This is succinct with what we do in SuperSearch.
            if version.endswith('b'):
                # exception!
                sql_versions.append('pv.version_string LIKE %({})s'.format(
                    key
                ))
                version += '%'
            else:
                # the norm
                sql_versions.append('pv.version_string = %({})s'.format(key))
            params[key] = version

        sql = """
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
                AND ({})
                AND os_name IN %(platforms)s
                AND adu_date BETWEEN %(start_date)s AND %(end_date)s
            GROUP BY
                adu_date,
                build_type,
                version_string
        """.format(
            ' OR '.join(sql_versions)
        )

        params['platforms'] = tuple(params['platforms'])
        assert isinstance(params, dict)
        results = self.query(sql, params)

        rows = []
        for row in results.zipped():
            row.date = row.date.strftime('%Y-%m-%d')
            # BIGINTs become Decimal which becomes floating point in JSON
            row.adi_count = long(row.adi_count)
            rows.append(row)
        return {'hits': rows, 'total': len(rows)}
