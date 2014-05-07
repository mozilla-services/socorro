# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import datetime

from nose.tools import eq_, ok_, assert_raises
from configman import ConfigurationManager, Namespace

from socorro.external import BadArgumentError
from socorro.lib import datetimeutil
from socorro.lib.search_common import (
    SearchBase, SearchParam, convert_to_type, get_parameters, restrict_fields
)
from socorro.unittest.testbase import TestCase


SUPERSEARCH_FIELDS_MOCKED_RESULTS = {
    'signature': {
        'name': 'signature',
        'data_validation_type': 'str',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'product': {
        'name': 'product',
        'data_validation_type': 'enum',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'version': {
        'name': 'version',
        'data_validation_type': 'enum',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'date': {
        'name': 'date',
        'data_validation_type': 'datetime',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'build_id': {
        'name': 'build_id',
        'data_validation_type': 'int',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'process_type': {
        'name': 'process_type',
        'data_validation_type': 'enum',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'hang_type': {
        'name': 'hang_type',
        'data_validation_type': 'enum',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
    'user_comments': {
        'name': 'user_comments',
        'data_validation_type': 'str',
        'namespace': 'processed_crash',
        'permissions_needed': [],
        'default_value': None,
        'is_exposed': True,
        'is_returned': True,
        'is_mandatory': False,
    },
}


def _get_config_manager():
    required_config = Namespace()

    webapi = Namespace()
    webapi.search_default_date_range = 7
    webapi.search_maximum_date_range = 365

    required_config.webapi = webapi

    config_manager = ConfigurationManager(
        [required_config],
        app_name='testapp',
        app_version='1.0',
        app_description='app description',
        argv_source=[]
    )

    return config_manager


class TestSearchBase(TestCase):

    def test_get_parameters(self):
        with _get_config_manager().context() as config:
            search = SearchBase(
                config=config,
                fields=SUPERSEARCH_FIELDS_MOCKED_RESULTS,
            )

        args = {
            'signature': 'mysig',
            'product': 'WaterWolf',
            'version': '1.0',
        }
        params = search.get_parameters(**args)
        for i in ('signature', 'product', 'version'):
            ok_(i in params)
            ok_(isinstance(params[i], list))
            ok_(isinstance(params[i][0], SearchParam))
            eq_(params[i][0].operator, '')

        args = {
            'signature': '~js',
            'product': ['WaterWolf', 'NightTrain'],
            'version': '=1.0',
        }
        params = search.get_parameters(**args)
        eq_(params['signature'][0].operator, '~')
        eq_(params['signature'][0].value, 'js')
        eq_(params['product'][0].operator, '')
        # Test that params with no operator are stacked
        eq_(
            params['product'][0].value,
            ['WaterWolf', 'NightTrain']
        )
        eq_(params['version'][0].operator, '')

        args = {
            'signature': ['~Mark', '$js'],
        }
        params = search.get_parameters(**args)
        eq_(params['signature'][0].operator, '~')
        eq_(params['signature'][0].value, 'Mark')
        eq_(params['signature'][1].operator, '$')
        eq_(params['signature'][1].value, 'js')

        args = {
            'build_id': ['>20000101000000', '<20150101000000'],
        }
        params = search.get_parameters(**args)
        eq_(params['build_id'][0].operator, '>')
        eq_(params['build_id'][0].value, 20000101000000)
        eq_(params['build_id'][1].operator, '<')
        eq_(params['build_id'][1].value, 20150101000000)

    def test_get_parameters_with_not(self):
        with _get_config_manager().context() as config:
            search = SearchBase(
                config=config,
                fields=SUPERSEARCH_FIELDS_MOCKED_RESULTS,
            )

        args = {
            'signature': '!~mysig',
            'product': '!WaterWolf',
            'version': '1.0',
            'user_comments': '!__null__',
        }
        params = search.get_parameters(**args)
        eq_(params['signature'][0].operator, '~')
        ok_(params['signature'][0].operator_not)
        eq_(params['signature'][0].value, 'mysig')

        eq_(params['product'][0].operator, '')
        ok_(params['product'][0].operator_not)

        eq_(params['version'][0].operator, '')
        ok_(not params['version'][0].operator_not)

        eq_(params['user_comments'][0].operator, '__null__')
        ok_(params['user_comments'][0].operator_not)

    def test_get_parameters_date_defaults(self):
        with _get_config_manager().context() as config:
            search = SearchBase(
                config=config,
                fields=SUPERSEARCH_FIELDS_MOCKED_RESULTS,
            )

        now = datetimeutil.utc_now()

        # Test default values when nothing is passed
        params = search.get_parameters()
        ok_('date' in params)
        eq_(len(params['date']), 2)

        # Pass only the high value
        args = {
            'date': '<%s' % datetimeutil.date_to_string(now)
        }
        params = search.get_parameters(**args)
        ok_('date' in params)
        eq_(len(params['date']), 2)
        eq_(params['date'][0].operator, '<')
        eq_(params['date'][1].operator, '>=')
        eq_(params['date'][0].value.date(), now.date())
        eq_(
            params['date'][1].value.date(),
            now.date() - datetime.timedelta(days=7)
        )

        # Pass only the low value
        pasttime = now - datetime.timedelta(days=10)
        args = {
            'date': '>=%s' % datetimeutil.date_to_string(pasttime)
        }
        params = search.get_parameters(**args)
        ok_('date' in params)
        eq_(len(params['date']), 2)
        eq_(params['date'][0].operator, '<=')
        eq_(params['date'][1].operator, '>=')
        eq_(params['date'][0].value.date(), now.date())
        eq_(params['date'][1].value.date(), pasttime.date())

        # Pass the two values
        pasttime = now - datetime.timedelta(days=10)
        args = {
            'date': [
                '<%s' % datetimeutil.date_to_string(now),
                '>%s' % datetimeutil.date_to_string(pasttime),
            ]
        }
        params = search.get_parameters(**args)
        ok_('date' in params)
        eq_(len(params['date']), 2)
        eq_(params['date'][0].operator, '<')
        eq_(params['date'][1].operator, '>')
        eq_(params['date'][0].value.date(), now.date())
        eq_(params['date'][1].value.date(), pasttime.date())

    def test_get_parameters_date_max_range(self):
        with _get_config_manager().context() as config:
            search = SearchBase(
                config=config,
                fields=SUPERSEARCH_FIELDS_MOCKED_RESULTS,
            )

        assert_raises(
            BadArgumentError,
            search.get_parameters,
            date='>1999-01-01'
        )

    def test_process_type_parameter_correction(self):
        with _get_config_manager().context() as config:
            search = SearchBase(
                config=config,
                fields=SUPERSEARCH_FIELDS_MOCKED_RESULTS,
            )

        args = {
            'process_type': 'browser'
        }
        params = search.get_parameters(**args)
        ok_('process_type' in params)
        eq_(len(params['process_type']), 1)
        eq_(params['process_type'][0].value, [''])
        eq_(params['process_type'][0].operator, '__null__')
        eq_(params['process_type'][0].operator_not, False)

    def test_hang_type_parameter_correction(self):
        with _get_config_manager().context() as config:
            search = SearchBase(
                config=config,
                fields=SUPERSEARCH_FIELDS_MOCKED_RESULTS,
            )

        args = {
            'hang_type': 'hang'
        }
        params = search.get_parameters(**args)
        ok_('hang_type' in params)
        eq_(len(params['hang_type']), 1)
        eq_(params['hang_type'][0].value, [-1, 1])

        args = {
            'hang_type': 'crash'
        }
        params = search.get_parameters(**args)
        ok_('hang_type' in params)
        eq_(len(params['hang_type']), 1)
        eq_(params['hang_type'][0].value, [0])


#==============================================================================
class TestSearchCommon(TestCase):
    """Test functions of the search_common module. """

    def test_convert_to_type(self):
        # Test null
        res = convert_to_type(None, 'datetime')
        ok_(res is None)

        # Test integer
        res = convert_to_type(12, 'int')
        ok_(isinstance(res, int))
        eq_(res, 12)

        # Test integer
        res = convert_to_type('12', 'int')
        ok_(isinstance(res, int))
        eq_(res, 12)

        # Test string
        res = convert_to_type(datetime.datetime(2012, 1, 1), 'str')
        ok_(isinstance(res, str))
        eq_(res, '2012-01-01 00:00:00')

        # Test boolean
        res = convert_to_type(1, 'bool')
        ok_(isinstance(res, bool))
        ok_(res)

        # Test boolean
        res = convert_to_type('T', 'bool')
        ok_(isinstance(res, bool))
        ok_(res)

        # Test boolean
        res = convert_to_type(14, 'bool')
        ok_(isinstance(res, bool))
        ok_(not res)

        # Test datetime
        res = convert_to_type('2012-01-01T12:23:34', 'datetime')
        ok_(isinstance(res, datetime.datetime))
        eq_(res.year, 2012)
        eq_(res.month, 1)
        eq_(res.hour, 12)

        # Test date
        res = convert_to_type('2012-01-01T00:00:00', 'date')
        ok_(isinstance(res, datetime.date))
        eq_(res.year, 2012)
        eq_(res.month, 1)

        # Test error
        assert_raises(ValueError, convert_to_type, 'abds', 'int')
        assert_raises(ValueError, convert_to_type, '2013-02-32', 'date')

    #--------------------------------------------------------------------------
    def test_get_parameters(self):
        """
        Test search_common.get_parameters()
        """
        # Empty params, only default values are returned
        params = get_parameters({})
        ok_(params)

        for i in params:
            typei = type(params[i])
            if i in ("from_date", "to_date", "build_from", "build_to"):
                ok_(typei is datetime.datetime)
            else:
                ok_(
                    not params[i] or
                    typei is int or
                    typei is str or
                    typei is list
                )

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
                ok_(typei is datetime.datetime)
            else:
                ok_(
                    not params[i] or
                    typei is int or
                    typei is str or
                    typei is list
                )

        # Test with encoded slashes in terms and signature
        params = get_parameters({
            "terms": ["some", "terms/sig"],
            "signature": "my/little/signature"
        })

        ok_("signature" in params)
        ok_("terms" in params)
        eq_(params["terms"], ["some", "terms/sig"])
        eq_(params["signature"], "my/little/signature")

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
        eq_(restricted_fields, theoric_fields)

        fields = []
        theoric_fields = ["signature"]
        restricted_fields = restrict_fields(fields, authorized_fields)
        eq_(restricted_fields, theoric_fields)

        fields = None
        theoric_fields = ["signature"]
        restricted_fields = restrict_fields(fields, authorized_fields)
        eq_(restricted_fields, theoric_fields)

        fields = ["nothing"]
        theoric_fields = ["signature"]
        restricted_fields = restrict_fields(fields, authorized_fields)
        eq_(restricted_fields, theoric_fields)

        assert_raises(ValueError, restrict_fields, fields, [])
        assert_raises(TypeError, restrict_fields, fields, None)
