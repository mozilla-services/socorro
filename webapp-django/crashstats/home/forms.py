from django import forms

from crashstats.crashstats.forms import BaseForm
from crashstats.supersearch.form_fields import MultipleValueField


class HomeForm(BaseForm):

    version = MultipleValueField(required=False)
    days = forms.IntegerField(required=False, min_value=1)

    def clean_days(self):
        return self.cleaned_data['days'] or 7
