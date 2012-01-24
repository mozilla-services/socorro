import logging

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
