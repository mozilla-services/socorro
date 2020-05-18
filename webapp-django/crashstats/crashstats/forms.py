# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django import forms


class _BaseForm:
    def clean(self):
        cleaned_data = super().clean()
        for field in cleaned_data:
            if isinstance(cleaned_data[field], str):
                cleaned_data[field] = (
                    cleaned_data[field]
                    .replace("\r\n", "\n")
                    .replace("\u2018", "'")
                    .replace("\u2019", "'")
                    .strip()
                )

        return cleaned_data


class BaseModelForm(_BaseForm, forms.ModelForm):
    pass


class BaseForm(_BaseForm, forms.Form):
    pass


class BugInfoForm(BaseForm):
    bug_ids = forms.CharField(required=True)

    def clean_bug_ids(self):
        value = self.cleaned_data["bug_ids"]
        bug_ids = [x.strip() for x in value.split(",") if x.strip()]
        nasty_bug_ids = [x for x in bug_ids if not x.isdigit()]
        if nasty_bug_ids:
            # all were invalid
            raise forms.ValidationError(
                "Not valid bug_ids %s" % (", ".join(repr(x) for x in nasty_bug_ids))
            )
        return bug_ids
