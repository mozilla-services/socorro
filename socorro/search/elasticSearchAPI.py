import json
import logging
import searchAPI
import sys
import urllib

from datetime import timedelta, datetime

import socorro.lib.datetimeutil as dtutil
import socorro.lib.httpClient as httpc
import socorro.lib.util as util

logger = logging.getLogger("webapi")


class ElasticSearchAPI(searchAPI.SearchAPI):
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

        Optional arguments:
        for -- Terms to search for. Can be a string or a list of strings.
        product -- Products concerned by this search. Can be a string or a list of strings.
        from -- Only elements after this date. Format must be "YYYY-mm-dd HH:ii:ss.S"
        to -- Only elements before this date. Format must be "YYYY-mm-dd HH:ii:ss.S"
        in -- Fields to search into. Can be a string or a list of strings. Default to all fields.
        os -- Limit search to those operating systems. Can be a string or a list of strings. Default to all OS.
        version -- Version of the software. Can be a string or a list of strings. Default to all versions.
        build -- Limit search to this particular build of the software. Must be a string. Default to all builds.
        search_mode -- How to search for terms. Must be one of the following: "default", "contains", "is_exactly" or "starts_with". Default to "default".
        crash_reason --  Restricts search to crashes caused by this reason. Default value is empty.

        """

        # Default dates
        now = datetime.today()
        lastWeek = now - timedelta(7)

        # Getting parameters that have default values
        terms       = kwargs.get("for", "_all")
        products    = kwargs.get("product", "firefox")
        from_date   = kwargs.get("from", lastWeek)
        to_date     = kwargs.get("to", now)
        fields      = kwargs.get("in", "_all")
        os          = kwargs.get("os", "_all")
        version     = kwargs.get("version", "_all")
        #branches   = kwargs.get("branches", "_all")    # Not implemented
        build_id    = kwargs.get("build", None)
        reason      = kwargs.get("crash_reason", None)
        report_type = kwargs.get("report_type", None)

        search_mode = kwargs.get("search_mode", "default")
        result_number = int( kwargs.get("result_number", 100) )
        result_offset = int( kwargs.get("result_offset", 0) )

        # Handling dates
        from_date = self._formatDate(from_date)
        to_date = self._formatDate(to_date)

        from_date = self._dateToString(from_date)
        to_date = self._dateToString(to_date)

        # Transforming arrays to strings
        if type(fields) is str and fields != "_all":
            fields = [fields]

        os = self._formatParam(os, "os_name")
        version = self._formatVersions(version)
        products = self._formatParam(products, "product")

        query = {
            "bool" : {
                "must" : [],
                "should" : []
            }
        }

        query_string = {
            "query" : products,
            "allow_leading_wildcard" : False
        }

        # Creating the terms depending on the way we should search
        if search_mode == "default" and terms != "_all" and terms != "":
            if type(terms) is not list:
                terms = (urllib.quote(terms),)
            else:
                for i in xrange(len(terms)):
                    terms[i] = urllib.quote(terms[i])

            query_string["query"] = " AND ".join( ( query_string["query"], " OR ".join(terms) ) )

            if type(fields) is list:
                query_string["fields"] =  fields
            else:
                query_string["default_field"] =  fields

        elif terms != "_all":

            wildcardQuery = {
                "wildcard" : {}
            }

            if type(terms) is list:
                if search_mode == "contains":
                    terms = "".join( ( "*", " ".join(terms), "*" ) )
                elif search_mode == "starts_with":
                    terms = "".join( ( " ".join(terms), "*" ) )
                else:
                    terms = " ".join(terms)
            elif search_mode == "contains":
                terms = "".join( ( "*", terms, "*" ) )
            elif search_mode == "starts_with":
                terms = "".join( ( terms, "*" ) )
            else:
                terms = terms

            if type(fields) is list:
                for i in fields:
                    if i == "signature":
                        i = "signature.full"
                    wildcardQuery["wildcard"][i] = terms
            else:
                if fields == "signature":
                    fields = "signature.full"
                wildcardQuery["wildcard"][fields] = terms

            query["bool"]["must"].append(wildcardQuery)

        if os != "_all":
            query_string["query"] += " AND " + os
        if version != "_all":
            query_string["query"] += " AND " + version
        if build_id:
            query_string["query"] += " AND build:" + build_id
        if reason:
            query_string["query"] += " AND reason:" + reason
        if report_type == "crash":
            query_string["query"] += " AND _missing_:hangid"
        if report_type == "hang":
            query_string["query"] += " AND _exists_:hangid"

        query["bool"]["must"].append( { "query_string" : query_string } )

        # Generating the query
        query = {
            "size" : result_number,
            "from" : result_offset,
            "query" : {
                "filtered" : {
                    "query" : query,
                    "filter" : {
                        "and" : [
                            {
                                "range" : {
                                    "client_crash_date" : {
                                        "from" : from_date,
                                        "to" : to_date
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }

        # For signatures mode, we need to collect more data with facets
        if types == "signatures":
            # No need to get crashes, we only want signatures
            query["size"] = 0
            query["from"] = 0
            query["facets"] = self._generateFacets(result_offset + result_number)

        json_query = json.dumps(query)

        logger.debug("Query the crashes or signatures: %s" % json_query)

        # Executing the query and returning the result
        if types != "signatures":
            return self.query("_all", json_query)
        else:
            esResult = self.query("_all", json_query)
            try:
                esData = json.loads(esResult[0])
            except Exception:
                logger.debug("ElasticSearch returned something wrong: %s" % esResult)
                raise

            signatureCount = len(esData["facets"]["signatures"]["terms"])
            maxSize = min(signatureCount, result_number + result_offset)

            signatures = self._generateSignaturesFromFacets(esData["facets"], maxSize)

            # If there are results for this page
            if maxSize > result_offset:
                countByOSQuery = self._generateCountByOSQuery(query, signatures, result_offset, maxSize)
                countByOSQueryJSON = json.dumps(countByOSQuery)
                logger.debug("Query the OS by signature: %s" % countByOSQueryJSON)

                countResult = self.query("_all", countByOSQueryJSON)
                try:
                    countData = json.loads(countResult[0])
                except Exception:
                    logger.debug("ElasticSearch returned something wrong: %s" % esResult)
                    raise

                countSign = countData["facets"]

                for i in xrange(result_offset, maxSize):
                    for term in countSign[signatures[i]["signature"]]["terms"]:
                        for os in self.context.platforms:
                            if term["term"] == os["id"]:
                                signatures[i]["is_"+os["id"]] = term["count"]

            results = {
                "total" : signatureCount,
                "hits" : []
            }

            for i in xrange(result_offset, maxSize):
                results["hits"].append(signatures[i])

            return results

    def _formatVersions(self, versions):
        """
        Format the versions, separating by ":" and returning the query_string.

        """
        if versions == "_all":
            return versions

        formattedVersions = ""

        if type(versions) is list:
            versionsList = []

            for v in versions:
                if v.find(":") != -1:
                    productVersion = v.split(":")
                    product = productVersion[0]
                    version = productVersion[1]
                    versionsList.append( "".join( ("( product: ", product, " AND version: ", version, " )") ) )
                else:
                    versionsList.append( "".join( ( "product: ", v ) ) )

            formattedVersions = "".join( ( "(", self._arrayToString(versionsList, " OR "), ")" ) )
        else:
            if versions.find(":") != -1:
                productVersion = versions.split(":")
                product = productVersion[0]
                version = productVersion[1]
                formattedVersions = "".join( ("( product: ", product, " AND version: ", version, " )") )
            else:
                formattedVersions = "".join( ( "product: ", v ) )

        return formattedVersions

    def _generateFacets(self, size):
        """
        Generate the facets for the search query.

        """
        # Get distinct signatures and count
        facets = {
            "signatures" : {
                "terms" : {
                    "field" : "signature.full",
                    "size" : sys.maxint
                }
            }
        }

        return facets

    def _generateSignaturesFromFacets(self, facets, maxSize):
        """
        Generate the result of search by signature from the facets ES returns.

        """
        signatures = facets["signatures"]["terms"]

        results = []
        signList = {}

        for i in xrange(maxSize):
            results.append({
                "signature" : signatures[i]["term"],
                "count" : signatures[i]["count"]
            })
            for platform in self.context.platforms:
                results[i][ "is_"+platform["id"] ] = 0

            signList[ signatures[i]["term"] ] = results[i]

        return results

    def _generateCountByOSQuery(self, query, signatures, result_offset, maxSize):
        """
        Generate the query to count the appearance in each OS for each signature.

        """
        facets = {}

        for i in xrange(result_offset, maxSize):
            sign = signatures[i]["signature"]
            facets[sign] = {
                "terms" : {
                    "field" : "os_name"
                },
                "facet_filter" : {
                    "term" : {
                        "signature.full" : sign
                    }
                }
            }

        query["facets"] = facets

        return query
