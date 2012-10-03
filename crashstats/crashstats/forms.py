import datetime
from django import forms


class BugInfoForm(forms.Form):

    bug_ids = forms.CharField(required=True)
    include_fields = forms.CharField(required=True)

    def clean_bug_ids(self):
        value = self.cleaned_data['bug_ids']
        return [x.strip() for x in value.split(',') if x.strip()]

    def clean_include_fields(self):
        value = self.cleaned_data['include_fields']
        return [x.strip() for x in value.split(',') if x.strip()]


class ReportListForm(forms.Form):

    range_value = forms.IntegerField(required=True)
    signature = forms.CharField(required=False)
    version = forms.CharField(required=False)
    date = forms.DateField(required=False)

    def clean_date(self):
        value = self.cleaned_data['date']
        if not value:
            value = datetime.datetime.utcnow()
        return value

    def clean_range_value(self):
        value = self.cleaned_data['range_value']
        if value < 0:
            raise forms.ValidationError(
                'range_value must be a positive integer'
            )
        return value
