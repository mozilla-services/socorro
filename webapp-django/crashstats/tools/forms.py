# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

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
        value = self.cleaned_data["product"]
        return list(filter(bool, value))
