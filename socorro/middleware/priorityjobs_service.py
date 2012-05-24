# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import web

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class Priorityjobs(DataAPIService):

    """
    Handle the priority jobs queue for crash reports processing.
    """

    service_name = "priorityjobs"
    uri = "/priorityjobs/(.*)"

    def __init__(self, config):
        super(Priorityjobs, self).__init__(config)
        logger.debug('Priorityjobs service __init__')

    def get(self, *args):
        """Return a job in the priority queue. """
        params = self.parse_query_string(args[0])

        module = self.get_module(params)
        impl = module.Priorityjobs(config=self.context)

        return impl.get(**params)

    def post(self, *args):
        """Add a new job to the priority queue. """
        params = self.parse_query_string(args[0])
        params.update(web.input())

        module = self.get_module(params)
        impl = module.Priorityjobs(config=self.context)

        return impl.create(**params)
