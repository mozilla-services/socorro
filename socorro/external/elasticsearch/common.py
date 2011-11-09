import logging

from datetime import timedelta, datetime

import socorro.lib.datetimeutil as dtutil
import socorro.lib.httpclient as httpc
import socorro.lib.util as util

logger = logging.getLogger("webapi")


class ElasticSearchCommon(object):

    """
    Base class for ElasticSearch based service implementations.
    """

    def __init__(self, config):
        """
        Default constructor
        """
        self.http = httpc.HttpClient(config.elasticSearchHostname,
                                     config.elasticSearchPort)

        # A simulation of cache, good enough for the current needs,
        # but wouldn't mind to be replaced.
        self.cache = {}

    def query(self, from_date, to_date, json_query):
        """
        Send a query directly to ElasticSearch and return the result.
        """
        # Default dates
        now = datetime.today()
        lastweek = now - timedelta(7)

        from_date = dtutil.string_to_datetime(from_date) or lastweek
        to_date = dtutil.string_to_datetime(to_date) or now

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

    @staticmethod
    def build_query_from_params(params):
        """
        Build and return an ES query given a list of parameters.

        See socorro.lib.search_common.SearchCommon.get_parameters() for
        parameters and default values.

        """
        # Dates need to be strings for ES
        params["from_date"] = dtutil.date_to_string(
                                                    params["from_date"])
        params["to_date"] = dtutil.date_to_string(params["to_date"])

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
                            ElasticSearchCommon.build_terms_query(
                                params["fields"],
                                util.lower(params["terms"])))

        elif params["terms"]:
            params["terms"] = ElasticSearchCommon.prepare_terms(
                                                    params["terms"],
                                                    params["search_mode"])
            queries.append(ElasticSearchCommon.build_wildcard_query(
                                                params["fields"],
                                                params["terms"]))

        # Generating the filters
        if params["products"]:
            filters["and"].append(
                            ElasticSearchCommon.build_terms_query(
                                "product.full",
                                params["products"]))
        if params["os"]:
            filters["and"].append(
                            ElasticSearchCommon.build_terms_query(
                                "os_name",
                                util.lower(params["os"])))
        if params["build_id"]:
            filters["and"].append(
                            ElasticSearchCommon.build_terms_query(
                                "build",
                                util.lower(params["build_id"])))
        if params["reason"]:
            filters["and"].append(
                            ElasticSearchCommon.build_terms_query(
                                "reason",
                                util.lower(params["reason"])))

        filters["and"].append({
                "range": {
                    "date_processed": {
                        "from": params["from_date"],
                        "to": params["to_date"]
                    }
                }
            })

        if params["report_process"] == "plugin":
            filters["and"].append(ElasticSearchCommon.build_terms_query(
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
            versions = ElasticSearchCommon.format_versions(params["version"])
            versions_type = type(versions)
            versions_info = params["versions_info"]

            if versions_type is str:
                # If there is already a product,don't do anything
                # Otherwise consider this as a product
                if not params["products"]:
                    filters["and"].append(
                                    ElasticSearchCommon.build_terms_query(
                                        "product",
                                        util.lower(versions)))

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
                            ElasticSearchCommon.build_terms_query(
                                                    "ReleaseChannel", "beta"))
                    # last use the right build id
                    filters["and"].append(
                            ElasticSearchCommon.build_terms_query(
                                    "build", versions_info[key]["build_id"]))
                elif (key in versions_info and
                        versions_info[key]["release_channel"]):
                    # this version is a release
                    filters["and"].append({
                        "not":
                            ElasticSearchCommon.build_terms_query(
                                    "ReleaseChannel",
                                    ["nightly", "aurora", "beta"])
                    })

                filters["and"].append(
                                ElasticSearchCommon.build_terms_query(
                                        "product",
                                        util.lower(
                                                    versions["product"])))
                filters["and"].append(
                                ElasticSearchCommon.build_terms_query(
                                        "version",
                                        util.lower(
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
                                ElasticSearchCommon.build_terms_query(
                                                    "ReleaseChannel", "beta"))
                        # last use the right build id
                        and_filter.append(
                                ElasticSearchCommon.build_terms_query(
                                    "build", versions_info[key]["build_id"]))

                    elif (key in versions_info and
                            versions_info[key]["release_channel"]):
                        # this version is a release
                        and_filter.append({
                            "not":
                                ElasticSearchCommon.build_terms_query(
                                        "ReleaseChannel",
                                        ["nightly", "aurora", "beta"])
                        })

                    and_filter.append(ElasticSearchCommon.build_terms_query(
                                            "product",
                                            util.lower(
                                                        v["product"])))
                    and_filter.append(ElasticSearchCommon.build_terms_query(
                                            "version",
                                            util.lower(
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
        Format the versions and return them.

        Separate versions parts by ":".
        Return: a string if there was only one product,
                a dict if there was only one product:version,
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
