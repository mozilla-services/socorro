import datetime
from nose.tools import eq_, ok_
from django.test import TestCase
from crashstats.crashstats import forms


class TestForms(TestCase):

    def test_report_list(self):
        form = forms.ReportListForm({})
        ok_(not form.is_valid())  # missing range_value

        form = forms.ReportListForm({'range_value': '-1'})
        ok_(not form.is_valid())  # invalid range_value

        form = forms.ReportListForm({'range_value': '1'})
        ok_(form.is_valid())

        ok_(isinstance(form.cleaned_data['date'], datetime.datetime))

    def test_report_list_date(self):
        # known formats
        date = datetime.date(2012, 1, 2)
        data = {'range_value': 1}

        fmt = '%Y-%m-%d'
        form = forms.ReportListForm(dict(data, date=date.strftime(fmt)))
        ok_(form.is_valid(), form.errors)
        eq_(form.cleaned_data['date'], date)

        fmt = '%m/%d/%Y'  # US format
        form = forms.ReportListForm(dict(data, date=date.strftime(fmt)))
        ok_(form.is_valid(), form.errors)
        eq_(form.cleaned_data['date'], date)
