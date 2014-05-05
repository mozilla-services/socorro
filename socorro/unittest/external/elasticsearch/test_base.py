# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import json
import mock

from nose.plugins.attrib import attr
from nose.tools import eq_, ok_

from socorro.external.elasticsearch.base import ElasticSearchBase

import socorro.lib.search_common as scommon
import socorro.lib.util as util
from socorro.unittest.testbase import TestCase


#==============================================================================
@attr(integration='elasticsearch')
class IntegrationTestElasticSearchBase(TestCase):

    def _get_default_config(self):
        config = util.DotDict()
        config.elasticSearchHostname = 'somehost'
        config.elasticSearchPort = '9200'
        config.elasticsearch_index = 'socorro%Y%W'

        return config

    def test_generate_list_of_indexes(self):
        config = self._get_default_config()
        es = ElasticSearchBase(config=config)

        from_date = datetime.datetime(2000, 1, 1, 0, 0)
        to_date = datetime.datetime(2000, 1, 16, 0, 0)

        indexes = es.generate_list_of_indexes(from_date, to_date)
        indexes_exp = [
            'socorro200000',
            'socorro200001',
            'socorro200002',
        ]

        eq_(indexes, indexes_exp)

    @mock.patch('socorro.external.elasticsearch.base.httpc')
    def test_query(self, mock_http):
        config = self._get_default_config()
        es = ElasticSearchBase(config=config)

        def post_fn(uri, query):
            if 'socorro200002' in uri:
                return {
                    'error': {
                        'code': 404,
                        'data': 'IndexMissingException[[socorro200002]]'
                    }
                }
            return ''
        mock_http.HttpClient.return_value.post = post_fn

        from_date = datetime.datetime(2000, 1, 1, 0, 0)
        to_date = datetime.datetime(2000, 1, 16, 0, 0)
        json_query = '{}'

        res = es.query(from_date, to_date, json_query)

        eq_(res, ('', "text/json"))


#==============================================================================
class TestElasticSearchBase(TestCase):
    """Test ElasticSearchBase class. """

    #--------------------------------------------------------------------------
    def get_dummy_context(self):
        """
        Create a dummy config object to use when testing.
        """
        context = util.DotDict()
        context.elasticSearchHostname = ""
        context.elasticSearchPort = 9200
        context.platforms = (
            {
                "id": "windows",
                "name": "Windows NT"
            },
            {
                "id": "linux",
                "name": "Linux"
            }
        )
        context.non_release_channels = ['beta', 'aurora', 'nightly']
        context.restricted_channels = ['beta']
        return context

    #--------------------------------------------------------------------------
    def test_build_query_from_params(self):
        # Test with all default parameters
        config = self.get_dummy_context()
        params = {}
        params = scommon.get_parameters(params)
        query = ElasticSearchBase.build_query_from_params(params, config)
        ok_(query)
        ok_("query" in query)
        ok_("size" in query)
        ok_("from" in query)

        # Searching for a term in a specific field and with a specific product
        params = {
            "terms": "hang",
            "fields": "dump",
            "search_mode": "contains",
            "products": "fennec"
        }
        params = scommon.get_parameters(params)
        query = ElasticSearchBase.build_query_from_params(params, config)
        ok_(query)
        ok_("query" in query)
        ok_("filtered" in query["query"])

        filtered = query["query"]["filtered"]
        ok_("query" in filtered)
        ok_("wildcard" in filtered["query"])
        ok_(
            "processed_crash.dump" in filtered["query"]["wildcard"]
        )

        dump_term = filtered["query"]["wildcard"]["processed_crash.dump"]
        eq_(dump_term, "*hang*")
        ok_("filter" in filtered)
        ok_("and" in filtered["filter"])

        # Test versions
        params = {
            "products": "WaterWolf",
            "versions": "WaterWolf:1.0a1"
        }
        params = scommon.get_parameters(params)
        params["versions_info"] = {
            "WaterWolf:1.0a1": {
                "product_version_id": 1,
                "version_string": "1.0a1",
                "product_name": "WaterWolf",
                "major_version": "1.0a1",
                "release_channel": "nightly-water",
                "build_id": None,
                "is_rapid_beta": False,
                "is_from_rapid_beta": False,
                "from_beta_version": "WaterWolf:1.0a1",
            }
        }
        query = ElasticSearchBase.build_query_from_params(params, config)
        filtered = query["query"]["filtered"]

        ok_("and" in filtered["filter"])
        and_filter_str = json.dumps(filtered["filter"]['and'])
        ok_('WaterWolf' in and_filter_str)
        ok_('1.0a1' in and_filter_str)
        ok_('nightly-water' in and_filter_str)

        # Test versions with an empty release channel in versions_info
        params = {
            "products": "WaterWolf",
            "versions": "WaterWolf:2.0"
        }
        params = scommon.get_parameters(params)
        params['versions_info'] = {
            'WaterWolf:2.0': {
                "version_string": "2.0",
                "product_name": "WaterWolf",
                "major_version": "2.0",
                "release_channel": None,
                "build_id": None,
                "is_rapid_beta": False,
                "is_from_rapid_beta": False,
                "from_beta_version": "WaterWolf:2.0",
            }
        }
        query = ElasticSearchBase.build_query_from_params(params, config)
        filtered = query["query"]["filtered"]

        ok_("and" in filtered["filter"])
        and_filter_str = json.dumps(filtered["filter"]['and'])
        ok_('WaterWolf' in and_filter_str)
        ok_('2.0' in and_filter_str)

    #--------------------------------------------------------------------------
    def test_build_terms_query(self):
        # Empty query
        fields = ""
        terms = None
        query = ElasticSearchBase.build_terms_query(fields, terms)
        ok_(not query)

        #......................................................................
        # Single term, single field query
        fields = "signature"
        prefixed_field = "processed_crash.signature"
        terms = "hang"
        query = ElasticSearchBase.build_terms_query(fields, terms)
        ok_("term" in query)
        ok_(prefixed_field in query["term"])
        eq_(query["term"][prefixed_field], terms)

        #......................................................................
        # Multiple terms, single field query
        fields = "signature"
        prefixed_field = "processed_crash.signature"
        terms = ["hang", "flash", "test"]
        query = ElasticSearchBase.build_terms_query(fields, terms)
        ok_("terms" in query)
        ok_(prefixed_field in query["terms"])
        eq_(query["terms"][prefixed_field], terms)

        #......................................................................
        # Multiple terms, multiple fields query
        fields = ["signature", "dump"]
        terms = ["hang", "flash"]
        query = ElasticSearchBase.build_terms_query(fields, terms)
        ok_("terms" in query)
        for field in fields:
            prefixed_field = "processed_crash.%s" % field
            ok_(prefixed_field in query["terms"])
            eq_(query["terms"][prefixed_field], terms)

    #--------------------------------------------------------------------------
    def test_build_wildcard_query(self):
        # Empty query
        fields = ""
        terms = None
        query = ElasticSearchBase.build_wildcard_query(fields, terms)
        ok_(not query)

        #......................................................................
        # Single term, single field query
        fields = "signature"
        terms = "hang"
        query = ElasticSearchBase.build_wildcard_query(fields, terms)
        ok_("wildcard" in query)
        ok_("processed_crash.signature.full" in query["wildcard"])
        eq_(
            query["wildcard"]["processed_crash.signature.full"],
            terms
        )

        #......................................................................
        # Multiple terms, single field query
        fields = "dump"
        prefixed_field = "processed_crash.dump"
        terms = ["hang", "flash", "test"]
        query = ElasticSearchBase.build_wildcard_query(fields, terms)
        ok_("wildcard" in query)
        ok_(prefixed_field in query["wildcard"])
        eq_(query["wildcard"][prefixed_field], terms)

        #......................................................................
        # Multiple terms, multiple fields query
        fields = ["reason", "dump"]
        terms = ["hang", "flash"]
        query = ElasticSearchBase.build_wildcard_query(fields, terms)
        ok_("wildcard" in query)
        for field in fields:
            prefixed_field = "processed_crash.%s" % field
            ok_(prefixed_field in query["wildcard"])
            eq_(query["wildcard"][prefixed_field], terms)

    #--------------------------------------------------------------------------
    def test_format_versions(self):
        # Empty versions
        versions = None
        version_res = ElasticSearchBase.format_versions(versions)
        ok_(not version_res)

        #......................................................................
        # Only one product, no version
        versions = ["firefox"]
        version_res = ElasticSearchBase.format_versions(versions)
        version_res_exp = [{"product": "firefox", "version": None}]
        ok_(isinstance(version_res, list))
        eq_(version_res, version_res_exp)

        #......................................................................
        # One product, one version
        versions = ["firefox:5.0.1b"]
        version_res = ElasticSearchBase.format_versions(versions)
        ok_(isinstance(version_res, list))
        ok_("product" in version_res[0])
        ok_("version" in version_res[0])
        eq_(version_res[0]["product"], "firefox")
        eq_(version_res[0]["version"], "5.0.1b")

        #......................................................................
        # Multiple products, multiple versions
        versions = ["firefox:5.0.1b", "fennec:1"]
        version_res = ElasticSearchBase.format_versions(versions)
        ok_(isinstance(version_res, list))
        for v in version_res:
            ok_("product" in v)
            ok_("version" in v)

        eq_(version_res[0]["product"], "firefox")
        eq_(version_res[0]["version"], "5.0.1b")
        eq_(version_res[1]["product"], "fennec")
        eq_(version_res[1]["version"], "1")

    #--------------------------------------------------------------------------
    def test_prepare_terms(self):
        """
        Test Search.prepare_terms()
        """
        # Empty terms
        terms = []
        search_mode = None
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        ok_(not newterms)

        # Contains mode, single term
        terms = ["test"]
        search_mode = "contains"
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        eq_(newterms, "*test*")

        # Contains mode, multiple terms
        terms = ["test", "hang"]
        search_mode = "contains"
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        eq_(newterms, "*test hang*")

        # Starts with mode, multiple terms
        terms = ["test", "hang"]
        search_mode = "starts_with"
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        eq_(newterms, "test hang*")

        # Is exactly mode, multiple terms
        terms = ["test", "hang"]
        search_mode = "is_exactly"
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        eq_(newterms, " ".join(terms))

        # Random unexisting mode, multiple terms
        terms = ["test", "hang"]
        search_mode = "random_unexisting_mode"
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        eq_(newterms, terms)
