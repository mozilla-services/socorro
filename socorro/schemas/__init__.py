# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json
from pathlib import Path

import yaml


def get_file_content(filename):
    path = Path(__file__).parent / filename

    with path.open("rb") as fp:
        if filename.endswith(".json"):
            schema = json.load(fp)

        elif filename.endswith(".yaml"):
            schema = yaml.load(fp, Loader=yaml.Loader)

    return schema


TELEMETRY_SOCORRO_CRASH_SCHEMA = get_file_content("telemetry_socorro_crash.json")
