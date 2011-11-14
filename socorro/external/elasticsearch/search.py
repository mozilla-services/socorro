import json
import logging

from socorro.external.elasticsearch.base import ElasticSearchBase

import socorro.lib.search_common as scommon
import socorro.services.versions_info as vi

logger = logging.getLogger("webapi")


class Search(ElasticSearchBase):

    """
    Implement the /search service with ElasticSearch.
    """

    def __init__(self, **kwargs):
        """
        Default constructor
        """
        super(Search, self).__init__(**kwargs)

    def search(self, **kwargs):
        """
        Search for crashes and return them.

        See http://socorro.readthedocs.org/en/latest/middleware.html#search

        Optional arguments: see SearchCommon.get_parameters()

        """
        params = scommon.get_parameters(kwargs)

        # Get information about the versions
        versions_service = vi.VersionsInfo(self.context)
        params["versions_info"] = versions_service.versions_info(params)

        query = Search.build_query_from_params(params)

        # For signatures mode, we need to collect more data with facets
        if params["data_type"] == "signatures":
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
        if params["data_type"] == "signatures":
            return self.search_for_signatures(params, es_result, query)
        else:
            return es_result

    def search_for_signatures(self, params, es_result, query):
        """
        """
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
            signatures = Search.get_signatures(es_data["facets"], maxsize,
                                               self.context.platforms)

            count_by_os_query = query
            facets = Search.get_count_facets(signatures,
                                             params["result_offset"],
                                             maxsize)
            count_by_os_query["facets"] = facets
            count_by_os_query_json = json.dumps(count_by_os_query)
            logger.debug("Query the OS by signature: %s",
                         count_by_os_query_json)

            count_result = self.query(params["from_date"], params["to_date"],
                                      count_by_os_query_json)
            try:
                count_data = json.loads(count_result[0])
            except Exception:
                logger.debug("ElasticSearch returned something wrong: %s",
                             count_result[0])
                raise

            count_sign = count_data["facets"]
            signatures = Search.get_counts(signatures, count_sign,
                                            params["result_offset"], maxsize,
                                            self.context.platforms)

        results = {
            "total": signature_count,
            "hits": []
        }

        for i in xrange(params["result_offset"], maxsize):
            results["hits"].append(signatures[i])

        return results

    @staticmethod
    def get_signatures_facet(size):
        """
        Generate the facets for the search query.
        """
        # Get distinct signatures and count
        facets = {
            "signatures": {
                "terms": {
                    "field": "signature.full",
                    "size": size
                }
            }
        }

        return facets

    @staticmethod
    def get_signatures(facets, maxsize, platforms):
        """
        Generate the result of search by signature from the facets ES returns.
        """
        signatures = facets["signatures"]["terms"]

        results = []
        sign_list = {}

        for i in xrange(maxsize):
            results.append({
                "signature": signatures[i]["term"],
                "count": signatures[i]["count"]
            })
            for platform in platforms:
                results[i]["_".join(("is", platform["id"]))] = 0

            sign_list[signatures[i]["term"]] = results[i]

        return results

    @staticmethod
    def get_count_facets(signatures, result_offset, maxsize):
        """
        Generate the facets to count the number of each OS for each signature.
        """
        facets = {}

        for i in xrange(result_offset, maxsize):
            sign = signatures[i]["signature"]
            sign_hang = "_".join((sign, "hang"))
            sign_plugin = "_".join((sign, "plugin"))

            facet_filter = {
                "term": {
                    "signature.full": sign
                }
            }

            facets[sign] = {
                "terms": {
                    "field": "os_name"
                },
                "facet_filter": facet_filter
            }
            facets[sign_hang] = {
                "filter": {
                    "exists": {
                        "field": "hangid"
                    }
                },
                "facet_filter": facet_filter
            }
            facets[sign_plugin] = {
                "filter": {
                    "exists": {
                        "field": "process_type"
                    }
                },
                "facet_filter": facet_filter
            }

        return facets

    @staticmethod
    def get_counts(signatures, count_sign, result_offset, maxsize, platforms):
        """
        Generate the complementary information about signatures
        (count by OS, number of plugins and of hang).
        """
        # Transform the results into something we can return
        for i in xrange(result_offset, maxsize):
            # OS count
            for term in count_sign[signatures[i]["signature"]]["terms"]:
                for os in platforms:
                    if term["term"] == os["id"]:
                        osid = "is_%s" % os["id"]
                        signatures[i][osid] = term["count"]
            # Hang count
            sign_hang = "_".join((signatures[i]["signature"], "hang"))
            signatures[i]["numhang"] = count_sign[sign_hang]["count"]
            # Plugin count
            sign_plugin = "_".join((signatures[i]["signature"], "plugin"))
            signatures[i]["numplugin"] = count_sign[sign_plugin]["count"]
        return signatures
