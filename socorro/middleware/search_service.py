import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class Search(DataAPIService):

    """
    Search API interface

    Handle the /search API entry point, parse the parameters, and
    call the API implementation to execute the query.

    """

    default_service_order = [
        "socorro.external.postgresql",
        "socorro.external.elasticsearch"
    ]
    service_name = "search"
    uri = "/search/([^/.]*)/(.*)"

    def __init__(self, config):
        """
        Constructor
        """
        super(Search, self).__init__(config)
        logger.debug('Search service __init__')

    def get(self, *args):
        """
        Call a Search API implementation and return the result.
        """
        # Parse parameters
        params = self.parse_query_string(args[1])
        params["data_type"] = args[0]

        module = self.get_module(params)
        impl = module.Search(self.context)

        return impl.search(**params)
