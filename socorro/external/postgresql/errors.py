# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import datetimeutil, external_common


class Errors(PostgreSQLBase):
    '''Implement the /errors services with PostgreSQL. '''

    def get_signatures(self, **kwargs):
        '''Return a list of errors aggregated by signatures. '''
        now = datetimeutil.utc_now()
        lastweek = now - datetime.timedelta(7)

        filters = [
            ('signature', None, 'str'),
            ('search_mode', 'is_exactly', 'str'),
            ('product', None, 'str'),
            ('start_date', lastweek, 'datetime'),
            ('end_date', now, 'datetime'),
        ]
        params = external_common.parse_arguments(filters, kwargs)

        authorized_search_modes = (
            'is_exactly',
            'contains',
            'starts_with',
            'ends_with'
        )
        if params.search_mode not in authorized_search_modes:
            search_mode = authorized_search_modes[0]

        fields = ('signature', 'count')
        sql_fields = {
            'signature': 'signature',
            'count': 'count(crash_id) as total'
        }

        sql = '''/* socorro.external.postgresql.error.Error.get */
            SELECT %s
            FROM bixie.crashes
            WHERE success IS NOT NULL
            AND processor_completed_datetime BETWEEN
                %%(start_date)s AND %%(end_date)s
        ''' % ', '.join(sql_fields[x] for x in fields)

        sql_where = [sql]
        if params.signature:
            if params.search_mode == 'is_exactly':
                sql_where.append('signature = %(signature)s')
            else:
                if params.search_mode == 'contains':
                    params.signature = '%%%s%%' % params.signature
                elif params.search_mode == 'starts_with':
                    params.signature = '%%%s' % params.signature
                elif params.search_mode == 'ends_with':
                    params.signature = '%s%%' % params.signature

                sql_where.append('signature LIKE %(signature)s')

        if params.product:
            sql_where.append('product = %(product)s')

        sql = ' AND '.join(sql_where)

        sql_group = 'GROUP BY signature'
        sql_order = 'ORDER BY total DESC, signature'

        sql = ' '.join((sql, sql_group, sql_order))

        error_message = 'Failed to retrieve error data from PostgreSQL'
        results = self.query(sql, params, error_message=error_message)

        errors = []
        for row in results:
            error = dict(zip(fields, row))
            errors.append(error)

        return {
            'hits': errors,
            'total': len(errors)
        }
