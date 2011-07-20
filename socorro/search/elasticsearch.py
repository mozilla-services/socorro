import json
import logging
import urllib

from datetime import timedelta, datetime

import socorro.lib.datetimeutil as dtutil
import socorro.lib.httpclient as httpc
import socorro.lib.util as util
import searchapi as sapi

logger = logging.getLogger("webapi")


class ElasticSearchAPI(sapi.SearchAPI):
    """
    Implements the search API using ElasticSearch.
    See https://wiki.mozilla.org/Socorro/ElasticSearch_API

    """

    def __init__(self, config):
        """
        Default constructor

        """
        super(ElasticSearchAPI, self).__init__(config)
        self.http = httpc.HttpClient(config.elasticSearchHostname, config.elasticSearchPort)

    def query(self, types, jsonQuery):
        """
        Send a query directly to ElasticSearch and return the result.
        See https://wiki.mozilla.org/Socorro/ElasticSearch_API#Query

        """
        uri = "/socorro/_search"

        with self.http:
            httpResponse = self.http.post(uri, jsonQuery)

        return ( httpResponse, "text/json" )

    def search(self, types, **kwargs):
        """
        Search for crashes and return them.
        See https://wiki.mozilla.org/Socorro/ElasticSearch_API#Search

        Keyword arguments:
        types -- Type of data to return. Can be "crashes" or "signatures".

        Optional arguments: see SearchAPI.get_parameters
        """
        params = ElasticSearchAPI.get_parameters(kwargs)
        query = ElasticSearchAPI.build_query_from_params(params)

        # For signatures mode, we need to collect more data with facets
        if types == "signatures":
            # No need to get crashes, we only want signatures
            query["size"] = 0
            query["from"] = 0
            query["facets"] = self.generate_signatures_facet(params["result_offset"] + params["result_number"])

        json_query = json.dumps(query)

        print json_query

        logger.debug("Query the crashes or signatures: %s" % json_query)

        # Executing the query and returning the result
        if types != "signatures":
            return self.query("_all", json_query)
        else:
            es_result = self.query("_all", json_query)
            try:
                es_data = json.loads(es_result[0])
            except Exception:
                logger.debug("ElasticSearch returned something wrong: %s" % es_result[0])
                raise

            signature_count = len(es_data["facets"]["signatures"]["terms"])
            maxsize = min(signature_count, params["result_number"] + params["result_offset"])

            signatures = self.generate_signatures_from_facet_results(es_data["facets"], maxsize)

            # If there are results for this page
            if maxsize > params["result_offset"]:
                count_by_os_query = query
                count_by_os_query["facets"] = self.generate_count_by_signatures_os_facets(signatures, params["result_offset"], maxsize)
                count_by_os_query_json = json.dumps(count_by_os_query)
                logger.debug("Query the OS by signature: %s" % count_by_os_query_json)

                count_result = self.query("_all", count_by_os_query_json)
                try:
                    count_data = json.loads(count_result[0])
                except Exception:
                    logger.debug("ElasticSearch returned something wrong: %s" % count_result[0])
                    raise

                count_sign = count_data["facets"]

                # Transform the results into something we can return
                for i in xrange(params["result_offset"], maxsize):
                    # OS count
                    for term in count_sign[signatures[i]["signature"]]["terms"]:
                        for os in self.context.platforms:
                            if term["term"] == os["id"]:
                                signatures[i]["is_"+os["id"]] = term["count"]
                    # Hang count
                    sign_hang = "_".join((signatures[i]["signature"], "hang"))
                    signatures[i]["numhang"] = count_sign[sign_hang]["count"]
                    # Plugin count
                    sign_plugin = "_".join((signatures[i]["signature"], "plugin"))
                    signatures[i]["numplugin"] = count_sign[sign_plugin]["count"]

            results = {
                "total" : signature_count,
                "hits" : []
            }

            for i in xrange(params["result_offset"], maxsize):
                results["hits"].append(signatures[i])

            return results

    def report(self, name, **kwargs):
        """
        Not implemented yet.

        """
        if name == "top_crashers_by_signature":
            return self.report_top_crashers_by_signature(kwargs)

    def report_top_crashers_by_signature(self, kwargs):
        """
        Not implemented yet.

        """
        return None

    def generate_signatures_facet(self, size):
        """
        Generate the facets for the search query.

        """
        # There is no way to get all the results with ES,
        # and we need them to count the total.
        MAXINT = 2**31-1

        # Get distinct signatures and count
        facets = {
            "signatures" : {
                "terms" : {
                    "field" : "signature.full",
                    "size" : MAXINT
                }
            }
        }

        return facets

    def generate_signatures_from_facet_results(self, facets, maxsize):
        """
        Generate the result of search by signature from the facets ES returns.

        """
        signatures = facets["signatures"]["terms"]

        results = []
        sign_list = {}

        for i in xrange(maxsize):
            results.append({
                "signature" : signatures[i]["term"],
                "count" : signatures[i]["count"]
            })
            for platform in self.context.platforms:
                results[i][ "_".join(("is", platform["id"])) ] = 0

            sign_list[ signatures[i]["term"] ] = results[i]

        return results

    def generate_count_by_signatures_os_facets(self, signatures, result_offset, maxsize):
        """
        Generate the facets to count the appearance in each OS for each signature.

        """
        facets = {}

        for i in xrange(result_offset, maxsize):
            sign = signatures[i]["signature"]
            sign_hang = "_".join((sign, "hang"))
            sign_plugin = "_".join((sign, "plugin"))

            facet_filter = {
                "term" : {
                    "signature.full" : sign
                }
            }

            facets[sign] = {
                "terms" : {
                    "field" : "os_name"
                },
                "facet_filter" : facet_filter
            }
            facets[sign_hang] = {
                "query" : {
                    "query_string" : {
                        "query" : "_exists_:hangid"
                    }
                },
                "facet_filter" : facet_filter
            }
            facets[sign_plugin] = {
                "query" : {
                    "query_string" : {
                        "query" : "_exists_:process_type"
                    }
                },
                "facet_filter" : facet_filter
            }

        return facets

    @staticmethod
    def build_query_from_params(params):
        """
        Build and return an ES query given a list of parameters.
        See searchUtil.get_parameters for parameters and default values.

        """
        # Dates need to be strings for ES
        params["from_date"] = ElasticSearchAPI.date_to_string(params["from_date"])
        params["to_date"] = ElasticSearchAPI.date_to_string(params["to_date"])

        # Preparing the different elements of the json query
        query = {
            "match_all" : {}
        }
        queries = []

        filters = {
            "and" : []
        }

        query_string = {
            "query" : None,
            "allow_leading_wildcard" : False
        }

        # Creating the terms depending on the way we should search
        if params["search_mode"] == "default" and params["terms"] and params["fields"]:
            filters["and"].append(ElasticSearchAPI.build_terms_query(params["fields"], ElasticSearchAPI.lower(params["terms"])))

        elif params["terms"]:
            params["terms"] = ElasticSearchAPI.prepare_terms(params["terms"], params["search_mode"])
            queries.append(ElasticSearchAPI.build_wildcard_query(params["fields"], params["terms"]))

        # Generating the filters
        if params["products"]:
            filters["and"].append(ElasticSearchAPI.build_terms_query("product", ElasticSearchAPI.lower(params["products"])))
        if params["os"]:
            filters["and"].append(ElasticSearchAPI.build_terms_query("os_name", ElasticSearchAPI.lower(params["os"])))
        if params["build_id"]:
            filters["and"].append(ElasticSearchAPI.build_terms_query("build", ElasticSearchAPI.lower(params["build_id"])))
        if params["reason"]:
            filters["and"].append(ElasticSearchAPI.build_terms_query("reason", ElasticSearchAPI.lower(params["reason"])))

        filters["and"].append({
                "range" : {
                    "client_crash_date" : {
                        "from" : params["from_date"],
                        "to" : params["to_date"]
                    }
                }
            })

        if params["report_process"] == "plugin":
            filters["and"].append(ElasticSearchAPI.build_terms_query("process_type", "plugin"))

        # Generating the query_string using special functions like _missing_ and _exists_
        query_string_list = []
        if params["version"]:
            #-----
            # TODO: This should be written using filters instead of being in the query_string
            #-----
            query_string_list.append(ElasticSearchAPI.format_versions(params["version"]))
        if params["report_type"] == "crash":
            query_string_list.append("_missing_:hangid")
        if params["report_type"] == "hang":
            query_string_list.append("_exists_:hangid")
        if params["report_process"] == "browser":
            query_string_list.append("_missing_:process_type")

        query_string["query"] = " AND ".join(query_string_list)

        if query_string["query"]:
            queries.append({ "query_string" : query_string })

        if len(queries) > 1:
            query = {
                "bool" : {
                    "must" : queries
                }
            }
        elif len(queries) == 1:
            query = queries[0]

        # Generating the full query from the parts
        return {
            "size" : params["result_number"],
            "from" : params["result_offset"],
            "query" : {
                "filtered" : {
                    "query" : query,
                    "filter" : filters
                }
            }
        }

    @staticmethod
    def build_terms_query(fields, terms):
        """
        Build and return an object containing a term or terms query for ElasticSearch.

        """
        if not terms or not fields:
            return None

        if type(terms) is list:
            query_type = "terms"
        else:
            query_type = "term"

        query = {
            query_type : {}
        }

        if type(fields) is list:
            for field in fields:
                query[query_type][field] = terms
        else:
            query[query_type][fields] = terms

        return query

    @staticmethod
    def build_wildcard_query(fields, terms):
        """
        Build and return an object containing a wildcard query for ElasticSearch.

        """
        if not terms or not fields:
            return None

        wildcard_query = {
            "wildcard" : {}
        }

        if type(fields) is list:
            for i in fields:
                if i == "signature":
                    i = "signature.full"
                wildcard_query["wildcard"][i] = terms
        else:
            if fields == "signature":
                fields = "signature.full"
            wildcard_query["wildcard"][fields] = terms

        return wildcard_query

    @staticmethod
    def format_versions(versions):
        """
        Format the versions, separating by ":" and returning the query_string.

        """
        if not versions:
            return None

        formatted_versions = ""

        if type(versions) is list:
            versions_list = []

            for v in versions:
                if v.find(":") != -1:
                    product_version = v.split(":")
                    product = product_version[0]
                    version = product_version[1]
                    versions_list.append( "".join( ("( product: ", urllib.quote(product), " AND version: ", urllib.quote(version), " )") ) )
                else:
                    versions_list.append( "".join( ( "product: ", urllib.quote(v) ) ) )

            formatted_versions = "".join( ( "(", ElasticSearchAPI.array_to_string(versions_list, " OR "), ")" ) )
        else:
            if versions.find(":") != -1:
                product_version = versions.split(":")
                product = product_version[0]
                version = product_version[1]
                formatted_versions = "".join( ("( product: ", urllib.quote(product), " AND version: ", urllib.quote(version), " )") )
            else:
                formatted_versions = "".join( ( "product: ", urllib.quote(versions) ) )

        return formatted_versions

    @staticmethod
    def prepare_terms(terms, search_mode):
        """
        Prepare the list of terms by adding wildcard where needed,
        depending on the search mode.

        """
        if type(terms) is list:
            if search_mode == "contains":
                terms = "".join( ( "*", " ".join(terms), "*" ) )
            elif search_mode == "starts_with":
                terms = "".join( ( " ".join(terms), "*" ) )
            elif search_mode == "is_exactly":
                terms = " ".join(terms)
        elif search_mode == "contains":
            terms = "".join( ( "*", terms, "*" ) )
        elif search_mode == "starts_with":
            terms = "".join( ( terms, "*" ) )

        return terms
