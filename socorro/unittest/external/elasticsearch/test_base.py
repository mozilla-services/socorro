import unittest

from socorro.external.elasticsearch.base import ElasticSearchBase

import socorro.lib.search_common as scommon
import socorro.lib.util as util
import socorro.unittest.testlib.util as testutil


#------------------------------------------------------------------------------
def setup_module():
    testutil.nosePrintModule(__file__)


#==============================================================================
class TestElasticSearchBase(unittest.TestCase):
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
        return context

    #--------------------------------------------------------------------------
    def test_build_query_from_params(self):
        # Test with all default parameters
        params = {}
        params = scommon.get_parameters(params)
        query = ElasticSearchBase.build_query_from_params(params)
        self.assertTrue(query)
        self.assertTrue("query" in query)
        self.assertTrue("size" in query)
        self.assertTrue("from" in query)

        # Searching for a term in a specific field and with a specific product
        params = {
            "terms": "hang",
            "fields": "dump",
            "search_mode": "contains",
            "products": "fennec"
        }
        params = scommon.get_parameters(params)
        query = ElasticSearchBase.build_query_from_params(params)
        self.assertTrue(query)
        self.assertTrue("query" in query)
        self.assertTrue("filtered" in query["query"])

        filtered = query["query"]["filtered"]
        self.assertTrue("query" in filtered)
        self.assertTrue("wildcard" in filtered["query"])
        self.assertTrue("dump" in filtered["query"]["wildcard"])

        dump_term = filtered["query"]["wildcard"]["dump"]
        self.assertEqual(dump_term, "*hang*")
        self.assertTrue("filter" in filtered)
        self.assertTrue("and" in filtered["filter"])

    #--------------------------------------------------------------------------
    def test_build_terms_query(self):
        # Empty query
        fields = ""
        terms = None
        query = ElasticSearchBase.build_terms_query(fields, terms)
        self.assertFalse(query)

        #......................................................................
        # Single term, single field query
        fields = "signature"
        terms = "hang"
        query = ElasticSearchBase.build_terms_query(fields, terms)
        self.assertTrue("term" in query)
        self.assertTrue(fields in query["term"])
        self.assertEqual(query["term"][fields], terms)

        #......................................................................
        # Multiple terms, single field query
        fields = "signature"
        terms = ["hang", "flash", "test"]
        query = ElasticSearchBase.build_terms_query(fields, terms)
        self.assertTrue("terms" in query)
        self.assertTrue(fields in query["terms"])
        self.assertEqual(query["terms"][fields], terms)

        #......................................................................
        # Multiple terms, multiple fields query
        fields = ["signature", "dump"]
        terms = ["hang", "flash"]
        query = ElasticSearchBase.build_terms_query(fields, terms)
        self.assertTrue("terms" in query)
        for field in fields:
            self.assertTrue(field in query["terms"])
            self.assertEqual(query["terms"][field], terms)

    #--------------------------------------------------------------------------
    def test_build_wildcard_query(self):
        # Empty query
        fields = ""
        terms = None
        query = ElasticSearchBase.build_wildcard_query(fields, terms)
        self.assertFalse(query)

        #......................................................................
        # Single term, single field query
        fields = "signature"
        terms = "hang"
        query = ElasticSearchBase.build_wildcard_query(fields, terms)
        self.assertTrue("wildcard" in query)
        self.assertTrue("signature.full" in query["wildcard"])
        self.assertEqual(query["wildcard"]["signature.full"], terms)

        #......................................................................
        # Multiple terms, single field query
        fields = "dump"
        terms = ["hang", "flash", "test"]
        query = ElasticSearchBase.build_wildcard_query(fields, terms)
        self.assertTrue("wildcard" in query)
        self.assertTrue(fields in query["wildcard"])
        self.assertEqual(query["wildcard"][fields], terms)

        #......................................................................
        # Multiple terms, multiple fields query
        fields = ["reason", "dump"]
        terms = ["hang", "flash"]
        query = ElasticSearchBase.build_wildcard_query(fields, terms)
        self.assertTrue("wildcard" in query)
        for field in fields:
            self.assertTrue(field in query["wildcard"])
            self.assertEqual(query["wildcard"][field], terms)

    #--------------------------------------------------------------------------
    def test_format_versions(self):
        # Empty versions
        versions = None
        version_res = ElasticSearchBase.format_versions(versions)
        self.assertFalse(version_res)

        #......................................................................
        # Only one product, no version
        versions = ["firefox"]
        version_res = ElasticSearchBase.format_versions(versions)
        version_res_exp = [{"product": "firefox", "version": None}]
        self.assertTrue(isinstance(version_res, list))
        self.assertEqual(version_res, version_res_exp)

        #......................................................................
        # One product, one version
        versions = ["firefox:5.0.1b"]
        version_res = ElasticSearchBase.format_versions(versions)
        self.assertTrue(isinstance(version_res, list))
        self.assertTrue("product" in version_res[0])
        self.assertTrue("version" in version_res[0])
        self.assertEqual(version_res[0]["product"], "firefox")
        self.assertEqual(version_res[0]["version"], "5.0.1b")

        #......................................................................
        # Multiple products, multiple versions
        versions = ["firefox:5.0.1b", "fennec:1"]
        version_res = ElasticSearchBase.format_versions(versions)
        self.assertTrue(isinstance(version_res, list))
        for v in version_res:
            self.assertTrue("product" in v)
            self.assertTrue("version" in v)

        self.assertEqual(version_res[0]["product"], "firefox")
        self.assertEqual(version_res[0]["version"], "5.0.1b")
        self.assertEqual(version_res[1]["product"], "fennec")
        self.assertEqual(version_res[1]["version"], "1")

    #--------------------------------------------------------------------------
    def test_prepare_terms(self):
        """
        Test Search.prepare_terms()
        """
        # Empty terms
        terms = []
        search_mode = None
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        self.assertFalse(newterms)

        # Contains mode, single term
        terms = ["test"]
        search_mode = "contains"
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        self.assertEqual(newterms, "*test*")

        # Contains mode, multiple terms
        terms = ["test", "hang"]
        search_mode = "contains"
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        self.assertEqual(newterms, "*test hang*")

        # Starts with mode, multiple terms
        terms = ["test", "hang"]
        search_mode = "starts_with"
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        self.assertEqual(newterms, "test hang*")

        # Is exactly mode, multiple terms
        terms = ["test", "hang"]
        search_mode = "is_exactly"
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        self.assertEqual(newterms, " ".join(terms))

        # Random unexisting mode, multiple terms
        terms = ["test", "hang"]
        search_mode = "random_unexisting_mode"
        newterms = ElasticSearchBase.prepare_terms(terms, search_mode)
        self.assertEqual(newterms, terms)
