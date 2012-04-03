from socorro.middleware.service import DataAPIService


class CrashTrends(DataAPIService):

    service_name = "crash_trends"
    uri = "/crashtrends/(.*)"

    def __init__(self, config):
        super(CrashTrends, self).__init__(config)

    def get(self, *args):
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.CrashTrends(config=self.context)
        return impl.get(**params)
