# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class ServerStatus(DataAPIService):
    """Return the current state of the server and the revisions of Socorro and
    Breakpad. """

    service_name = "server_status"
    uri = "/server_status/(.*)"

    def __init__(self, config):
        super(ServerStatus, self).__init__(config)
        logger.debug('ServerStatus service __init__')

    def get(self, *args):
        """Called when a get HTTP request is executed to /server_status. """
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.ServerStatus(config=self.context)
        return impl.get(**params)
