# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

import jsonschema


def test_validate_schemas(reporoot):
    """Validate the schemas are themselves valid jsonschema"""
    path = reporoot / "socorro" / "schemas"

    for fn in path.glob("*.json"):
        print(fn)
        with open(fn) as fp:
            schema = json.load(fp)

        jsonschema.Draft4Validator.check_schema(schema)
