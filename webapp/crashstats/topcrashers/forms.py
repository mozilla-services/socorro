# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django import forms

from crashstats.supersearch.form_fields import MultipleValueField
from crashstats.crashstats.forms import BaseForm


class TopCrashersForm(BaseForm):
    product = forms.CharField()
    version = MultipleValueField(required=False)
    process_type = forms.CharField(required=False)
    platform = forms.CharField(required=False)
    _facets_size = forms.IntegerField(required=False)
    _tcbs_mode = forms.CharField(required=False)
    _range_type = forms.CharField(required=False)

    # NOTE(willkg): _report_type choices must match the TopCrashers form options in the
    # jinja2 template
    _report_type = forms.ChoiceField(
        choices=[("any", "any"), ("hang", "hang"), ("crash", "crash")],
        required=False,
    )
