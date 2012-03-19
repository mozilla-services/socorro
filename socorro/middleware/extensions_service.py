import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class Extensions(DataAPIService):
    """Return a list of extensions associated with a crash's UUID.
    """

    service_name = "extensions"
    uri = "/extensions/(.*)"

    def __init__(self, config):
        super(Extensions, self).__init__(config)
        logger.debug('Extensions service __init__')

    def get(self, *args):
        """Called when a get HTTP request is executed to /extensions.
        """
        params = self.parse_query_string(args[0])

        module = self.get_module(params)
        impl = module.Extensions(config=self.context)

        return impl.get(**params)
