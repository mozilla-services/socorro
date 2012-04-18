import logging
import web

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class Bugs(DataAPIService):

    """Return a list of signature - bug id associations. """

    service_name = "bugs"
    uri = "/bugs/"

    def __init__(self, config):
        super(Bugs, self).__init__(config)
        logger.debug('Bugs service __init__')

    def post(self, *args):
        """
        Called when a POST HTTP request is executed to /bugs
        """
        post_args = web.input()
        query_string = "signatures/%s/" % post_args["signatures"]
        params = self.parse_query_string(query_string)
        module = self.get_module(params)
        impl = module.Bugs(config=self.context)
        return impl.get(**params)
