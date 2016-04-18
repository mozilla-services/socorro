import datetime
from nose.tools import eq_, ok_

from django.conf import settings
from django.utils.timezone import utc

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

    def test_report_list(self):

        def get_new_form(data):
            return forms.ReportListForm(
                self.active_versions,
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
            'plugin_query_type': 'invalid'
        })
        ok_(not form.is_valid())  # invalid query type

        form = get_new_form({
            'signature': 'sig',
            'product': ['WaterWolf'],
            'version': ['NightTrain:20.0']
        })
        ok_(not form.is_valid())  # invalid product combo

        # Test all valid data
        form = get_new_form({
            'signature': 'sig',
            'product': ['WaterWolf', 'SeaMonkey', 'NightTrain'],
            'version': ['WaterWolf:20.0'],
            'date': '01/02/2012 12:23:34',
            'range_unit': 'weeks',
            'range_value': 12,
            'reason': 'some reason',
            'build_id': '20200101344556',
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

        # Test default values
        form = get_new_form({'signature': 'sig',
                             'range_unit': 'weeks',
                             'hang_type': 'any',
                             'process_type': 'any',
                             'plugin_field': 'filename'})
        ok_(form.is_valid())

        eq_(form.cleaned_data['product'], [])
        eq_(form.cleaned_data['version'], [])
        eq_(form.cleaned_data['range_unit'], 'weeks')
        eq_(form.cleaned_data['process_type'], 'any')
        eq_(form.cleaned_data['hang_type'], 'any')
        eq_(form.cleaned_data['plugin_field'], 'filename')

    def test_report_list_date(self):

        def get_new_form(data):
            return forms.ReportListForm(
                self.active_versions,
                data
            )

        # known formats
        datetime_ = datetime.datetime(2012, 1, 2, 13, 45, 55)
        datetime_ = datetime_.replace(tzinfo=utc)
        date = datetime.datetime(2012, 1, 2, 0, 0)
        date = date.replace(tzinfo=utc)
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
            return forms.SignatureSummaryForm(
                self.active_versions,
                data,
            )

        form = get_new_form({'range_value': '-1'})
        ok_(not form.is_valid())  # missing signature and invalid range

        form = get_new_form({
            'signature': 'sig',
            'range_value': '-1',
            'versions': 'WaterWolf:19.0',
        })
        ok_(not form.is_valid())  # invalid range_value

        long_signature = 'x' * (settings.SIGNATURE_MAX_LENGTH + 1)
        form = get_new_form({
            'signature': long_signature,
            'range_unit': 'days',
            'range_value': 12,
            'versions': 'WaterWolf:19.0',
        })
        ok_(not form.is_valid())  # signature too long

        # Test all valid data
        form = get_new_form({
            'signature': 'sig',
            'range_unit': 'days',
            'range_value': 12,
            'versions': 'WaterWolf:19.0',
        })
        ok_(form.is_valid())

        # Test expected types
        ok_(isinstance(form.cleaned_data['range_value'], int))

        # Test default values
        form = get_new_form({'signature': 'sig'})
        ok_(form.is_valid())

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

    def test_adubysignature_form(self):

        def get_new_form(data):
            return forms.ADUBySignatureJSONForm(
                self.current_channels,
                self.active_versions,
                data
            )

        start_date = datetime.datetime.utcnow() - datetime.timedelta(days=7)
        end_date = datetime.datetime.utcnow()
        form = get_new_form({
            'product_name': 'WaterWolf',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'signature': 'the-signatu(re)',
            'channel': 'nightly'
        })
        ok_(form.is_valid())  # all is good

        form = get_new_form({
            'product_name': '',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'signature': 'the-signatu(re)',
            'channel': 'nightly'
        })
        ok_(not form.is_valid())  # no product provided

        form = get_new_form({
            'product_name': 'SuckerFish',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'signature': 'the-signatu(re)',
            'channel': 'nightly'
        })
        ok_(not form.is_valid())  # invalid product

        form = get_new_form({
            'product_name': 'WaterWolf',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'signature': '',
            'channel': 'nightly'
        })
        ok_(not form.is_valid())  # empty signature

        form = get_new_form({
            'product_name': 'WaterWolf',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'signature': 'the-signatu(re)',
            'channel': 'dooky'
        })
        ok_(not form.is_valid())  # invalid channel

        form = get_new_form({
            'product_name': 'WaterWolf',
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'signature': 'the-signatu(re)',
            'channel': ''
        })
        ok_(not form.is_valid())  # no channel provided

        form = get_new_form({
            'product_name': 'WaterWolf',
            'channel': 'nightly',
            'signature': 'the-signatu(re)',
            'start_date': '2013-02-33',
            'end_date': '2013-01-02'
        })
        ok_(not form.is_valid())  # not a valid date

        form = get_new_form({
            'product_name': 'WaterWolf',
            'channel': 'nightly',
            'signature': 'the-signatu(re)',
            'start_date': '2013-02-13',
            'end_date': '2013-01-44'
        })
        ok_(not form.is_valid())  # not a valid date

        form = get_new_form({
            'product_name': 'WaterWolf',
            'channel': 'nightly',
            'signature': 'the-signatu(re)',
            'start_date': '2013-02-02',
            'end_date': '2013-01-01'
        })
        ok_(not form.is_valid())  # start_date > end_date

        future_date = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        form = get_new_form({
            'product_name': 'WaterWolf',
            'channel': 'nightly',
            'signature': 'the-signatu(re)',
            'start_date': future_date.strftime('%Y-%m-%d'),
            'end_date': '2013-01-01'
        })
        ok_(not form.is_valid())  # start_date in the future

        form = get_new_form({
            'product_name': 'WaterWolf',
            'channel': 'nightly',
            'signature': 'the-signatu(re)',
            'start_date': '2013-02-02',
            'end_date': future_date.strftime('%Y-%m-%d')
        })
        ok_(not form.is_valid())  # end_date in the future

    def test_gcrashes_form(self):

        def get_new_form(data):
            nightly_versions = {}
            for product in self.active_versions:
                if product not in nightly_versions:
                    nightly_versions[product] = []
                for version in self.active_versions[product]:
                    if version['build_type'].lower() == 'nightly':
                        nightly_versions[product].append(version['version'])
            return forms.GCCrashesForm(
                data,
                nightly_versions=nightly_versions
            )

        form = get_new_form({
            'product': '',
            'version': '21.0a1',
            'start_date': '2013-01-01',
            'end_date': '2013-01-02'
        })
        ok_(not form.is_valid())  # no product specified

        form = get_new_form({
            'product': 'WaterWolf',
            'version': '',
            'start_date': '2013-01-01',
            'end_date': '2013-01-02'
        })
        ok_(not form.is_valid())  # no version specified

        form = get_new_form({
            'product': 'WaterWolf',
            'version': '19.0',
            'start_date': '2013-01-01',
            'end_date': '2013-01-02'
        })
        ok_(not form.is_valid())  # invalid version specified

        form = get_new_form({
            'product': 'LandCrab',
            'version': '21.0a1',
            'start_date': '2013-01-01',
            'end_date': '2013-01-02'
        })
        ok_(not form.is_valid())  # invalid product specified

        form = get_new_form({})
        ok_(not form.is_valid())  # missing both

        form = get_new_form({
            'product': 'WaterWolf',
            'version': '21.0a1',
            'start_date': '2013-02-33',
            'end_date': '2013-01-02'
        })
        ok_(not form.is_valid())  # not a valid date

        form = get_new_form({
            'product': 'WaterWolf',
            'version': '21.0a1',
            'start_date': '2013-02-13',
            'end_date': '2013-01-44'
        })
        ok_(not form.is_valid())  # not a valid date

        form = get_new_form({
            'product': 'WaterWolf',
            'version': '21.0a1',
            'start_date': '2013-02-02',
            'end_date': '2013-01-01'
        })
        ok_(not form.is_valid())  # start_date > end_date

        future_date = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        form = get_new_form({
            'product': 'WaterWolf',
            'version': '21.0a1',
            'start_date': future_date.strftime('%Y-%m-%d'),
            'end_date': '2013-01-01'
        })
        ok_(not form.is_valid())  # start_date in the future

        form = get_new_form({
            'product': 'WaterWolf',
            'version': '21.0a1',
            'start_date': '2013-02-02',
            'end_date': future_date.strftime('%Y-%m-%d')
        })
        ok_(not form.is_valid())  # end_date in the future

        form = get_new_form({
            'product': 'WaterWolf',
            'version': '21.0a1',
            'start_date': '2013-01-01',
            'end_date': '2013-01-02'
        })
        ok_(form.is_valid())  # should be fine
