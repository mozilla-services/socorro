import datetime
from nose.tools import eq_, ok_

from crashstats.base.tests.testbase import DjangoTestCase
from crashstats.crashstats import forms


class TestForms(DjangoTestCase):

    def setUp(self):
        super(TestForms, self).setUp()
        self.active_versions = {
            'WaterWolf': [
                {'version': '20.0', 'build_type': 'Beta'},
                {'version': '21.0a1', 'build_type': 'Nightly'},
            ],
            'NightTrain': [
                {'version': '20.0', 'build_type': 'Beta'},
            ],
            'SeaMonkey': [
                {'version': '9.5', 'build_type': 'Beta'},
            ],
        }

        self.current_channels = (
            'release',
            'beta',
            'aurora',
            'nightly',
            'esr'
        )

    def test_daily_forms(self):

        def get_new_form(cls, data):
            return cls(
                active_versions,
                platforms,
                date_range_types=['foo', 'bar'],
                hang_types=['xxx', 'yyy'],
                data=data
            )

        active_versions = {
            'WaterWolf': [{'version': '19.0'}, {'version': '18.0'}],
            'NightTrain': [{'version': '15.0'}],
        }
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

        # test the start_date and end_date invariance
        today = datetime.datetime.utcnow()
        form = get_new_form(
            forms.DailyFormByVersion,
            {'p': 'WaterWolf',
             'date_start': today + datetime.timedelta(days=1),
             'date_end': today},
        )
        ok_(not form.is_valid())
        ok_('Start date greater than end date' in str(form.errors))
        # but should be OK to be equal
        form = get_new_form(
            forms.DailyFormByVersion,
            {'p': 'WaterWolf',
             'date_start': today,
             'date_end': today},
        )
        ok_(form.is_valid())

        # Test that the start or end date are not in the future
        form = get_new_form(
            forms.DailyFormByVersion,
            {'p': 'WaterWolf',
             'date_start': today,
             'date_end': today + datetime.timedelta(days=1)},
        )
        ok_(not form.is_valid())

    def test_buginfoform(self):

        def get_new_form(data):
            return forms.BugInfoForm(data)

        form = get_new_form({})
        ok_(not form.is_valid())  # missing bug_ids

        form = get_new_form({'bug_ids': '456, not a bug'})
        ok_(not form.is_valid())  # invalid bug_ids

        form = get_new_form({'bug_ids': '123 , 345 ,, 100'})
        ok_(form.is_valid())
        eq_(form.cleaned_data['bug_ids'], ['123', '345', '100'])
