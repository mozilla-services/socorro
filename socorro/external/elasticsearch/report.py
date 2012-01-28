import datetime
import json
import logging

from socorro.external.elasticsearch.base import ElasticSearchBase
from socorro.services.versions_info import VersionsInfo
from socorro.lib import datetimeutil, search_common


logger = logging.getLogger("webapi")


class Report(ElasticSearchBase):

    """
    Implement the /report services with ElasticSearch.
    """

    def get_list(self, **kwargs):
        """
        List all crashes with a given signature and return them.

        Optional arguments: see SearchCommon.get_parameters()

        """
        params = search_common.get_parameters(kwargs)

        # Search does not have a signature parameter, so we handle this one
        # separately and make sure it's a list of one string only.
        params["signature"] = kwargs.get("signature")

        if params["signature"] is None:
            return None

        if not isinstance(params["signature"], list):
            params["signature"] = [params["signature"]]

        # If using full days, remove the time part of datetimes
        if params["use_full_days"]:
            params["from_date"] = params["from_date"].date()
            params["to_date"] = params["to_date"].date()

        # Get information about the versions
        versions_service = VersionsInfo(self.context)
        params["versions_info"] = versions_service.versions_info(params)

        # Whatever the source was, we always search for an exact signature
        params["terms"] = params["signature"]
        params["search_mode"] = "is_exactly"

        query = self.build_query_from_params(params)
        json_query = json.dumps(query)
        logger.debug("Query the crashes or signatures: %s", json_query)

        es_result = self.query(params["from_date"], params["to_date"],
                               json_query)
        es_data = json.loads(es_result[0])

        if es_data:
            total = es_data["hits"]["total"]
            hits = es_data["hits"]["hits"]
        else:
            total = 0
            hits = []

        # filter results fields
        fields = [
            "date_processed",
            "uptime",
            "user_comments",
            "uuid",
            "product",
            "version",
            "build",
            "signature",
            "url",
            "os_name",
            "os_version",
            "cpu_name",
            "cpu_info",
            "address",
            "reason",
            "last_crash",
            "install_age",
            "hangid",
            "process_type",
            "client_crash_date"
        ]
        filtered_hits = []
        for hit in hits:
            filtered_hit = dict((f, hit["_source"][f]) for f in hit["_source"]
                                                                if f in fields)

            client_crash_date = datetimeutil.string_to_datetime(
                                            filtered_hit["client_crash_date"])
            install_age = datetime.timedelta(0, filtered_hit["install_age"])
            install_time = client_crash_date - install_age
            filtered_hit["install_time"] = install_time.strftime(
                                                        "%Y-%m-%d %H:%M:%S.%f")

            filtered_hits.append(filtered_hit)

        results = {
            "total": total,
            "hits": filtered_hits
        }

        return results
