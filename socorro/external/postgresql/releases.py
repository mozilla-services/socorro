# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import psycopg2

from socorro.lib import (
    MissingArgumentError,
    external_common,
)
from socorro.external.postgresql.base import PostgreSQLBase
from .dbapi2_util import execute_no_results, single_row_sql

logger = logging.getLogger("webapi")


class Releases(PostgreSQLBase):
    def post(self, **kwargs):
        filters = [
            ('product', None, 'str'),
            ('version', None, 'str'),
            ('update_channel', None, 'str'),
            ('build_id', None, 'str'),
            ('platform', None, 'str'),
            ('beta_number', None, 'int'),
            ('release_channel', None, 'str'),
            ('throttle', None, 'int'),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        # all fields are mandatory
        for key in [x[0] for x in filters if x[1] is None]:
            if key == 'beta_number':
                # exception because this can either be a non-zero integer
                # or a None
                if params.get(key) is not None:
                    if not params.get(key):
                        raise MissingArgumentError(key)

            elif not params.get(key) and params.get(key) != 0:
                raise MissingArgumentError(key)

        with self.get_connection() as connection:
            try:
                single_row_sql(
                    connection,
                    # product, version, update_channel, build_id, platform,
                    # beta_number
                    "SELECT add_new_release(%s, %s, %s, %s, %s, %s)",
                    (
                        params['product'],
                        params['version'],
                        params['update_channel'],
                        params['build_id'],
                        params['platform'],
                        params['beta_number']
                    ),
                )
                execute_no_results(
                    connection,
                    """
                        INSERT INTO product_release_channels
                        (product_name, release_channel, throttle)
                        SELECT %s, %s, %s
                        WHERE NOT EXISTS (
                            SELECT product_name, release_channel
                            FROM product_release_channels
                            WHERE
                            product_name = %s
                            AND
                            release_channel = %s
                        )
                    """,
                    (
                        params['product'],
                        params['release_channel'],
                        params['throttle'],
                        params['product'],
                        params['release_channel'],
                    ),
                )
                single_row_sql(
                    connection,
                    "SELECT update_product_versions()"
                )
            except psycopg2.Error:
                connection.rollback()
                raise
            else:
                connection.commit()

        return True
