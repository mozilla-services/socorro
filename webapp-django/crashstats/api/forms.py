from django import forms

from crashstats.crashstats.forms import BaseForm


class NewSignaturesForm(BaseForm):

    end_date = forms.DateField(required=False)
    start_date = forms.DateField(required=False)
    not_after = forms.DateField(required=False)
