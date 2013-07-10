# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class CrashesSignatureHistory(DataAPIService):
    """Return the history of a signature. """

    service_name = "crashes"
    uri = "/crashes/signature_history/(.*)"

    def __init__(self, config):
        super(CrashesSignatureHistory, self).__init__(config)
        logger.debug('CrashesSignatureHistory service __init__')

    def get(self, *args):
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.Crashes(config=self.context)
        return impl.get_signature_history(**params)
