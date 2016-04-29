from django import forms

from crashstats.crashstats.forms import BaseForm
from crashstats.supersearch.form_fields import MultipleValueField


class NewSignaturesForm(BaseForm):

    end_date = forms.DateField(required=False)
    start_date = forms.DateField(required=False)
    not_after = forms.DateField(required=False)
    product = MultipleValueField(required=False)
    version = MultipleValueField(required=False)

    def clean_product(self):
        """Remove all empty values from the list of products. """
        value = self.cleaned_data['product']
        return filter(bool, value)
