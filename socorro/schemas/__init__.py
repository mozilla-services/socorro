# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

import yaml
from pkg_resources import resource_stream


def get_file_content(filename):
    with resource_stream(__name__, filename) as fp:
        if filename.endswith(".json"):
            schema = json.load(fp)

        elif filename.endswith(".yaml"):
            schema = yaml.load(fp, Loader=yaml.Loader)

    return schema


PROCESSED_CRASH_SCHEMA = get_file_content("processed_crash.schema.yaml")

TELEMETRY_SOCORRO_CRASH_SCHEMA = get_file_content("telemetry_socorro_crash.json")

JAVA_EXCEPTION_SCHEMA = get_file_content("java_exception.json")
