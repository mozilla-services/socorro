import json
import logging

import elasticsearch as es
import socorro.services.versions_info as vi

logger = logging.getLogger("webapi")


class Search(es.Search):

    """
    Implement the /search service with ElasticSearch.

    """

    def search(self, **kwargs):
        """
        Search for crashes and return them.

        See https://wiki.mozilla.org/Socorro/Middleware#Search

        Keyword arguments:
        type -- Type of data to return. Can be "crashes" or "signatures".

        Optional arguments: see socorro.external.common.Common.get_parameters
        """
        params = Search.get_parameters(kwargs)

        # Get information about the versions
        versions_service = vi.VersionsInfo(self.context)
        params["versions_info"] = versions_service.versions_info(params)

        query = Search.build_query_from_params(params)

        # For signatures mode, we need to collect more data with facets
        types = params["type"]
        if types == "signatures":
            # No need to get crashes, we only want signatures
            query["size"] = 0
            query["from"] = 0

            # Using a fixed number instead of the needed number.
            # This hack limits the number of distinct signatures to process,
            # and hugely improves performances with long queries.
            query["facets"] = Search.get_signatures_facet(
                            self.context.searchMaxNumberOfDistinctSignatures)

        json_query = json.dumps(query)
        logger.debug("Query the crashes or signatures: %s", json_query)

        es_result = self.query(params["from_date"],
                               params["to_date"],
                               json_query)

        # Executing the query and returning the result
        if types != "signatures":
            return es_result
        else:
            try:
                es_data = json.loads(es_result[0])
            except Exception:
                logger.debug("ElasticSearch returned something wrong: %s",
                             es_result[0])
                raise

            # Making sure we have a real result before using it
            if not es_data:
                signature_count = 0
            else:
                signature_count = len(es_data["facets"]["signatures"]["terms"])

            maxsize = min(signature_count,
                          params["result_number"] + params["result_offset"])

            if maxsize > params["result_offset"]:
                signatures = Search.get_signatures(
                                                es_data["facets"],
                                                maxsize,
                                                self.context.platforms)

                count_by_os_query = query
                facets = Search.get_count_facets(
                                            signatures,
                                            params["result_offset"],
                                            maxsize)
                count_by_os_query["facets"] = facets
                count_by_os_query_json = json.dumps(count_by_os_query)
                logger.debug("Query the OS by signature: %s",
                             count_by_os_query_json)

                count_result = self.query(params["from_date"],
                                          params["to_date"],
                                          count_by_os_query_json)
                try:
                    count_data = json.loads(count_result[0])
                except Exception:
                    logger.debug("ElasticSearch returned something wrong: %s",
                                 count_result[0])
                    raise

                count_sign = count_data["facets"]
                signatures = Search.get_counts(
                                                signatures,
                                                count_sign,
                                                params["result_offset"],
                                                maxsize,
                                                self.context.platforms)

            results = {
                "total": signature_count,
                "hits": []
            }

            for i in xrange(params["result_offset"], maxsize):
                results["hits"].append(signatures[i])

            return results
