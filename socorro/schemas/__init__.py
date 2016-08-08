# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from pkg_resources import resource_stream


def _get_file_content(filename):
    with resource_stream(__name__, filename) as f:
        return json.load(f)

CRASH_REPORT_JSON_SCHEMA = _get_file_content('crash_report.json')
