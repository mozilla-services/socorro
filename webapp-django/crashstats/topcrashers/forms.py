from django import forms

from crashstats.supersearch.form_fields import MultipleValueField
from crashstats.crashstats.forms import BaseForm


class TopCrashersForm(BaseForm):
    product = forms.CharField()
    version = MultipleValueField(required=False)
    process_type = forms.CharField(required=False)
    platform = forms.CharField(required=False)
    _facets_size = forms.IntegerField(required=False)
    _tcbs_mode = forms.CharField(required=False)
    _range_type = forms.CharField(required=False)
