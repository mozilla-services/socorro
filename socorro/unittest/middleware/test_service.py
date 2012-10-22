# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

import socorro.external.elasticsearch.base as es
import socorro.external.postgresql.base as pg
import socorro.middleware.service as serv
import socorro.lib.util as util
import socorro.unittest.testlib.util as testutil


#------------------------------------------------------------------------------
def setup_module():
    testutil.nosePrintModule(__file__)


#==============================================================================
class TestMiddlewareService(unittest.TestCase):
    """Test the base class for all middleware services. """

    #--------------------------------------------------------------------------
    def get_dummy_context(self):
        """
        Create a dummy config object to use when testing.
        """
        context = util.DotDict()
        context.database = util.DotDict({
            'database_host': 'fred',
            'database_port': '127',
            'database_name': 'wilma',
            'database_user': 'ricky',
            'database_password': 'lucy',
        })
        context.webapi = util.DotDict({
            'elasticSearchHostname': "localhost",
            'elasticSearchPort': "9200"
        })
        context.searchImplementationModule = "socorro.external.postgresql"
        context.serviceImplementationModule = "socorro.external.elasticsearch"
        return context

    #--------------------------------------------------------------------------
    def test_get_module(self):
        """
        Test Service.get_module
        """
        config = self.get_dummy_context()
        service = serv.DataAPIService(config)
        service.service_name = "search"
        params = {}

        # Test service config module
        import_failed = False
        try:
            mod = service.get_module(params)
        except NotImplementedError:
            import_failed = True

        self.assertFalse(import_failed)
        self.assertTrue(mod)

        try:
            search = mod.Search(config=config)
        except AttributeError:
            assert False, "Imported module does not contain the needed class"

        self.assertTrue(isinstance(search, pg.PostgreSQLBase))

        # Test forced module
        import_failed = False
        params["force_api_impl"] = "elasticsearch"
        try:
            mod = service.get_module(params)
        except NotImplementedError:
            import_failed = True

        self.assertFalse(import_failed)
        self.assertTrue(mod)

        try:
            search = mod.Search(config=config)
        except AttributeError:
            assert False, "Imported module does not contain the needed class"

        self.assertTrue(isinstance(search, es.ElasticSearchBase))

        # Test default config module
        import_failed = False
        params = {}
        del config.searchImplementationModule
        try:
            mod = service.get_module(params)
        except NotImplementedError:
            import_failed = True

        self.assertFalse(import_failed)
        self.assertTrue(mod)

        try:
            search = mod.Search(config=config)
        except AttributeError:
            assert False, "Imported module does not contain the needed class"

        self.assertTrue(isinstance(search, es.ElasticSearchBase))

        # Test no valid module to import
        import_failed = False
        params = {}
        config.serviceImplementationModule = "unknownmodule"
        try:
            mod = service.get_module(params)
        except AttributeError:  # catching web.InternalError
            import_failed = True

        self.assertTrue(import_failed)

    #--------------------------------------------------------------------------
    def test_parse_query_string(self):
        """
        Test Service.parse_query_string
        """
        config = self.get_dummy_context()
        service = serv.DataAPIService(config)

        # Test simple query string
        url = "param/value/"
        result = service.parse_query_string(url)
        expected = {
            "param": "value"
        }

        self.assertEqual(result, expected)

        # Test complex query string
        url = "product/firefox/from/yesterday/build/12+33+782/version/7.0.1b4/"
        result = service.parse_query_string(url)
        expected = {
            "product": "firefox",
            "from": "yesterday",
            "build": ["12", "33", "782"],
            "version": "7.0.1b4"
        }

        self.assertEqual(result, expected)

        # Test incorrect query string
        url = "product/firefox/for"
        result = service.parse_query_string(url)
        expected = {
            "product": "firefox"
        }

        self.assertEqual(result, expected)

        # Test empty value
        url = "product/firefox/for//"
        result = service.parse_query_string(url)
        expected = {
            "product": "firefox",
            "for": ""
        }

        self.assertEqual(result, expected)

        # Test empty param
        url = "product/firefox//bla/"
        result = service.parse_query_string(url)
        expected = {
            "product": "firefox"
        }

        self.assertEqual(result, expected)
