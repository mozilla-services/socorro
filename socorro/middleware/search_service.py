import logging

import socorro.middleware.service
import socorro.search.elasticsearch as es
import socorro.search.postgresql as pg

logger = logging.getLogger("webapi")


class Search(service.DataAPIService):

    """
    Search API interface

    Handle the /search API entry point, parse the parameters, and
    call the API implementation to execute the query.

    """
    service_name = "search"
    uri = "/201105/search/([^/.]*)/(.*)"

    def __init__(self, config):
        """
        Constructor
        """
        super(Search, self).__init__(config)
        logger.debug('Search service __init__')

    def get(self, *args):
        """
        Called when a get HTTP request is executed to /search
        """
        # Parse parameters
        params = self.parse_query_string(args[1])
        params["type"] = args[0]

        module = self.get_module()
        impl = module.Search(self.config)

        return impl.search(**params)
