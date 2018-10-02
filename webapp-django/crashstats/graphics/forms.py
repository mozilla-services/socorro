from django import forms

from crashstats.crashstats.forms import BaseForm


class GraphicsReportForm(BaseForm):
    date = forms.DateField()
    product = forms.CharField(required=False)
