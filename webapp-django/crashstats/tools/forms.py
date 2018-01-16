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


class CrashStopDataForm(BaseForm):

    buildid = MultipleValueField(required=True)
    signature = MultipleValueField(required=True)
    product = MultipleValueField(required=True)
    channel = MultipleValueField(required=True)

    def clean(self, s):
        """Remove all empty values from the list """
        value = self.cleaned_data[s]
        return filter(bool, value)

    def clean_product(self):
        """Remove all empty values from the list of products. """
        return self.clean('product')

    def clean_channel(self):
        """Remove all empty values from the list of channels. """
        return self.clean('channel')

    def clean_buildid(self):
        """Remove all empty values from the list of buildids. """
        return self.clean('buildid')

    def clean_signature(self):
        """Remove all empty values from the list of signatures. """
        return self.clean('signature')
