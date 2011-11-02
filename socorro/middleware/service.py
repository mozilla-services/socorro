import logging
import sys

from socorro.webapi.webapiService import JsonWebServiceBase

logger = logging.getLogger("webapi")


class DataAPIService(JsonWebServiceBase):

    """
    Search API interface

    Handle the /search API entry point, parse the parameters, and
    call the API implementation to execute the query.

    """
    default_service_order = []
    service_name = ""

    def __init__(self, config):
        """
        Constructor
        """
        super(DataAPIService, self).__init__(config)
        logger.debug('DataAPIService __init__')

    def get_module(self, params):
        """
        Find the external module to use and return it.

        Find the external module that will be called by the service to execute
        the required action. If one exists and is valid, use user input first,
        then configuration, then default_service_order of the service.

        Return the imported module.
        """
        impl = None

        # First use user value if it exists
        if "force_api_impl" in params:
            module_name = ".".join(("socorro.external",
                                    params["force_api_impl"],
                                    self.service_name))
            impl = self._import(module_name)
            if impl:
                logger.debug("Service %s uses forced implementation module: %s"
                             % (self.service_name, module_name))

        # Second use config value
        if not impl:
            module_name = "%s.%s" % (self.context.serviceImplementationModule,
                                     self.service_name)
            impl = self._import(module_name)
            if impl:
                logger.debug("Service %s uses config module: %s"
                             % (self.service_name, module_name))

        # Third use module values in order of preference
        if not impl:
            for m in self.default_service_order:
                module_name = "%s.%s" % (m, self.service_name)
                impl = self._import(module_name)
                if impl:
                    logger.debug("Service %s uses default module: %s"
                                 % (self.service_name, module_name))
                    break

        # If no implementation was found raise an error
        if not impl:
            raise NotImplementedError

        # Else return the implementation module
        return impl

    def _import(self, module_name):
        """
        Import a module, check it exists and return it.

        Return the module if it exists, False otherwise.
        """
        logger.debug("Try to import %s" % module_name)
        try:
            __import__(module_name)
            return sys.modules[module_name]
        except ImportError:
            logger.debug("Could not import %s" % module_name)
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
            try:
                if args[i]:
                    params[args[i]] = args[i + 1]
            except IndexError:
                pass

        for i in params:
            if params[i].find(terms_sep) > -1:
                params[i] = params[i].split(terms_sep)

        return params
