import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class Crash(DataAPIService):

    """
    Return a single crash report from it's UUID.
    """

    service_name = "crash"
    uri = "/crash/(.*)"

    def __init__(self, config):
        super(Crash, self).__init__(config)
        logger.debug('Crash service __init__')

    def get(self, *args):
        """
        Called when a get HTTP request is executed to /crash
        """
        params = self.parse_query_string(args[0])

        module = self.get_module(params)
        impl = module.Crash(config=self.context)

        return impl.get(**params)
