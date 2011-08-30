import logging

import socorro.webapi.webapiService as webapi
import socorro.search.elasticsearch as es
import socorro.search.postgresql as pg

logger = logging.getLogger("webapi")


class Search(webapi.JsonServiceBase):

    """
    Search API interface

    Handle the /search API entry point, parse the parameters, and
    call the API implementation to execute the query.

    """

    def __init__(self, config):
        """
        Constructor
        """
        super(Search, self).__init__(config)
        self.api_impl = config.searchImplClass(config)
        logger.debug('Search __init__')

    uri = '/201105/search/([^/.]*)/(.*)'

    def get(self, *args):
        """
        Called when a get HTTP request is executed to /search
        """
        # Parse parameters
        params = self._parse_query_string(args[1])
        types = args[0]

        # If one wants to choose the api to use, then force it
        forced_api_impl = None
        if "force_search_impl" in params:
            if params["force_search_impl"] == "es":
                forced_api_impl = es.ElasticSearchAPI(self.context)
            elif params["force_search_impl"] == "pg":
                forced_api_impl = pg.PostgresAPI(self.context)

        # API to actually call
        api = forced_api_impl or self.api_impl

        return api.search(types, **params)

    def _parse_query_string(self, query_string):
        """
        Take a string of parameters and return a dictionary of key, value.
        """
        terms_sep = "+"
        params_sep = "/"

        args = query_string.split(params_sep)

        params = {}
        for i in xrange(0, len(args), 2):
            if args[i] and args[i + 1]:
                params[args[i]] = args[i + 1]

        for i in params:
            if params[i].find(terms_sep) > -1:
                params[i] = params[i].split(terms_sep)

        return params
