from django import forms

from crashstats.crashstats.forms import BaseForm


class SkipListForm(BaseForm):
    category = forms.CharField(required=True)
    rule = forms.CharField(required=True)
