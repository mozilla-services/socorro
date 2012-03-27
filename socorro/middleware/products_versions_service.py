import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class ProductsVersions(DataAPIService):

    service_name = "products"
    uri = "/products/(.*)"

    def __init__(self, config):
        super(ProductsVersions, self).__init__(config)
        logger.debug('ProductsVersions service __init__')

    def get(self, *args):
        params = self.parse_query_string(args[0])

        module = self.get_module(params)

        impl = module.Products(config=self.context)

        return impl.get_versions(**params)
