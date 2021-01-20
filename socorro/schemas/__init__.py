# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json

from pkg_resources import resource_stream


def _get_file_content(filename, parsed=True):
    with resource_stream(__name__, filename) as f:
        if parsed:
            return json.load(f)
        else:
            return f.read()


TELEMETRY_SOCORRO_CRASH_SCHEMA = _get_file_content("telemetry_socorro_crash.json")
TELEMETRY_SOCORRO_CRASH_SCHEMA_AS_STRING = _get_file_content(
    "telemetry_socorro_crash.json", parsed=False
)

JAVA_EXCEPTION_SCHEMA = _get_file_content("java_exception.json")
