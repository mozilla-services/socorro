from nose.tools import ok_

from crashstats.base.tests.testbase import TestCase
from crashstats.supersearch import forms
from crashstats.supersearch.tests.test_views import (
    SUPERSEARCH_FIELDS_MOCKED_RESULTS
)


class TestForms(TestCase):

    def setUp(self):
        # Mocking models needed for form validation.
        self.current_products = {
            'WaterWolf': [],
            'NightTrain': [],
            'SeaMonkey': []
        }
        self.current_versions = [
            {
                'product': 'WaterWolf',
                'version': '20.0',
                "release": "Beta"
            },
            {
                'product': 'WaterWolf',
                'version': '21.0a1',
                "release": "Nightly"
            },
            {
                'product': 'NightTrain',
                'version': '20.0',
                "release": "Beta",
            },
            {
                'product': 'SeaMonkey',
                'version': '9.5',
                "release": "Beta"
            }
        ]
        self.current_platforms = [
            {
                'code': 'windows',
                'name': 'Windows'
            },
            {
                'code': 'mac',
                'name': 'Mac OS X'
            },
            {
                'code': 'linux',
                'name': 'Linux'
            }
        ]
        self.all_fields = SUPERSEARCH_FIELDS_MOCKED_RESULTS

    def test_search_form(self):

        def get_new_form(data):

            class User(object):
                def has_perm(self, permission):
                    return {
                        'crashstats.view_pii': False,
                        'crashstats.view_exploitability': False,
                    }.get(permission, False)

            return forms.SearchForm(
                self.all_fields,
                self.current_products,
                self.current_versions,
                self.current_platforms,
                User(),
                data
            )

        form = get_new_form({
            'product': 'WaterWolf'
        })
        ok_(not form.is_valid())  # expect values as lists

        form = get_new_form({
            'date': '2012-01-16 12:23:34324234'
        })
        ok_(not form.is_valid())  # invalid datetime

        # Test all valid data
        form = get_new_form({
            'signature': ['~sig'],
            'product': ['WaterWolf', 'SeaMonkey', 'NightTrain'],
            'version': ['20.0'],
            'platform': ['Linux', 'Mac OS X'],
            'date': ['>2012-01-16 12:23:34', '<=2013-01-16 12:23:34'],
            'reason': ['some reason'],
            'build_id': '<20200101344556',
        })
        ok_(form.is_valid(), form.errors)

        # Verify admin restricted fields are not accepted
        form = get_new_form({
            'email': 'something',
            'exploitability': 'high'
        })
        ok_(form.is_valid(), form.errors)
        ok_('email' not in form.fields)
        ok_('exploitability' not in form.fields)

    def test_search_form_with_admin_mode(self):

        def get_new_form(data):

            class User(object):
                def has_perm(self, permission):
                    return {
                        'crashstats.view_pii': True,
                        'crashstats.view_exploitability': True,
                    }.get(permission, False)

            return forms.SearchForm(
                self.all_fields,
                self.current_products,
                self.current_versions,
                self.current_platforms,
                User(),
                data
            )

        form = get_new_form({
            'product': 'WaterWolf'
        })
        ok_(not form.is_valid())  # expect values as lists

        form = get_new_form({
            'date': '2012-01-16 12:23:34324234'
        })
        ok_(not form.is_valid())  # invalid datetime

        # Test all valid data
        form = get_new_form({
            'signature': ['~sig'],
            'product': ['WaterWolf', 'SeaMonkey', 'NightTrain'],
            'version': ['20.0'],
            'platform': ['Linux', 'Mac OS X'],
            'date': ['>2012-01-16 12:23:34', '<=2013-01-16 12:23:34'],
            'reason': ['some reason'],
            'build_id': '<20200101344556',
            'email': ['^mail.com'],
            'url': ['$http://'],
            'exploitability': ['high', 'medium'],
        })
        ok_(form.is_valid(), form.errors)

        # Verify admin restricted fields are accepted
        ok_('email' in form.fields)
        ok_('url' in form.fields)
        ok_('exploitability' in form.fields)
