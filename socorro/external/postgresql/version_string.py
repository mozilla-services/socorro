# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.lib import MissingArgumentError, external_common
from socorro.external.postgresql.base import PostgreSQLBase


logger = logging.getLogger("webapi")


class VersionString(PostgreSQLBase):
    def get(self, **kwargs):
        filters = [
            ('product', None, 'str'),
            ('version', None, 'str'),
            ('build_id', None, 'int'),
            ('release_channel', None, 'str'),
        ]
        params = external_common.parse_arguments(filters, kwargs)
        required = ('product', 'build_id', 'version', 'release_channel')
        for key in required:
            if not params.get(key):
                raise MissingArgumentError(key)

        sql = """
            SELECT
                pv.version_string
            FROM product_versions pv
                LEFT JOIN product_version_builds pvb ON
                    (pv.product_version_id = pvb.product_version_id)
            WHERE pv.product_name = %(product)s
            AND pv.release_version = %(version)s
            AND pvb.build_id = %(build_id)s
            AND pv.build_type = %(release_channel)s
        """
        results = self.query(sql, params)

        # The query can return multiple results, but they're the same value. So
        # we just return the first one.
        version_string = [
            row['version_string'] for row in results.zipped()
        ]
        if version_string:
            version_string = [version_string[0]]

        return {
            'hits': version_string
        }
