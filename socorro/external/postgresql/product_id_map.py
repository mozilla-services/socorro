# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.external.postgresql.base import PostgreSQLBase


logger = logging.getLogger("webapi")


class ProductIDMap(PostgreSQLBase):

    def get(self, **kwargs):
        sql = """
            SELECT product_name, productid, rewrite FROM
            product_productid_map WHERE rewrite IS TRUE
        """

        product_mappings = self.query(sql)

        product_id_map = {}
        for product_name, productid, rewrite in product_mappings:
            product_id_map[productid] = {
                'product_name': product_name,
                'rewrite': rewrite
            }
        return product_id_map
