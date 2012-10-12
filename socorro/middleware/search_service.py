# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class Search(DataAPIService):

    """
    Search API interface

    Handle the /search API entry point, parse the parameters, and
    call the API implementation to execute the query.

    """

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
        params = self._bind_params(params)
        params["data_type"] = args[0]
        params["terms"] = self.decode_special_chars(params.get("terms"))

        module = self.get_module(params)
        impl = module.Search(config=self.context)

        return impl.search(**params)

    def _bind_params(self, params):
        """
        Return parameters with names adaptated for the implementation API.
        """
        params["terms"] = params.get("for")
        params["from_date"] = params.get("from")
        params["to_date"] = params.get("to")
        params["fields"] = params.get("in")
        return params
