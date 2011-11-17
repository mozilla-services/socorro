import logging
import sys

from socorro.webapi.webapiService import JsonWebServiceBase

logger = logging.getLogger("webapi")


class DataAPIService(JsonWebServiceBase):

    """
    Base class for new-style REST API services.

    Provide methods for arguments parsing and implementation finding.

    """

    default_service_order = []
    service_name = ""

    def __init__(self, config):
        """
        Contruct that object, init parent class.

        Parameters:
        config -- Configuration of the application.
        """
        super(DataAPIService, self).__init__(config)
        logger.debug('DataAPIService __init__')

    def get_module(self, params):
        """
        Find the external module to use and return it.

        Find the external module that will be called by the service to execute
        the required action. If one exists and is valid, use user input first,
        then configuration, then default_service_order of the service.

        Raise a NotImplementedError if no implementation was found.

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
            logger.debug("Service %s uses forced implementation module: %s" %
                         (self.service_name, module_name))
            return impl

        # Second use config value
        module_name = "%s.%s" % (self.context.serviceImplementationModule,
                                 self.service_name)
        impl = self._import(module_name)

        if impl:
            logger.debug("Service %s uses config module: %s" %
                         (self.service_name, module_name))
            return impl

        # Third use module values in order of preference
        for m in self.default_service_order:
            module_name = "%s.%s" % (m, self.service_name)
            impl = self._import(module_name)
            if impl:
                logger.debug("Service %s uses default module: %s" %
                             (self.service_name, module_name))
                return impl

        # No implementation was found, raise an error
        raise NotImplementedError

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

    def parse_query_string(self, query_string):
        """
        Take a string of parameters and return a dictionary of key, value.

        Example 1:
            "param/value/"
            =>
            {
                "param": "value"
            }

        Example 2:
            "param1/value1/param2/value21+value22+value23/"
            =>
            {
                "param1": "value1",
                "param2": [
                    "value21",
                    "value22",
                    "value23"
                ]
            }

        Example 3:
            "param1/value1/param2/"
            =>
            {
                "param1": "value1"
            }

        """
        terms_sep = "+"
        params_sep = "/"

        args = query_string.split(params_sep)

        params = {}
        for i in range(0, len(args), 2):
            try:
                if args[i]:
                    params[args[i]] = args[i + 1]
            except IndexError:
                pass

        for i in params:
            if params[i].find(terms_sep) > -1:
                params[i] = params[i].split(terms_sep)

        return params
