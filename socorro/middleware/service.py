import logging
import sys

import socorro.webapi.webapiService as webapi

logger = logging.getLogger("webapi")


class DataAPIService(webapi.JsonServiceBase):

    """
    Search API interface

    Handle the /search API entry point, parse the parameters, and
    call the API implementation to execute the query.

    """

    def __init__(self, config):
        """
        Constructor
        """
        super(DataAPIService, self).__init__(config)
        self.api_impl = config.searchImplClass(config)
        logger.debug('DataAPIService __init__')

    def get_module(self):
        """
        """
        impl = None

        # First use user value if it exists
        if "force_api_impl" in params:
            module_name = ".".join(("external", params["force_api_impl"],
                                    self.service_name))
            impl = self._import(module_name)

        # Second use config value
        if not impl:
            module_name = ".".join((self.config.serviceImplementationModule,
                                    self.service_name))
            impl = self._import(module_name)

        # Third use module values in order of preference
        if not impl:
            for m in self.default_service_order:
                module_name = ".".join((self.default_service_order[m],
                                        self.service_name))
                impl = self._import(module_name)
                if impl:
                    continue

        # If no implementation was found raise an error
        if not impl:
            raise NotImplementedError

        # Else return the implementation module
        return impl

    def _import(self, module):
        try:
            __import__(module)
            return sys.modules[module]
        except ImportError:
            return False
        return False

    def parse_query_string(self, query_string):
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
