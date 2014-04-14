# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

import psycopg2

from socorro.external import MissingArgumentError, BadArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common


class GraphicsDevices(PostgreSQLBase):

    def get(self, **kwargs):
        filters = [
            ("vendor_hex", None, "str"),
            ("adapter_hex", None, "str"),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        for key in ('vendor_hex', 'adapter_hex'):
            if not params[key]:
                raise MissingArgumentError(key)

        sql_where = """
            WHERE
                vendor_hex = %(vendor_hex)s
                AND
                adapter_hex = %(adapter_hex)s
        """
        sql_query = """
            SELECT
                vendor_hex, adapter_hex, vendor_name, adapter_name
            FROM graphics_device
        """
        results = self.query(sql_query + sql_where, params)
        keys = 'vendor_hex', 'adapter_hex', 'vendor_name', 'adapter_name'
        hits = [dict(zip(keys, x)) for x in results]
        return {'hits': hits, 'total': len(hits)}

    def post(self, **kwargs):
        try:
            data = json.loads(kwargs['data'])
            if data is None:
                raise BadArgumentError('POST data sent was null')
        except AttributeError:
            raise MissingArgumentError('No POST data sent')
        except ValueError:
            raise BadArgumentError('Posted data not valid JSON')
        except TypeError:
            # happens if kwargs['data'] is None
            raise BadArgumentError('POST data sent was empty')

        # make an upsert for each thing and rollback if any failed
        upsert = """
        WITH
        update_graphics_device AS (
            UPDATE graphics_device
            SET
                adapter_name = %(adapter_name)s,
                vendor_name = %(vendor_name)s
            WHERE
                vendor_hex = %(vendor_hex)s
                AND
                adapter_hex = %(adapter_hex)s
            RETURNING 1
        ),
        insert_graphics_device AS (
            INSERT INTO
                graphics_device
                (vendor_hex, adapter_hex, vendor_name, adapter_name)
            SELECT
                %(vendor_hex)s AS vendor_hex,
                %(adapter_hex)s AS adapter_hex,
                %(vendor_name)s AS vendor_name,
                %(adapter_name)s AS adapter_name
            WHERE NOT EXISTS (
                SELECT * FROM graphics_device
                WHERE
                    vendor_hex = %(vendor_hex)s
                    AND
                    adapter_hex = %(adapter_hex)s
                LIMIT 1
            )
            RETURNING 2
        )
        SELECT * FROM update_graphics_device
        UNION
        ALL SELECT * FROM insert_graphics_device
        """

        with self.get_connection() as connection:
            try:
                for row in data:
                    self.query(upsert, row, connection=connection)
                connection.commit()
                return True
            except (psycopg2.Error, KeyError):
                # KeyErrors happen if any of the rows don't have
                # all the required keys
                connection.rollback()
                return False
