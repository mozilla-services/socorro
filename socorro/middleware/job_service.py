import logging

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class Job(DataAPIService):
    """Return a single job from its UUID. """

    service_name = "job"
    uri = "/job/(.*)"

    def __init__(self, config):
        super(Job, self).__init__(config)
        logger.debug('Job service __init__')

    def get(self, *args):
        """Called when a get HTTP request is executed to /job. """
        params = self.parse_query_string(args[0])
        module = self.get_module(params)
        impl = module.Job(config=self.context)
        return impl.get(**params)
