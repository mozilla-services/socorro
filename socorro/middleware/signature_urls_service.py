# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class SignatureURLs(DataAPIService):

    service_name = "signature_urls"
    uri = "/signatureurls/(.*)"

    def __init__(self, config):
        super(SignatureURLs, self).__init__(config)
        logger.debug('SignatureURLs service __init__')

    def get(self, *args):
        params = self.parse_query_string(args[0])
        params["signature"] = self.decode_special_chars(
                                                params.get("signature", ""))

        module = self.get_module(params)

        impl = module.SignatureURLs(config=self.context)

        return impl.get(**params)
