# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import logging

from socorro.external.elasticsearch.base import ElasticSearchBase
from socorro.external.postgresql.util import Util

import socorro.lib.search_common as search_common

logger = logging.getLogger("webapi")


class Search(ElasticSearchBase):

    """
    Implement the /search service with ElasticSearch.
    """

    def search(self, **kwargs):
        import warnings
        warnings.warn("Use `.get()' instead", DeprecationWarning, 2)
        return self.get(**kwargs)

    def get_signatures(self, **kwargs):
        kwargs['data_type'] = 'signatures'
        return self.get(**kwargs)

    def get_crashes(self, **kwargs):
        kwargs['data_type'] = 'crashes'
        return self.get(**kwargs)

    def get(self, **kwargs):
        """
        Search for crashes and return them.

        See http://socorro.readthedocs.org/en/latest/middleware.html#search

        Optional arguments: see SearchCommon.get_parameters()

        """
        # change aliases from the web to the implementation's need
        if "for" in kwargs and "terms" not in kwargs:
            kwargs["terms"] = kwargs.get("for")
        if "from" in kwargs and "from_date" not in kwargs:
            kwargs["from_date"] = kwargs.get("from")
        if "to" in kwargs and "to_date" not in kwargs:
            kwargs["to_date"] = kwargs.get("to")
        if "in" in kwargs and "fields" not in kwargs:
            kwargs["fields"] = kwargs.get("in")

        params = search_common.get_parameters(kwargs)

        # Get information about the versions
        versions_service = Util(config=self.context)
        params["versions_info"] = versions_service.versions_info(**params)

        # Changing the OS ids to OS names
        for i, elem in enumerate(params["os"]):
            for platform in self.config.platforms:
                if platform["id"][:3] == elem[:3]:
                    # the split is here to remove 'nt' from 'windows nt'
                    # and 'os x' from 'mac os x'
                    params["os"][i] = platform["name"].split(' ')[0]

        query = Search.build_query_from_params(params, self.config)

        # For signatures mode, we need to collect more data with facets
        if params["data_type"] == "signatures":
            # No need to get crashes, we only want signatures
            query["size"] = 0
            query["from"] = 0

            # Using a fixed number instead of the needed number.
            # This hack limits the number of distinct signatures to process,
            # and hugely improves performances with long queries.

            query["facets"] = Search.get_signatures_facet(
                self.config.searchMaxNumberOfDistinctSignatures
            )

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
        Return a list of signatures and their counts.
        """
        try:
            es_data = json.loads(es_result[0])
        except ValueError:
            logger.error("ElasticSearch returned something wrong: %s",
                         es_result[0], exc_info=True)
            raise

        # Making sure we have a real result before using it
        if not es_data:
            signature_count = 0
        else:
            signature_count = len(es_data["facets"]["signatures"]["terms"])

        maxsize = min(signature_count,
                      params["result_number"] + params["result_offset"])

        if maxsize > params["result_offset"]:
            signatures = self.get_signatures_list(
                es_data["facets"],
                maxsize,
                self.config.platforms
            )

            plugin_fields = []
            if params['report_process'] == 'plugin':
                plugin_fields = [
                    'PluginFilename',
                    'PluginName',
                    'PluginVersion',
                ]

            facets = self.get_count_facets(
                signatures,
                params["result_offset"],
                maxsize,
                plugin_fields,
            )

            count_by_os_query = query
            count_by_os_query["facets"] = facets
            count_by_os_query_json = json.dumps(count_by_os_query)
            logger.debug("Query the OS by signature: %s",
                         count_by_os_query_json)

            count_result = self.query(params["from_date"], params["to_date"],
                                      count_by_os_query_json)
            try:
                count_data = json.loads(count_result[0])
            except ValueError:
                logger.error("ElasticSearch returned something wrong: %s",
                             count_result[0], exc_info=True)
                raise

            count_sign = count_data["facets"]
            signatures = self.get_counts(
                signatures,
                count_sign,
                params["result_offset"],
                maxsize,
                self.config.platforms,
                plugin_fields,
            )

        hits = [signatures[x] for x in range(params["result_offset"], maxsize)]

        # sort results by count *and* signatures
        hits.sort(key=lambda x: (-x['count'], x['signature'].lower()))

        return {
            "total": signature_count,
            "hits": hits
        }

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
    def get_signatures_list(facets, maxsize, platforms):
        """
        Generate the result of search by signature from the facets ES returns.
        """
        signatures = facets["signatures"]["terms"]

        results = []
        sign_list = {}

        for i in range(maxsize):
            results.append({
                "signature": signatures[i]["term"],
                "count": signatures[i]["count"]
            })
            for platform in platforms:
                results[i]["_".join(("is", platform["id"]))] = 0

            sign_list[signatures[i]["term"]] = results[i]

        return results

    @staticmethod
    def get_count_facets(
        signatures,
        result_offset,
        maxsize,
        plugin_fields=None
    ):
        """
        Generate the facets to count the number of each OS for each signature.
        """
        facets = {}

        for i in range(result_offset, maxsize):
            sign = signatures[i]["signature"]
            sign_hang = "_".join((sign, "hang"))
            sign_plugin = "_".join((sign, "plugin"))
            sign_content = "_".join((sign, "content"))

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
                    "term": {
                        "process_type": "plugin"
                    }
                },
                "facet_filter": facet_filter
            }
            facets[sign_content] = {
                "filter": {
                    "term": {
                        "process_type": "content"
                    }
                },
                "facet_filter": facet_filter
            }

            for plugin_field in plugin_fields or []:
                sign_plugin_field = "_".join((sign, plugin_field))
                facets[sign_plugin_field] = {
                    "terms": {
                        "field": "%s.full" % plugin_field
                    },
                    "facet_filter": facet_filter
                }

        return facets

    @staticmethod
    def get_counts(
        signatures,
        count_sign,
        result_offset,
        maxsize,
        platforms,
        plugin_fields=None
    ):
        """
        Generate the complementary information about signatures
        (count by OS, number of plugins and of hang, plugin information).
        """
        # Transform the results into something we can return
        for i in range(result_offset, maxsize):
            signature = signatures[i]["signature"]
            # OS count
            for term in count_sign[signature]["terms"]:
                for os in platforms:
                    if term["term"] == os["id"]:
                        osid = "is_%s" % os["id"]
                        signatures[i][osid] = term["count"]
            # Hang count
            sign_hang = "_".join((signature, "hang"))
            signatures[i]["numhang"] = count_sign[sign_hang]["count"]
            # Plugin count
            sign_plugin = "_".join((signature, "plugin"))
            signatures[i]["numplugin"] = count_sign[sign_plugin]["count"]
            # Content count
            sign_content = "_".join((signature, "content"))
            signatures[i]["numcontent"] = count_sign[sign_content]["count"]

            for plugin_field in plugin_fields or []:
                sign_plugin_field = "_".join((signature, plugin_field))
                try:
                    term = count_sign[sign_plugin_field]['terms'][0]['term']
                except IndexError:
                    term = ''

                signatures[i][plugin_field.lower()] = term

        return signatures
