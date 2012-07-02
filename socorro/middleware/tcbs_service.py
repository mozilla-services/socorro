# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class TCBS(DataAPIService):

    """
    Return top crashers by signatures.
    """

    service_name = "crashes"
    uri = "/crashes/signatures/(.*)"

    def __init__(self, config):
        """
        Constructor
        """
        super(TCBS, self).__init__(config)
        logger.debug('TCBS service __init__')

    def get(self, *args):
        """
        Called when a get HTTP request is executed to /crashes/signatures
        """
        params = self.parse_query_string(args[0])

        module = self.get_module(params)
        logger.debug(module)
        impl = module.Crashes(config=self.context)

        return impl.get_signatures(**params)
