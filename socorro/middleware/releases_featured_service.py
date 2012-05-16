import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class ReleasesFeatured(DataAPIService):
    """Handle featured versions of a given product.
    """

    service_name = "releases"
    uri = "/releases/featured/(.*)"

    def __init__(self, config):
        super(ReleasesFeatured, self).__init__(config)
        logger.debug('Extensions service __init__')

    def get(self, *args):
        """Called when a get HTTP request is executed to /releases/featured.
        """
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.Releases(config=self.context)
        return impl.get_featured(**params)

    def put(self, *args):
        """Called when a put HTTP request is executed to /releases/featured.
        """
        params = self.parse_query_string(args[0])
        params.update(web.input())

        module = self.get_module(params)
        impl = module.Releases(config=self.context)

        return impl.update_featured(**params)
