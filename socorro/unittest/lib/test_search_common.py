# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from datetime import datetime

import socorro.lib.search_common as co


#==============================================================================
class TestSearchCommon(unittest.TestCase):
    """Test functions of the search_common module. """

    #--------------------------------------------------------------------------
    def test_get_parameters(self):
        """
        Test search_common.get_parameters()
        """
        # Empty params, only default values are returned
        params = co.get_parameters({})
        self.assertTrue(params)

        for i in params:
            typei = type(params[i])
            if i in ("from_date", "to_date", "build_from", "build_to"):
                self.assertTrue(typei is datetime)
            else:
                self.assertTrue(not params[i] or typei is int or typei is str
                                or typei is list)

        # Empty params
        params = co.get_parameters({
            "terms": "",
            "fields": "",
            "products": "",
            "from_date": "",
            "to_date": "",
            "versions": "",
            "reasons": "",
            "release_channels": "",
            "os": "",
            "search_mode": "",
            "build_ids": "",
            "report_process": "",
            "report_type": "",
            "plugin_in": "",
            "plugin_search_mode": "",
            "plugin_terms": ""
        })
        assert params, "SearchCommon.get_parameters() returned something " \
                       "empty or null."
        for i in params:
            typei = type(params[i])
            if i in ("from_date", "to_date", "build_from", "build_to"):
                self.assertTrue(typei is datetime)
            else:
                self.assertTrue(not params[i] or typei is int or typei is str
                                or typei is list)

        # Test with encoded slashes in terms and signature
        params = co.get_parameters({
            "terms": ["some", "terms/sig"],
            "signature": "my/little/signature"
        })

        self.assertTrue("signature" in params)
        self.assertTrue("terms" in params)
        self.assertEqual(params["terms"], ["some", "terms/sig"])
        self.assertEqual(params["signature"], "my/little/signature")

    #--------------------------------------------------------------------------
    def test_restrict_fields(self):
        """
        Test search_common.restrict_fields()
        """
        authorized_fields = ['signature', 'dump']

        fields = ["signatute", "signature", "123456sfdgerw&$%#&", "dump",
                  None, "dump"]
        theoric_fields = ["signature", "dump"]
        restricted_fields = co.restrict_fields(fields, authorized_fields)
        self.assertEqual(restricted_fields, theoric_fields)

        fields = []
        theoric_fields = ["signature"]
        restricted_fields = co.restrict_fields(fields, authorized_fields)
        self.assertEqual(restricted_fields, theoric_fields)

        fields = None
        theoric_fields = ["signature"]
        restricted_fields = co.restrict_fields(fields, authorized_fields)
        self.assertEqual(restricted_fields, theoric_fields)

        fields = ["nothing"]
        theoric_fields = ["signature"]
        restricted_fields = co.restrict_fields(fields, authorized_fields)
        self.assertEqual(restricted_fields, theoric_fields)

        self.assertRaises(ValueError, co.restrict_fields, fields, [])
        self.assertRaises(TypeError, co.restrict_fields, fields, None)
