import datetime
from nose.tools import eq_, ok_

from django.conf import settings
from django.test import TestCase

from crashstats.crashstats import forms


class TestForms(TestCase):

    def setUp(self):
        # Mocking models needed for form validation
        self.current_products = {
            'Firefox': [],
            'Thunderbird': [],
            'Camino': []
        }
        self.current_versions = [
            {
                'product': 'Firefox',
                'version': '20.0'
            },
            {
                'product': 'Thunderbird',
                'version': '20.0'
            },
            {
                'product': 'Camino',
                'version': '9.5'
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

    def test_report_list(self):

        def get_new_form(data):
            return forms.ReportListForm(
                self.current_products,
                self.current_versions,
                self.current_platforms,
                data
            )

        form = get_new_form({'range_value': '-1'})
        ok_(not form.is_valid())  # missing signature and invalid range

        form = get_new_form({
            'signature': 'sig',
            'range_value': '-1'
        })
        ok_(not form.is_valid())  # invalid range_value

        form = get_new_form({
            'signature': 'sig',
            'product': ['SomeUnkownProduct']
        })
        ok_(not form.is_valid())  # invalid product

        form = get_new_form({
            'signature': 'sig',
            'version': 'invalidVersion'
        })
        ok_(not form.is_valid())  # invalid version

        form = get_new_form({
            'signature': 'sig',
            'version': ['Another:Invalid']
        })
        ok_(not form.is_valid())  # invalid version

        form = get_new_form({
            'signature': 'sig',
            'platform': ['winux']
        })
        ok_(not form.is_valid())  # invalid platform

        form = get_new_form({
            'signature': 'sig',
            'plugin_query_type': 'invalid'
        })
        ok_(not form.is_valid())  # invalid query type

        # Test all valid data
        form = get_new_form({
            'signature': 'sig',
            'product': ['Firefox', 'Camino', 'Thunderbird'],
            'version': ['Firefox:20.0'],
            'platform': ['linux', 'mac'],
            'date': '01/02/2012 12:23:34',
            'range_unit': 'weeks',
            'range_value': 12,
            'reason': 'some reason',
            'build_id': 'some buildid',
            'process_type': 'any',
            'hang_type': 'any',
            'plugin_field': 'name',
            'plugin_query_type': 'is_exactly',
            'plugin_query': 'plugin name'
        })
        ok_(form.is_valid())

        # Test expected types
        ok_(isinstance(form.cleaned_data['date'], datetime.datetime))
        ok_(isinstance(form.cleaned_data['range_value'], int))
        ok_(isinstance(form.cleaned_data['product'], list))
        ok_(isinstance(form.cleaned_data['version'], list))
        ok_(isinstance(form.cleaned_data['platform'], list))

        # Test default values
        form = get_new_form({'signature': 'sig'})
        ok_(form.is_valid())

        ok_(isinstance(form.cleaned_data['date'], datetime.datetime))
        eq_(form.cleaned_data['product'], [settings.DEFAULT_PRODUCT])
        eq_(form.cleaned_data['version'], [])
        eq_(form.cleaned_data['platform'], [])
        eq_(form.cleaned_data['range_unit'], 'weeks')
        eq_(form.cleaned_data['process_type'], 'any')
        eq_(form.cleaned_data['hang_type'], 'any')
        eq_(form.cleaned_data['plugin_field'], 'filename')

    def test_report_list_date(self):

        def get_new_form(data):
            return forms.ReportListForm(
                self.current_products,
                self.current_versions,
                self.current_platforms,
                data
            )

        # known formats
        datetime_ = datetime.datetime(2012, 1, 2, 13, 45, 55)
        date = datetime.datetime(2012, 1, 2, 0, 0)
        data = {'signature': 'sig'}

        fmt = '%Y-%m-%d'
        form = get_new_form(dict(data, date=datetime_.strftime(fmt)))
        ok_(form.is_valid(), form.errors)
        eq_(form.cleaned_data['date'], date)

        fmt = '%m/%d/%Y'  # US format
        form = get_new_form(dict(data, date=datetime_.strftime(fmt)))
        ok_(form.is_valid(), form.errors)
        eq_(form.cleaned_data['date'], date)

        fmt = '%m/%d/%Y %H:%M:%S'  # US format
        form = get_new_form(dict(data, date=datetime_.strftime(fmt)))
        ok_(form.is_valid(), form.errors)
        eq_(form.cleaned_data['date'], datetime_)

    def test_query(self):

        def get_new_form(data):
            return forms.QueryForm(
                self.current_products,
                self.current_versions,
                self.current_platforms,
                data
            )

        form = get_new_form({'query_type': 'invalid'})
        ok_(not form.is_valid())  # invalid query type

        form = get_new_form({'query': u'some %^*@# \xe9 \xf9 chars'})
        ok_(form.is_valid())

    def test_daily_forms(self):
        current_versions = [
            {'product': 'Firefox', 'version': '19.0'},
            {'product': 'Firefox', 'version': '18.0'},
            {'product': 'Thunderbird', 'version': '15.0'},
        ]
        platforms = [
            {'code': 'osx', 'name': 'Mac OS X'},
            {'code': 'windows', 'name': 'Windows'},
        ]
        form = forms.DailyFormByOS(current_versions, platforms)
        ok_(not form.is_valid())  # missing product

        form = forms.DailyFormByOS(
            current_versions,
            platforms,
            data={'p': 'Uhh?'}
        )
        ok_(not form.is_valid())  # invalid product

        form = forms.DailyFormByOS(
            current_versions,
            platforms,
            data={'p': 'Firefox'},
        )
        ok_(form.is_valid())

        form = forms.DailyFormByOS(
            current_versions,
            platforms,
            data={'p': 'Firefox',
                  'v': ['15.0']},
        )
        ok_(not form.is_valid())  # wrong version for that product

        form = forms.DailyFormByOS(current_versions,
                                   platforms,
                                   data={'p': 'Firefox',
                                         'v': ['18.0', '']})
        ok_(form.is_valid())
        eq_(form.cleaned_data['v'], ['18.0'])

        # try DailyFormByVersion with different OS names
        form = forms.DailyFormByVersion(
            current_versions,
            platforms,
            data={'p': 'Firefox',
                  'os': 'unheardof'},
        )
        ok_(not form.is_valid())  # unrecognized os

        form = forms.DailyFormByVersion(
            current_versions,
            platforms,
            data={'p': 'Firefox',
                  'os': ['Windows']},
        )
        ok_(form.is_valid())
        eq_(form.cleaned_data['os'], ['Windows'])
