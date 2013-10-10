# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
#import logging

import socorro.lib.datetimeutil as dtutil
import socorro.lib.httpclient as httpc

#logger = logging.getLogger("webapi")


class UnexpectedElasticsearchError(Exception):
    pass


class ElasticSearchBase(object):

    """
    Base class for ElasticSearch based service implementations.
    """

    def __init__(self, *args, **kwargs):
        """
        Store the config and create a connection to the database.

        Keyword arguments:
        config -- Configuration of the application.

        """
        self.context = kwargs.get("config")
        if 'webapi' in self.context:
            context = self.context.webapi
        else:
            # old middleware
            context = self.context
        self.config = context
        self.http = httpc.HttpClient(context.elasticSearchHostname,
                                     context.elasticSearchPort)

    def generate_list_of_indexes(self, from_date, to_date):
        """Return the list of indexes to query to access all the crash reports
        that were processed between from_date and to_date.

        The naming pattern for indexes in elasticsearch is configurable, it is
        possible to have an index per day, per week, per month...

        Parameters:
        * from_date datetime object
        * to_date datetime object
        """
        es_index = self.config.elasticsearch_index
        indexes = []

        current_date = from_date
        while current_date <= to_date:
            index = current_date.strftime(es_index)

            # Make sure no index is twice in the list
            # (for weekly or monthly indexes for example)
            if index not in indexes:
                indexes.append(index)
            current_date += datetime.timedelta(days=1)

        return indexes

    def query(self, from_date, to_date, json_query):
        """
        Send a query directly to ElasticSearch and return the result.
        """
        # Default dates
        now = dtutil.utc_now().date()
        lastweek = now - datetime.timedelta(7)

        from_date = dtutil.string_to_datetime(from_date) or lastweek
        to_date = dtutil.string_to_datetime(to_date) or now
        daterange = self.generate_list_of_indexes(from_date, to_date)

        # -
        # This code is here to avoid failing queries caused by missing
        # indexes. It should not happen on prod, but doing this makes
        # sure users will never see a 500 Error because of this eventuality.
        # -

        # Iterate until we can return an actual result and not an error
        can_return = False
        while not can_return:
            if not daterange:
                # This is probably wrong and should be raising an error instead
                http_response = "{}"
                break

            uri = "/%s/_search" % ",".join(daterange)

            with self.http:
                http_response = self.http.post(uri, json_query)

            # If there has been an error,
            # then we get a dict instead of some json.
            if isinstance(http_response, dict):
                data = http_response["error"]["data"]

                # If an index is missing,
                # try to remove it from the list of indexes and retry.
                if (http_response["error"]["code"] == 404 and
                    data.find("IndexMissingException") >= 0):
                    index = data[data.find("[[") + 2:data.find("]")]
                    daterange.remove(index)
                else:
                    error = 'Unexpected error from elasticsearch: %s'
                    raise UnexpectedElasticsearchError(error % data)
            else:
                can_return = True

        return (http_response, "text/json")

    @staticmethod
    def build_query_from_params(params, config):
        """
        Build and return an ES query given a list of parameters.

        See socorro.lib.search_common.SearchCommon.get_parameters() for
        parameters and default values.

        """
        # Dates need to be strings for ES
        params["from_date"] = dtutil.date_to_string(params["from_date"])
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
        if params["terms"] and params["search_mode"] == "default":
            filters["and"].append(
                            ElasticSearchBase.build_terms_query(
                                params["fields"],
                                [x.lower() for x in params["terms"]]))

        elif (params["terms"] and params["search_mode"] == "is_exactly" and
              params["fields"] == ["signature"]):
            filters["and"].append(
                            ElasticSearchBase.build_terms_query(
                                            "signature.full", params["terms"]))

        elif params["terms"]:
            params["terms"] = ElasticSearchBase.prepare_terms(
                                                    params["terms"],
                                                    params["search_mode"])
            queries.append(ElasticSearchBase.build_wildcard_query(
                                                params["fields"],
                                                params["terms"]))

        # Generating the filters
        if params["products"]:
            filters["and"].append(
                            ElasticSearchBase.build_terms_query("product.full",
                                                        params["products"]))
        if params["os"]:
            filters["and"].append(
                            ElasticSearchBase.build_terms_query("os_name",
                                    [x.lower() for x in params["os"]]))
        if params["build_ids"]:
            filters["and"].append(
                            ElasticSearchBase.build_terms_query("build",
                                                        params["build_ids"]))
        if params["reasons"]:
            filters["and"].append(
                            ElasticSearchBase.build_terms_query("reason",
                                    [x.lower() for x in params["reasons"]]))
        if params["release_channels"]:
            filters["and"].append(
                ElasticSearchBase.build_terms_query(
                    "release_channel",
                    [x.lower() for x in params["release_channels"]]
                )
            )

        # plugins filter
        if params['plugin_terms']:
            # change plugin field names to match what is in elasticsearch
            params['plugin_in'] = [
                'Plugin%s' % x.capitalize()
                for x in params['plugin_in']
            ]

            if params['plugin_search_mode'] == 'default':
                filters['and'].append(
                    ElasticSearchBase.build_terms_query(
                        params['plugin_in'],
                        [x.lower() for x in params['plugin_terms']]
                    )
                )
            elif (
                params['plugin_search_mode'] == 'is_exactly' and
                len(params['plugin_in']) == 1
            ):
                filters['and'].append(
                    ElasticSearchBase.build_terms_query(
                        '%s.full' % params['plugin_in'][0],
                        params['plugin_terms']
                    )
                )
            else:
                params['plugin_terms'] = ElasticSearchBase.prepare_terms(
                    params['plugin_terms'],
                    params['plugin_search_mode']
                )
                queries.append(
                    ElasticSearchBase.build_wildcard_query(
                        ['%s.full' % x for x in params['plugin_in']],
                        params['plugin_terms']
                    )
                )

        filters["and"].append({
                "range": {
                    "date_processed": {
                        "from": params["from_date"],
                        "to": params["to_date"]
                    }
                }
            })

        if params["report_process"] == "browser":
            filters["and"].append({"missing": {"field": "process_type"}})
        elif params["report_process"] in ("plugin", "content"):
            filters["and"].append(ElasticSearchBase.build_terms_query(
                                                    "process_type",
                                                    params["report_process"]))

        if params["report_type"] == "crash":
            filters["and"].append({"missing": {"field": "hangid"}})
        elif params["report_type"] == "hang":
            filters["and"].append({"exists": {"field": "hangid"}})

        # Generating the filters for versions
        if params["versions"]:
            versions = ElasticSearchBase.format_versions(params["versions"])
            versions_info = params["versions_info"]

            # There are several pairs product:version
            or_filter = []
            for v in versions:
                if not v["version"]:
                    continue

                and_filter = []
                channel = None
                key = ":".join((v["product"], v["version"]))
                if key in versions_info:
                    version_info = versions_info[key]
                    if version_info["release_channel"]:
                        channel = version_info["release_channel"].lower()

                if channel and channel.startswith(tuple(config.channels)):
                    # this version is not a release
                    # first use the major version instead
                    v["version"] = versions_info[key]["major_version"]
                    # then make sure it's in the right release channel
                    and_filter.append(
                        ElasticSearchBase.build_terms_query(
                            "release_channel",
                            channel
                        )
                    )

                    if channel.startswith(tuple(config.restricted_channels)):
                        # if it's a beta, verify the build id
                        and_filter.append(
                            ElasticSearchBase.build_terms_query(
                                "build",
                                versions_info[key]["build_id"]
                            )
                        )

                elif channel:
                    # this version is a release
                    and_filter.append({
                        "not":
                            ElasticSearchBase.build_terms_query(
                                    "release_channel",
                                    config.channels)
                    })

                and_filter.append(ElasticSearchBase.build_terms_query(
                                        "product", v["product"].lower()))
                and_filter.append(ElasticSearchBase.build_terms_query(
                                        "version", v["version"].lower()))
                or_filter.append({"and": and_filter})

            if or_filter:
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

        if isinstance(terms, list):
            query_type = "terms"
        else:
            query_type = "term"

        query = {
            query_type: {}
        }

        if isinstance(fields, list):
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

        if isinstance(fields, list):
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
        Return a list of dicts.

        Example 1:
            ["Firefox:10.0a1"]
            =>
            [
                {
                    "product": "Firefox",
                    "version": "10.0a1"
                }
            ]

        """
        if not versions:
            return None

        versions_list = []

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

        return versions_list

    @staticmethod
    def prepare_terms(terms, search_mode):
        """
        Prepare the list of terms by adding wildcard where needed,
        depending on the search mode.
        """
        if search_mode == "contains":
            terms = "*%s*" % " ".join(terms)
        elif search_mode == "starts_with":
            terms = "%s*" % " ".join(terms)
        elif search_mode == "is_exactly":
            terms = " ".join(terms)
        return terms
