# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class Platforms(DataAPIService):
    """Return data about all platforms. """

    service_name = "platforms"
    uri = "/platforms/(.*)"

    def __init__(self, config):
        super(Platforms, self).__init__(config)
        logger.debug('Platforms service __init__')

    def get(self, *args):
        """
        Called when a get HTTP request is executed to /platforms
        """
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.Platforms(config=self.context)
        return impl.get(**params)
