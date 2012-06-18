# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import web

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class ProductsBuilds(DataAPIService):

    """
    Return information about nightly builds of a product.
    """

    service_name = "products_builds"
    uri = "/products/builds/(.*)"

    def __init__(self, config):
        """
        Constructor
        """
        super(ProductsBuilds, self).__init__(config)
        logger.debug('ProductsBuilds service __init__')

    def get(self, *args):
        """
        Called when a get HTTP request is executed to /search
        """
        params = self.parse_query_string(args[0])

        module = self.get_module(params)
        impl = module.ProductsBuilds(config=self.context)

        return impl.get(**params)

    def post(self, *args):
        """
        Insert a new build given the URL-encoded data provided in the request.
        On success, raises a 303 See Other redirect to the newly-added build.
        """
        params = self.parse_query_string(args[0])
        params.update(web.input())

        module = self.get_module(params)
        impl = module.ProductsBuilds(config=self.context)

        product, version = impl.create(**params)
        raise web.seeother("/products/builds/product/%s/version/%s" %
                           (product, version))
