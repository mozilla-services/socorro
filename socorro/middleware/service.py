# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import sys
import web

from socorro.webapi.webapiService import JsonWebServiceBase

logger = logging.getLogger("webapi")


class DataAPIService(JsonWebServiceBase):

    """
    Base class for new-style REST API services.

    Provide methods for arguments parsing and implementation finding.

    """

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
        then this service's configuration, then default services'
        configuration.

        Raise a 400 Bad Request HTTP error if user forced the implementation
        to a value that does not exist.

        Raise an internal error if configuration is improper.

        Return the imported module otherwise.

        """
        if "force_api_impl" in params:
            module_name = ".".join(("socorro.external",
                                    params["force_api_impl"],
                                    self.service_name))
            try:
                __import__(module_name)
                return sys.modules[module_name]
            except ImportError:
                logger.debug("Could not import %s" % module_name)
                raise web.webapi.BadRequest()

        service_config_key = "%sImplementationModule" % self.service_name
        if service_config_key in self.context:
            # Use that specific service's config value
            module_name = "%s.%s" % (self.context[service_config_key],
                                     self.service_name)
        else:
            # Use the generic services' config value
            module_name = "%s.%s" % (self.context.serviceImplementationModule,
                                     self.service_name)

        try:
            __import__(module_name)
            return sys.modules[module_name]
        except ImportError:
            logger.debug("Could not import %s" % module_name)
            raise web.webapi.InternalError(message=("Improper configuration, "
                                     "could not find module %s" % module_name))

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
