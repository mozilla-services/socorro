import unittest

from socorro.external.postgresql.crashes import Crashes
from socorro.lib import util

import socorro.unittest.testlib.util as testutil


#------------------------------------------------------------------------------
def setup_module():
    testutil.nosePrintModule(__file__)


#==============================================================================
class TestCrashes(unittest.TestCase):
    """Test PostgreSQLBase class. """

    #--------------------------------------------------------------------------
    def get_dummy_context(self):
        """Create a dummy config object to use when testing."""
        context = util.DotDict()
        context.platforms = (
            {
                "id": "windows",
                "name": "Windows NT"
            },
            {
                "id": "linux",
                "name": "Linux"
            },
            {
                "id": "mac",
                "name": "Mac OS X"
            }
        )
        return context

    #--------------------------------------------------------------------------
    def get_instance(self, config=None):
        """Return an instance of Crashes with the config parameter as
        a context or the default one if config is None.
        """
        args = {
            "config": config or self.get_dummy_context()
        }
        return Crashes(**args)

    #--------------------------------------------------------------------------
    def test_prepare_search_params(self):
        """Test Crashes.prepare_search_params()."""
        crashes = self.get_instance()

        # .....................................................................
        # Test 1: no args
        args = {}
        self.assertEqual(crashes.prepare_search_params(**args), None)

        # .....................................................................
        # Test 2: a signature
        args = {
            "signature": "something"
        }

        params = crashes.prepare_search_params(**args)
        self.assertTrue("signature" in params)
        self.assertTrue("terms" in params)
        self.assertEqual(params["signature"], "something")
        self.assertEqual(params["signature"], params["terms"])

        # .....................................................................
        # Test 3: some OS
        args = {
            "signature": "something",
            "os": ["windows", "linux"]
        }

        params = crashes.prepare_search_params(**args)
        self.assertTrue("os" in params)
        self.assertEqual(len(params["os"]), 2)
        self.assertEqual(params["os"][0], "Windows NT")
        self.assertEqual(params["os"][1], "Linux")

        # .....................................................................
        # Test 4: with a plugin
        args = {
            "signature": "something",
            "report_process": "plugin",
            "plugin_terms": ["some", "plugin"],
            "plugin_search_mode": "contains",
        }

        params = crashes.prepare_search_params(**args)
        self.assertTrue("plugin_terms" in params)
        self.assertEqual(params["plugin_terms"], "%some plugin%")
