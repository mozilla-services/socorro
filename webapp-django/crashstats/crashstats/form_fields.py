# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from django import forms
from django.conf import settings


class SignatureField(forms.CharField):
    # to use whenever you need a `signature` field

    def __init__(self, *args, **kwargs):
        if not kwargs.get('max_length'):
            kwargs['max_length'] = settings.SIGNATURE_MAX_LENGTH
        super(SignatureField, self).__init__(*args, **kwargs)


class BuildIdsField(forms.IntegerField):
    '''Handle specific validation rules for `build_id` fields.

    Accept one or several integers separated by commas, and returns a list.
    '''

    def to_python(self, value):
        if not value:
            return None

        return [
            super(BuildIdsField, self).to_python(x.strip())
            for x in value.split(',') if x.strip()
        ]

    def clean(self, value, *args, **kwargs):
        value = self.to_python(value)

        if value is None:
            self.validate(value)
            self.run_validators(value)
            return value

        cleaned_values = []
        for val in value:
            self.validate(val)
            self.run_validators(val)
            cleaned_values.append(val)

        return cleaned_values
