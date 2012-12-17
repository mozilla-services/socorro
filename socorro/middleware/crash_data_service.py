# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging
import web

from socorro.external import ResourceNotFound, ResourceUnavailable
from socorro.middleware.service import DataAPIService
from socorro.webapi import webapiService

logger = logging.getLogger("webapi")


class CrashData(DataAPIService):

    """
    Return JSON data of a crash report, given its uuid.
    """

    service_name = "crash_data"
    uri = "/crash_data/(.*)"

    def __init__(self, config):
        super(CrashData, self).__init__(config)
        logger.debug('CrashData service __init__')

    def get(self, *args):
        """
        Called when a get HTTP request is executed to /crash_data
        """
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.CrashData(config=self.context)
        try:
            return impl.get(**params)
        except ResourceNotFound:
            raise web.webapi.NotFound()
        except ResourceUnavailable:
            raise webapiService.Timeout()
