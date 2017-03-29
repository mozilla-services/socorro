# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import logging
import itertools

import psycopg2

from socorro.lib.datetimeutil import string_to_datetime
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common
from .dbapi2_util import single_row_sql


logger = logging.getLogger("webapi")


class SmartDate(object):

    def clean(self, value):
        if any(itertools.imap(value.startswith, ('>=', '<='))):
            op = value[:2]
            value = value[2:]
        elif any(itertools.imap(value.startswith, ('=', '>', '<'))):
            op = value[:1]
            value = value[1:]
        else:
            op = '='
        return (op, string_to_datetime(value).date())


class ProductVersions(PostgreSQLBase):

    def get(self, **kwargs):
        filters = [
            ("version", None, [str]),
            ("product", None, [str]),
            ("is_featured", None, bool),
            ("start_date", None, SmartDate()),
            ("end_date", None, SmartDate()),
            ("active", None, bool),
            ("is_rapid_beta", None, bool),
            ("build_type", None, [str]),
        ]
        params = external_common.parse_arguments(filters, kwargs, modern=True)
        where = []
        sql_params = {}
        for param, value in params.items():
            if value is None:
                continue
            param = {
                'product': 'pv.product_name',
                'version': 'version_string',
                'is_featured': 'featured_version',
                'end_date': 'sunset_date',
                'start_date': 'build_date',
            }.get(param, param)

            if param == 'active':
                # This is a convenient exception. It makes it possible
                # to query for only productversions that are NOT sunset
                # without having to do any particular date arithmetic.
                param = 'sunset_date'
                operator_ = value and '>=' or '<'
                value = datetime.datetime.utcnow().date().isoformat()
            elif isinstance(value, list):
                operator_ = 'IN'
                value = tuple(value)
            elif isinstance(value, tuple):
                assert len(value) == 2
                operator_, value = value
            else:
                operator_ = '='
            where.append('{} {} %({})s'.format(
                param,
                operator_,
                param
            ))
            sql_params[param] = value

        # rewrite it to a string
        if where:
            sql_where = 'WHERE ' + ' AND '.join(where)
        else:
            sql_where = ''

        sql = """
            /* socorro.external.postgresql.products.ProductVersions.get */
            SELECT
                pv.product_name AS product,
                pv.version_string AS version,
                pv.build_date AS start_date,
                pv.sunset_date AS end_date,
                ((prc.throttle * (100)::numeric))::REAL AS throttle,
                pv.featured_version AS is_featured,
                pv.build_type,
                pv.has_builds,
                pv.is_rapid_beta
            FROM (
                ( product_versions pv
                  JOIN product_release_channels prc
                    ON (
                        pv.product_name = prc.product_name AND
                        pv.build_type = prc.release_channel
                  )
                  JOIN products
                    ON pv.product_name = products.product_name
                )
                JOIN release_channels
                    ON pv.build_type = release_channels.release_channel
            )
            {}
            ORDER BY products.sort, version_sort DESC, release_channels.sort
        """.format(sql_where)
        results = self.query(sql, sql_params).zipped()

        return {
            'hits': results,
            'total': len(results),
        }

    def post(self, **kwargs):
        """adding a new product"""
        filters = [
            ("product", None, "str"),
            ("version", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        with self.get_connection() as connection:
            try:
                result, = single_row_sql(
                    connection,
                    "SELECT add_new_product(%s, %s)",
                    (params['product'], params['version']),
                )
            except psycopg2.Error:
                connection.rollback()
                return False
            else:
                connection.commit()
            return result
