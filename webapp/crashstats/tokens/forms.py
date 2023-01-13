# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django import forms

from crashstats.crashstats.forms import BaseModelForm
from crashstats.tokens import models


class GenerateTokenForm(BaseModelForm):
    class Meta:
        model = models.Token
        fields = ("permissions", "notes")

    def __init__(self, *args, **kwargs):
        possible_permissions = kwargs.pop("possible_permissions")
        super().__init__(*args, **kwargs)

        if possible_permissions:
            self.fields["permissions"].choices = [
                (x.pk, x.name) for x in possible_permissions
            ]
            self.fields["permissions"].required = False
            self.fields["permissions"].help_text = (
                "Optional. "
                "These are the permissions you have been granted. "
                "You can select one or more."
            )
        else:
            del self.fields["permissions"]
        self.fields["notes"].help_text = "Optional. Entirely for your own records."

    def clean_notes(self):
        value = self.cleaned_data["notes"]
        if len(value) > 2000:
            raise forms.ValidationError("Text too long")
        return value
