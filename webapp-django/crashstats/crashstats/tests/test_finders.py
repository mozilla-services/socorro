# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import copy

import pytest

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command


class TestLeftoverPipelineFinder:
    """Test our custom staticfiles finder class."""

    def test_missing_css_source_file(self, settings):
        busted_pipeline = copy.deepcopy(settings.PIPELINE)
        # Doesn't matter which key we chose to bust, so let's just
        # pick the first one.
        key = list(busted_pipeline["STYLESHEETS"].keys())[0]
        filenames = busted_pipeline["STYLESHEETS"][key]["source_filenames"]

        # add a junk one
        filenames += ("neverheardof.css",)
        busted_pipeline["STYLESHEETS"][key]["source_filenames"] = filenames

        settings.PIPELINE = busted_pipeline

        with pytest.raises(ImproperlyConfigured):
            call_command("collectstatic", "--noinput", interactive=False)
