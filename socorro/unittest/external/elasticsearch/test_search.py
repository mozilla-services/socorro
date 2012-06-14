# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from socorro.external.elasticsearch.search import Search

import socorro.lib.util as util
import socorro.unittest.testlib.util as testutil


#------------------------------------------------------------------------------
def setup_module():
    testutil.nosePrintModule(__file__)


#==============================================================================
class TestElasticSearchSearch(unittest.TestCase):
    """Test Search class implemented with ElasticSearch. """

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
    def test_get_signatures(self):
        """
        Test Search.get_signatures()
        """
        context = self.get_dummy_context()
        facets = {
            "signatures": {
                "terms": [
                    {
                        "term": "hang",
                        "count": 145
                    },
                    {
                        "term": "js",
                        "count": 7
                    },
                    {
                        "term": "ws",
                        "count": 4
                    }
                ]
            }
        }
        size = 3
        expected = ["hang", "js", "ws"]
        signatures = Search.get_signatures(facets, size, context.platforms)
        res_signs = []
        for sign in signatures:
            self.assertTrue(sign["signature"] in expected)
            res_signs.append(sign["signature"])

        for sign in expected:
            self.assertTrue(sign in res_signs)

    #--------------------------------------------------------------------------
    def test_get_counts(self):
        """
        Test Search.get_counts()
        """
        context = self.get_dummy_context()
        signatures = [
            {
                "signature": "hang",
                "count": 12
            },
            {
                "signature": "js",
                "count": 4
            }
        ]
        count_sign = {
            "hang": {
                "terms": [
                    {
                        "term": "windows",
                        "count": 3
                    },
                    {
                        "term": "linux",
                        "count": 4
                    }
                ]
            },
            "js": {
                "terms": [
                    {
                        "term": "windows",
                        "count": 2
                    }
                ]
            },
            "hang_hang": {
                "count": 0
            },
            "js_hang": {
                "count": 0
            },
            "hang_plugin": {
                "count": 0
            },
            "js_plugin": {
                "count": 0
            },
            "hang_content": {
                "count": 0
            },
            "js_content": {
                "count": 0
            }
        }
        res = Search.get_counts(signatures, count_sign, 0, 2,
                                context.platforms)

        self.assertTrue(type(res) is list)
        for sign in res:
            self.assertTrue("signature" in sign)
            self.assertTrue("count" in sign)
            self.assertTrue("is_windows" in sign)
            self.assertTrue("numhang" in sign)
            self.assertTrue("numplugin" in sign)
            self.assertTrue("numcontent" in sign)

        self.assertTrue("is_linux" in res[0])
        self.assertFalse("is_linux" in res[1])
