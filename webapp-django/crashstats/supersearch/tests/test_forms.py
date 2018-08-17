from crashstats.base.tests.testbase import TestCase
from crashstats.supersearch import forms
from socorro.external.es.super_search_fields import FIELDS


class TestForms(TestCase):

    def setUp(self):
        self.products = [
            {
                'product_name': 'WaterWolf',
            },
            {
                'product_name': 'NightTrain',
            },
            {
                'product_name': 'SeaMonkey',
            },
            {
                'product_name': 'Tinkerbell',
            }
        ]
        self.product_versions = [
            {
                'product': 'WaterWolf',
                'version': '20.0',
                'build_type': 'Beta',
            },
            {
                'product': 'WaterWolf',
                'version': '21.0a1',
                'build_type': 'Nightly',
            },
            {
                'product': 'NightTrain',
                'version': '20.0',
                'build_type': 'Beta',
            },
            {
                'product': 'SeaMonkey',
                'version': '9.5',
                'build_type': 'Beta',
            },
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
        self.all_fields = FIELDS

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
                self.products,
                self.product_versions,
                self.current_platforms,
                User(),
                data
            )

        form = get_new_form({
            'product': 'WaterWolf'
        })
        # expect values as lists
        assert not form.is_valid()

        form = get_new_form({
            'date': '2012-01-16 12:23:34324234'
        })
        # invalid datetime
        assert not form.is_valid()

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
        assert form.is_valid()

        # Verify admin restricted fields are not accepted
        form = get_new_form({
            'email': 'something',
            'exploitability': 'high'
        })
        assert form.is_valid()
        assert 'email' not in form.fields
        assert 'exploitability' not in form.fields

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
                self.products,
                self.product_versions,
                self.current_platforms,
                User(),
                data
            )

        form = get_new_form({
            'product': 'WaterWolf'
        })
        # expect values as lists
        assert not form.is_valid()

        form = get_new_form({
            'date': '2012-01-16 12:23:34324234'
        })
        # invalid datetime
        assert not form.is_valid()

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
        assert form.is_valid()

        # Verify admin restricted fields are accepted
        assert 'email' in form.fields
        assert 'url' in form.fields
        assert 'exploitability' in form.fields

    def test_get_fields_list(self):

        def get_new_form(data):

            class User(object):
                def has_perm(self, permission):
                    return {
                        'crashstats.view_pii': False,
                        'crashstats.view_exploitability': False,
                    }.get(permission, False)

            return forms.SearchForm(
                self.all_fields,
                self.products,
                self.product_versions,
                self.current_platforms,
                User(),
                data
            )

        form = get_new_form({})
        assert form.is_valid()

        fields = form.get_fields_list()
        assert 'version' in fields

        # Verify there's only one occurence of the version.
        assert fields['version']['values'].count('20.0') == 1
