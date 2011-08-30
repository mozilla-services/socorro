import json
import logging
import urllib

from datetime import timedelta, datetime

import socorro.lib.httpclient as httpc
import socorro.services.versions_info as vi
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
        self.http = httpc.HttpClient(config.elasticSearchHostname,
                                     config.elasticSearchPort)

        # A simulation of cache, good enough for the current needs,
        # but wouldn't mind to be replaced.
        self.cache = {}

    def query(self, from_date, to_date, json_query):
        """
        Send a query directly to ElasticSearch and return the result.
        See https://wiki.mozilla.org/Socorro/ElasticSearch_API#Query

        """
        # Default dates
        now = datetime.today()
        lastweek = now - timedelta(7)

        from_date = ElasticSearchAPI.format_date(from_date) or lastweek
        to_date = ElasticSearchAPI.format_date(to_date) or now

        # Create the indexes to use for querying.
        daterange = []
        delta_day = to_date - from_date
        for delta in xrange(0, delta_day.days + 1):
            day = from_date + timedelta(delta)
            index = "socorro_%s" % day.strftime("%y%m%d")
            # Cache protection for limitating the number of HTTP calls
            if index not in self.cache or not self.cache[index]:
                daterange.append(index)

        can_return = False

        # -
        # This code is here to avoid failing queries caused by missing
        # indexes. It should not happen on prod, but doing this makes
        # sure users will never see a 500 Error because of this
        # eventuality.
        # -

        # Iterate until we can return an actual result and not an error
        while not can_return:
            if not daterange:
                http_response = "{}"
                break

            datestring = ",".join(daterange)
            uri = "/%s/_search" % datestring

            with self.http:
                http_response = self.http.post(uri, json_query)

            # If there has been an error,
            # then we get a dict instead of some json.
            if type(http_response) is dict:
                data = http_response["error"]["data"]

                # If an index is missing,
                # try to remove it from the list of indexes and retry.
                if (http_response["error"]["code"] == 404 and
                    data.find("IndexMissingException") >= 0):
                    index = data[data.find("[[") + 2:data.find("]")]

                    # Cache protection for limitating the number of HTTP calls
                    self.cache[index] = True

                    try:
                        daterange.remove(index)
                    except Exception:
                        raise
            else:
                can_return = True

        return (http_response, "text/json")

    def search(self, types, **kwargs):
        """
        Search for crashes and return them.
        See https://wiki.mozilla.org/Socorro/ElasticSearch_API#Search

        Keyword arguments:
        types -- Type of data to return. Can be "crashes" or "signatures".

        Optional arguments: see SearchAPI.get_parameters
        """
        params = ElasticSearchAPI.get_parameters(kwargs)

        # Get information about the versions
        versions_service = vi.VersionsInfo(self.context)
        params["versions_info"] = versions_service.versions_info(params)

        query = ElasticSearchAPI.build_query_from_params(params)

        # For signatures mode, we need to collect more data with facets
        if types == "signatures":
            # No need to get crashes, we only want signatures
            query["size"] = 0
            query["from"] = 0

            # Using a fixed number instead of the needed number.
            # This hack limits the number of distinct signatures to process,
            # and hugely improves performances with long queries.
            query["facets"] = ElasticSearchAPI.get_signatures_facet(
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
                signatures = ElasticSearchAPI.get_signatures(
                                                es_data["facets"],
                                                maxsize,
                                                self.context.platforms)

                count_by_os_query = query
                facets = ElasticSearchAPI.get_count_facets(
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
                signatures = ElasticSearchAPI.get_counts(
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

    @staticmethod
    def build_query_from_params(params):
        """
        Build and return an ES query given a list of parameters.
        See searchUtil.get_parameters for parameters and default values.

        """
        # Dates need to be strings for ES
        params["from_date"] = ElasticSearchAPI.date_to_string(
                                                    params["from_date"])
        params["to_date"] = ElasticSearchAPI.date_to_string(params["to_date"])

        # Preparing the different elements of the json query
        query = {
            "match_all": {}
        }
        queries = []

        filters = {
            "and": []
        }

        # Creating the terms depending on the way we should search
        if (params["search_mode"] == "default" and
            params["terms"] and params["fields"]):
            filters["and"].append(
                            ElasticSearchAPI.build_terms_query(
                                params["fields"],
                                ElasticSearchAPI.lower(params["terms"])))

        elif params["terms"]:
            params["terms"] = ElasticSearchAPI.prepare_terms(
                                                    params["terms"],
                                                    params["search_mode"])
            queries.append(ElasticSearchAPI.build_wildcard_query(
                                                params["fields"],
                                                params["terms"]))

        # Generating the filters
        if params["products"]:
            filters["and"].append(
                            ElasticSearchAPI.build_terms_query(
                                "product",
                                ElasticSearchAPI.lower(params["products"])))
        if params["os"]:
            filters["and"].append(
                            ElasticSearchAPI.build_terms_query(
                                "os_name",
                                ElasticSearchAPI.lower(params["os"])))
        if params["build_id"]:
            filters["and"].append(
                            ElasticSearchAPI.build_terms_query(
                                "build",
                                ElasticSearchAPI.lower(params["build_id"])))
        if params["reason"]:
            filters["and"].append(
                            ElasticSearchAPI.build_terms_query(
                                "reason",
                                ElasticSearchAPI.lower(params["reason"])))

        filters["and"].append({
                "range": {
                    "date_processed": {
                        "from": params["from_date"],
                        "to": params["to_date"]
                    }
                }
            })

        if params["report_process"] == "plugin":
            filters["and"].append(ElasticSearchAPI.build_terms_query(
                                                        "process_type",
                                                        "plugin"))
        if params["report_type"] == "crash":
            filters["and"].append({"missing": {"field": "hangid"}})
        if params["report_type"] == "hang":
            filters["and"].append({"exists": {"field": "hangid"}})
        if params["report_process"] == "browser":
            filters["and"].append({"missing": {"field": "process_type"}})

        # Generating the filters for versions
        if params["version"]:
            versions = ElasticSearchAPI.format_versions(params["version"])
            versions_type = type(versions)
            versions_info = params["versions_info"]

            if versions_type is str:
                # If there is already a product,don't do anything
                # Otherwise consider this as a product
                if not params["products"]:
                    filters["and"].append(
                                    ElasticSearchAPI.build_terms_query(
                                        "product",
                                        ElasticSearchAPI.lower(versions)))

            elif versions_type is dict:
                # There is only one pair product:version
                key = ":".join((versions["product"], versions["version"]))

                if (key in versions_info and
                        versions_info[key]["release_channel"] == "Beta"):
                    # this version is a beta
                    # first use the major version instead
                    versions["version"] = versions_info[key]["major_version"]
                    # then make sure it's a beta
                    filters["and"].append(
                            ElasticSearchAPI.build_terms_query(
                                                    "ReleaseChannel", "beta"))
                    # last use the right build id
                    filters["and"].append(
                            ElasticSearchAPI.build_terms_query(
                                    "build", versions_info[key]["build_id"]))
                elif (key in versions_info and
                        versions_info[key]["release_channel"]):
                    # this version is a release
                    filters["and"].append({
                        "not":
                            ElasticSearchAPI.build_terms_query(
                                    "ReleaseChannel",
                                    ["nightly", "aurora", "beta"])
                    })

                filters["and"].append(
                                ElasticSearchAPI.build_terms_query(
                                        "product",
                                        ElasticSearchAPI.lower(
                                                    versions["product"])))
                filters["and"].append(
                                ElasticSearchAPI.build_terms_query(
                                        "version",
                                        ElasticSearchAPI.lower(
                                                    versions["version"])))

            elif versions_type is list:
                # There are several pairs product:version
                or_filter = []
                for v in versions:
                    and_filter = []
                    key = ":".join((v["product"], v["version"]))

                    if (key in versions_info and
                            versions_info[key]["release_channel"] == "Beta"):
                        # this version is a beta
                        # first use the major version instead
                        v["version"] = versions_info[key]["major_version"]
                        # then make sure it's a beta
                        and_filter.append(
                                ElasticSearchAPI.build_terms_query(
                                                    "ReleaseChannel", "beta"))
                        # last use the right build id
                        and_filter.append(
                                ElasticSearchAPI.build_terms_query(
                                    "build", versions_info[key]["build_id"]))

                    elif (key in versions_info and
                            versions_info[key]["release_channel"]):
                        # this version is a release
                        and_filter.append({
                            "not":
                                ElasticSearchAPI.build_terms_query(
                                        "ReleaseChannel",
                                        ["nightly", "aurora", "beta"])
                        })

                    and_filter.append(ElasticSearchAPI.build_terms_query(
                                            "product",
                                            ElasticSearchAPI.lower(
                                                        v["product"])))
                    and_filter.append(ElasticSearchAPI.build_terms_query(
                                            "version",
                                            ElasticSearchAPI.lower(
                                                        v["version"])))
                    or_filter.append({"and": and_filter})
                filters["and"].append({"or": or_filter})

        if len(queries) > 1:
            query = {
                "bool": {
                    "must": queries
                }
            }
        elif len(queries) == 1:
            query = queries[0]

        # Generating the full query from the parts
        return {
            "size": params["result_number"],
            "from": params["result_offset"],
            "query": {
                "filtered": {
                    "query": query,
                    "filter": filters
                }
            }
        }

    @staticmethod
    def build_terms_query(fields, terms):
        """
        Build and return an object containing a term or terms query
        for ElasticSearch.

        """
        if not terms or not fields:
            return None

        if type(terms) is list:
            query_type = "terms"
        else:
            query_type = "term"

        query = {
            query_type: {}
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
        Build and return an object containing a wildcard query
        for ElasticSearch.

        """
        if not terms or not fields:
            return None

        wildcard_query = {
            "wildcard": {}
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
        Format the versions, separating by ":".
        Return a string if there was only one product,
                a dict if there was only one product:versionm
                a list of dicts if there was several product:version.

        """
        if not versions:
            return None

        versions_list = []

        if type(versions) is list:
            for v in versions:
                try:
                    (product, version) = v.split(":")
                except ValueError:
                    product = v
                    version = None

                versions_list.append({
                    "product": product,
                    "version": version
                })
        else:
            try:
                (product, version) = versions.split(":")
            except ValueError:
                product = versions
                version = None

            if version:
                versions_list = {
                    "product": product,
                    "version": version
                }
            else:
                versions_list = product

        return versions_list

    @staticmethod
    def prepare_terms(terms, search_mode):
        """
        Prepare the list of terms by adding wildcard where needed,
        depending on the search mode.

        """
        if type(terms) is list:
            if search_mode == "contains":
                terms = "".join(("*", " ".join(terms), "*"))
            elif search_mode == "starts_with":
                terms = "".join((" ".join(terms), "*"))
            elif search_mode == "is_exactly":
                terms = " ".join(terms)
        elif search_mode == "contains":
            terms = "".join(("*", terms, "*"))
        elif search_mode == "starts_with":
            terms = "".join((terms, "*"))

        return terms
