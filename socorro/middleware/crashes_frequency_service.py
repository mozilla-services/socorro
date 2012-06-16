# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class CrashesFrequency(DataAPIService):
    """Return the number and frequency of crashes on each OS.
    """

    service_name = "crashes"
    uri = "/crashes/frequency/(.*)"

    def __init__(self, config):
        super(CrashesFrequency, self).__init__(config)
        logger.debug('CrashesFrequency service __init__')

    def get(self, *args):
        """Called when a get HTTP request is executed to /crashes/frequency/.
        """
        params = self.parse_query_string(args[0])
        params = self._bind_params(params)

        module = self.get_module(params)
        impl = module.Crashes(config=self.context)
        return impl.get_frequency(**params)

    def _bind_params(self, params):
        """
        Return parameters with names adaptated for the implementation API.
        """
        params["from_date"] = params.get("from")
        params["to_date"] = params.get("to")
        return params
