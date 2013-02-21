# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class CrontabberState(DataAPIService):
    """Return the current state of Crontabber jobs"""

    service_name = "crontabber_state"
    uri = "/crontabber_state/(.*)"

    def __init__(self, config):
        super(CrontabberState, self).__init__(config)
        logger.debug('CrontabberState service __init__')

    def get(self, *args):
        """Called when a GET HTTP request is executed to /crontabber_state"""
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.CrontabberState(config=self.context)
        return impl.get(**params)