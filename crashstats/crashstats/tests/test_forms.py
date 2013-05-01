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
                'version': '20.0',
                "release": "Beta"
            },
            {
                'product': 'Firefox',
                'version': '21.0a1',
                "release": "Nightly"
            },
            {
                'product': 'Thunderbird',
                'version': '20.0',
                "release": "Beta",
            },
            {
                'product': 'Camino',
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
        form = get_new_form({'signature': 'sig',
                             'range_unit': 'weeks',
                             'hang_type': 'any',
                             'process_type': 'any',
                             'plugin_field': 'filename'})
        ok_(form.is_valid())

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

    def test_signature_summary(self):

        def get_new_form(data):
            return forms.SignatureSummaryForm(data)

        form = get_new_form({'range_value': '-1'})
        ok_(not form.is_valid())  # missing signature and invalid range

        form = get_new_form({
            'signature': 'sig',
            'range_value': '-1'
        })
        ok_(not form.is_valid())  # invalid range_value

        long_signature = 'x' * (settings.SIGNATURE_MAX_LENGTH + 1)
        form = get_new_form({
            'signature': long_signature,
            'range_unit': 'days',
            'range_value': 12,
        })
        ok_(not form.is_valid())  # signature too long

        # Test all valid data
        form = get_new_form({
            'signature': 'sig',
            'range_unit': 'days',
            'range_value': 12,
        })
        ok_(form.is_valid())

        # Test expected types
        ok_(isinstance(form.cleaned_data['range_value'], int))

        # Test default values
        form = get_new_form({'signature': 'sig'})
        ok_(form.is_valid())

        eq_(form.cleaned_data['range_unit'], 'days')

    def test_crashtrends_json(self):

        now = datetime.datetime.utcnow()
        week_ago = now - datetime.timedelta(days=7)

        def get_new_form(data):
            return forms.CrashTrendsForm(
                self.current_versions,
                data
            )

        form = get_new_form({
            'product': '',
            'version': '19.0',
            'start_date': now,
            'end_date': week_ago
        })
        # All fields are required
        # Testing empty product
        ok_(not form.is_valid())

        form = get_new_form({
            'product': 'Firefox',
            'version': '',
            'start_date': now,
            'end_date': week_ago
        })
        # All fields are required
        # Testing empty version
        ok_(not form.is_valid())

        form = get_new_form({
            'product': 'Firefox',
            'version': '21.0',
            'start_date': '',
            'end_date': '2012-11-02'
        })
        # All fields are required
        # Testing empty start_date
        ok_(not form.is_valid())

        form = get_new_form({
            'product': 'Firefox',
            'version': '19.0',
            'start_date': now,
            'end_date': week_ago
        })
        # Testing invalid product version
        ok_(not form.is_valid())

        form = get_new_form({
            'product': 'Gorilla',
            'version': '19.0',
            'start_date': now,
            'end_date': week_ago
        })
        # Testing invalid product name
        ok_(not form.is_valid())

        form = get_new_form({
            'product': 'Gorilla',
            'version': '20.0',
            'start_date': now,
            'end_date': week_ago
        })
        # Testing valid version, invalid product name
        ok_(not form.is_valid())

        form = get_new_form({
            'product': 'Gorilla',
            'version': '19.0',
            'start_date': now,
            'end_date': 'nodatehere'
        })
        # Testing invalid date
        ok_(not form.is_valid())

        form = get_new_form({
            'product': 'Firefox',
            'version': '21.0a1',
            'start_date': now,
            'end_date': week_ago
        })
        # Testing valid form
        ok_(form.is_valid())

    def test_query(self):

        def get_new_form(data):
            return forms.QueryForm(
                self.current_products,
                self.current_versions,
                self.current_platforms,
                data
            )

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
            'plugin_query': 'plugin name',
            'query_type': 'simple',
            'query': u'some %^*@# \xe9 \xf9 chars'
        })
        ok_(form.is_valid())

    def test_daily_forms(self):

        def get_new_form(cls, data):
            return cls(
                current_versions,
                platforms,
                date_range_types=['foo', 'bar'],
                hang_types=['xxx', 'yyy'],
                data=data
            )

        current_versions = [
            {'product': 'WaterWolf', 'version': '19.0'},
            {'product': 'WaterWolf', 'version': '18.0'},
            {'product': 'NightTrain', 'version': '15.0'},
        ]
        platforms = [
            {'code': 'osx', 'name': 'Mac OS X'},
            {'code': 'windows', 'name': 'Windows'},
        ]
        form = get_new_form(forms.DailyFormByOS, {})
        ok_(not form.is_valid())  # missing product

        form = get_new_form(forms.DailyFormByOS, {'p': 'Uhh?'})
        ok_(not form.is_valid())  # invalid product

        form = get_new_form(forms.DailyFormByOS, {'p': 'WaterWolf'})
        ok_(form.is_valid())

        form = get_new_form(
            forms.DailyFormByOS,
            {'p': 'WaterWolf',
             'v': ['15.0']}
        )
        ok_(not form.is_valid())  # wrong version for that product

        form = get_new_form(
            forms.DailyFormByOS,
            {'p': 'WaterWolf',
             'v': ['18.0', '']}
        )
        ok_(form.is_valid())
        eq_(form.cleaned_data['v'], ['18.0'])

        # try DailyFormByVersion with different OS names
        form = get_new_form(
            forms.DailyFormByVersion,
            {'p': 'WaterWolf',
             'os': 'unheardof'},
        )
        ok_(not form.is_valid())  # unrecognized os

        form = get_new_form(
            forms.DailyFormByVersion,
            {'p': 'WaterWolf',
             'os': ['Windows']},
        )
        ok_(form.is_valid())
        eq_(form.cleaned_data['os'], ['Windows'])

    def test_buginfoform(self):

        def get_new_form(data):
            return forms.BugInfoForm(data)

        form = get_new_form({})
        ok_(not form.is_valid())  # missing both

        form = get_new_form({'include_fields': 'foo,bar'})
        ok_(not form.is_valid())  # missing bug_ids

        form = get_new_form({'bug_ids': '456,123'})
        ok_(not form.is_valid())  # missing include_fields

        form = get_new_form({'bug_ids': '456, not a bug',
                             'include_fields': 'foo'})
        ok_(not form.is_valid())  # invalid bug_id

        form = get_new_form({'bug_ids': '123', 'include_fields': 'foo,&123'})
        ok_(not form.is_valid())  # invalid include field

        form = get_new_form({'bug_ids': '123 , 345 ,, 100',
                             'include_fields': 'foo_1 ,, bar_2 '})
        ok_(form.is_valid())
        eq_(form.cleaned_data['bug_ids'], ['123', '345', '100'])
        eq_(form.cleaned_data['include_fields'], ['foo_1', 'bar_2'])
