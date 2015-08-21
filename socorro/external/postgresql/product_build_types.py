# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external import MissingArgumentError
from socorro.external.postgresql.base import PostgreSQLBase
from socorro.lib import external_common


logger = logging.getLogger("webapi")


class ProductBuildTypes(PostgreSQLBase):

    def get(self, **kwargs):
        """Return a dict that holds the throttling value per build type
        for a specific product."""
        filters = [
            ('product', None, 'str'),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        required = ('product',)
        for key in required:
            if not params.get(key):
                raise MissingArgumentError(key)

        sql = """
            SELECT
                build_type,
                throttle
            FROM product_build_types
            WHERE product_name = %(product)s
        """
        results = self.query(sql, params)

        build_types = {}
        for row in results:
            build_types[row[0]] = row[1]

        return {
            'hits': build_types,
        }
