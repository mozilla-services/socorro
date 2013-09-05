# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime
import unittest

from socorro.lib import datetimeutil
from socorro.lib.search_common import (
    SearchBase, SearchParam, convert_to_type, get_parameters, restrict_fields
)


class TestSearchBase(unittest.TestCase):
    """Test search_common.SearchBase. """

    def test_get_parameters(self):
        search = SearchBase()

        args = {
            'signature': 'mysig',
            'product': 'WaterWolf',
            'version': '1.0',
        }
        params = search.get_parameters(**args)
        for i in ('signature', 'product', 'version'):
            self.assertTrue(i in params)
            self.assertTrue(isinstance(params[i], list))
            self.assertTrue(isinstance(params[i][0], SearchParam))
            self.assertEqual(params[i][0].operator, '')

        args = {
            'signature': '~js',
            'product': ['WaterWolf', 'NightTrain'],
            'version': '=1.0',
        }
        params = search.get_parameters(**args)
        self.assertEqual(params['signature'][0].operator, '~')
        self.assertEqual(params['signature'][0].value, 'js')
        self.assertEqual(params['product'][0].operator, '')
        # Test that params with no operator are stacked
        self.assertEqual(
            params['product'][0].value,
            ['WaterWolf', 'NightTrain']
        )
        self.assertEqual(params['version'][0].operator, '')

        args = {
            'signature': ['~Mark', '$js'],
        }
        params = search.get_parameters(**args)
        self.assertEqual(params['signature'][0].operator, '~')
        self.assertEqual(params['signature'][0].value, 'Mark')
        self.assertEqual(params['signature'][1].operator, '$')
        self.assertEqual(params['signature'][1].value, 'js')

        args = {
            'build_id': ['>20000101000000', '<20150101000000'],
        }
        params = search.get_parameters(**args)
        self.assertEqual(params['build_id'][0].operator, '>')
        self.assertEqual(params['build_id'][0].value, 20000101000000)
        self.assertEqual(params['build_id'][1].operator, '<')
        self.assertEqual(params['build_id'][1].value, 20150101000000)

    def test_get_parameters_with_not(self):
        search = SearchBase()

        args = {
            'signature': '!~mysig',
            'product': '!WaterWolf',
            'version': '1.0',
            'user_comments': '!__null__',
        }
        params = search.get_parameters(**args)
        self.assertEqual(params['signature'][0].operator, '~')
        self.assertTrue(params['signature'][0].operator_not)
        self.assertEqual(params['signature'][0].value, 'mysig')

        self.assertEqual(params['product'][0].operator, '')
        self.assertTrue(params['product'][0].operator_not)

        self.assertEqual(params['version'][0].operator, '')
        self.assertFalse(params['version'][0].operator_not)

        self.assertEqual(params['user_comments'][0].operator, '__null__')
        self.assertTrue(params['user_comments'][0].operator_not)

    def test_get_parameters_date_defaults(self):
        search = SearchBase()
        now = datetimeutil.utc_now()

        # Test default values when nothing is passed
        params = search.get_parameters()
        self.assertTrue('date' in params)
        self.assertTrue(len(params['date']), 2)

        # Pass only the high value
        args = {
            'date': '<%s' % datetimeutil.date_to_string(now)
        }
        params = search.get_parameters(**args)
        self.assertTrue('date' in params)
        self.assertTrue(len(params['date']), 2)
        self.assertEqual(params['date'][0].operator, '<')
        self.assertEqual(params['date'][1].operator, '>=')
        self.assertEqual(params['date'][0].value.date(), now.date())
        self.assertEqual(
            params['date'][1].value.date(),
            now.date() - datetime.timedelta(days=7)
        )

        # Pass only the low value
        pasttime = now - datetime.timedelta(days=10)
        args = {
            'date': '>=%s' % datetimeutil.date_to_string(pasttime)
        }
        params = search.get_parameters(**args)
        self.assertTrue('date' in params)
        self.assertTrue(len(params['date']), 2)
        self.assertEqual(params['date'][0].operator, '<=')
        self.assertEqual(params['date'][1].operator, '>=')
        self.assertEqual(params['date'][0].value.date(), now.date())
        self.assertEqual(params['date'][1].value.date(), pasttime.date())

        # Pass the two values
        pasttime = now - datetime.timedelta(days=10)
        args = {
            'date': [
                '<%s' % datetimeutil.date_to_string(now),
                '>%s' % datetimeutil.date_to_string(pasttime),
            ]
        }
        params = search.get_parameters(**args)
        self.assertTrue('date' in params)
        self.assertTrue(len(params['date']), 2)
        self.assertEqual(params['date'][0].operator, '<')
        self.assertEqual(params['date'][1].operator, '>')
        self.assertEqual(params['date'][0].value.date(), now.date())
        self.assertEqual(params['date'][1].value.date(), pasttime.date())


#==============================================================================
class TestSearchCommon(unittest.TestCase):
    """Test functions of the search_common module. """

    def test_convert_to_type(self):
        # Test null
        res = convert_to_type(None, 'datetime')
        self.assertTrue(res is None)

        # Test integer
        res = convert_to_type(12, 'int')
        self.assertTrue(isinstance(res, int))
        self.assertEqual(res, 12)

        # Test integer
        res = convert_to_type('12', 'int')
        self.assertTrue(isinstance(res, int))
        self.assertEqual(res, 12)

        # Test string
        res = convert_to_type(datetime.datetime(2012, 1, 1), 'str')
        self.assertTrue(isinstance(res, str))
        self.assertEqual(res, '2012-01-01 00:00:00')

        # Test boolean
        res = convert_to_type(1, 'bool')
        self.assertTrue(isinstance(res, bool))
        self.assertTrue(res)

        # Test boolean
        res = convert_to_type('T', 'bool')
        self.assertTrue(isinstance(res, bool))
        self.assertTrue(res)

        # Test boolean
        res = convert_to_type(14, 'bool')
        self.assertTrue(isinstance(res, bool))
        self.assertFalse(res)

        # Test datetime
        res = convert_to_type('2012-01-01T12:23:34', 'datetime')
        self.assertTrue(isinstance(res, datetime.datetime))
        self.assertEqual(res.year, 2012)
        self.assertEqual(res.month, 1)
        self.assertEqual(res.hour, 12)

        # Test date
        res = convert_to_type('2012-01-01T00:00:00', 'date')
        self.assertTrue(isinstance(res, datetime.date))
        self.assertEqual(res.year, 2012)
        self.assertEqual(res.month, 1)

        # Test error
        self.assertRaises(ValueError, convert_to_type, 'abds', 'int')
        self.assertRaises(ValueError, convert_to_type, '2013-02-32', 'date')

    #--------------------------------------------------------------------------
    def test_get_parameters(self):
        """
        Test search_common.get_parameters()
        """
        # Empty params, only default values are returned
        params = get_parameters({})
        self.assertTrue(params)

        for i in params:
            typei = type(params[i])
            if i in ("from_date", "to_date", "build_from", "build_to"):
                self.assertTrue(typei is datetime.datetime)
            else:
                self.assertTrue(not params[i] or typei is int or typei is str
                                or typei is list)

        # Empty params
        params = get_parameters({
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
                self.assertTrue(typei is datetime.datetime)
            else:
                self.assertTrue(not params[i] or typei is int or typei is str
                                or typei is list)

        # Test with encoded slashes in terms and signature
        params = get_parameters({
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
        restricted_fields = restrict_fields(fields, authorized_fields)
        self.assertEqual(restricted_fields, theoric_fields)

        fields = []
        theoric_fields = ["signature"]
        restricted_fields = restrict_fields(fields, authorized_fields)
        self.assertEqual(restricted_fields, theoric_fields)

        fields = None
        theoric_fields = ["signature"]
        restricted_fields = restrict_fields(fields, authorized_fields)
        self.assertEqual(restricted_fields, theoric_fields)

        fields = ["nothing"]
        theoric_fields = ["signature"]
        restricted_fields = restrict_fields(fields, authorized_fields)
        self.assertEqual(restricted_fields, theoric_fields)

        self.assertRaises(ValueError, restrict_fields, fields, [])
        self.assertRaises(TypeError, restrict_fields, fields, None)
