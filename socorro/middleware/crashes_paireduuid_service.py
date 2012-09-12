# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class CrashesPaireduuid(DataAPIService):
    """Return paired UUIDs of a crash report.
    """

    service_name = "crashes"
    uri = "/crashes/paireduuid/(.*)"

    def __init__(self, config):
        super(CrashesPaireduuid, self).__init__(config)
        logger.debug('CrashesPaireduuid service __init__')

    def get(self, *args):
        """
        Called when a get HTTP request is executed to /crashes/paireduuid/
        """
        params = self.parse_query_string(args[0])
        params["signature"] = self.decode_special_chars(
                                                params.get("signature", ""))

        module = self.get_module(params)
        impl = module.Crashes(config=self.context)

        return impl.get_paireduuid(**params)
