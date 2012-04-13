import logging
import web

from socorro.middleware.service import DataAPIService

logger = logging.getLogger("webapi")


class ReportList(DataAPIService):

    """
    ReportList API interface

    Handle the /search API entry point, parse the parameters, and
    call the API implementation to execute the query.

    Documentation: http://socorro.readthedocs.org/en/latest/middleware.html

    """

    service_name = "report"
    uri = "/report/list/(.*)"

    def __init__(self, config):
        super(ReportList, self).__init__(config)
        logger.debug('ReportList service __init__')

    def get(self, *args):
        """
        Call a ReportList API implementation and return the result.
        """
        # Parse parameters
        params = self.parse_query_string(args[0])
        params = self._bind_params(params)

        module = self.get_module(params)
        impl = module.Report(config=self.context)

        return impl.get_list(**params)

    def _bind_params(self, params):
        """
        Return parameters with names adaptated for the implementation API.
        """
        params["from_date"] = params.get("from")
        params["to_date"] = params.get("to")
        return params
