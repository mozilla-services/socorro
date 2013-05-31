# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class Correlations(DataAPIService):
    """return correlations for a specific search"""

    service_name = "correlations"
    uri = "/correlations/(.*)"

    def __init__(self, config):
        super(Correlations, self).__init__(config)

    def get(self, *args):
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.Correlations(config=self.context)
        return impl.get(**params)
