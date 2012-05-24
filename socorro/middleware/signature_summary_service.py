# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from socorro.middleware.service import DataAPIService


class SignatureSummary(DataAPIService):

    service_name = "signature_summary"
    uri = "/signaturesummary/(.*)"

    def __init__(self, config):
        super(SignatureSummary, self).__init__(config)

    def get(self, *args):
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.SignatureSummary(config=self.context)
        return impl.get(**params)
