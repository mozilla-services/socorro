from django import forms
from django.conf import settings

from crashstats.crashstats.forms import BaseForm
from crashstats.supersearch.form_fields import MultipleValueField


class NewSignaturesForm(BaseForm):

    end_date = forms.DateField(required=False)
    start_date = forms.DateField(required=False)
    not_after = forms.DateField(required=False)
    product = MultipleValueField(required=False)
    version = MultipleValueField(required=False)

    def clean_product(self):
        """By default, we want the product to be set to something, it should
        not be empty. """
        value = self.cleaned_data['product']
        value = filter(bool, value)  # Remove all empty values.

        if not value:
            value = settings.DEFAULT_PRODUCT

        return value
