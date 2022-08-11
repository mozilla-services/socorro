# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import jsonschema

from socorro.lib.libjson import traverse_schema
from socorro.schemas import get_file_content, PROCESSED_CRASH_SCHEMA


def test_validate_schemas(reporoot):
    """Validate the schemas are themselves valid jsonschema"""
    path = reporoot / "socorro" / "schemas"

    # Validate JSON-specified schemas are valid jsonschema
    for fn in path.glob("*.json"):
        print(fn)
        schema = get_file_content(fn.name)
        jsonschema.Draft4Validator.check_schema(schema)

    # Validate YAML-specified schemas are valid jsonschema
    for fn in path.glob("*.yaml"):
        print(fn)
        schema = get_file_content(fn.name)
        jsonschema.Draft4Validator.check_schema(schema)


def test_processed_crash_schema():
    # We use the schema reducer to traverse the schema and validate the socorro metadata
    # values

    metadata_schema = get_file_content("socorro_metadata.1.schema.yaml")

    def validate_metadata(path, general_path, schema_item):
        # Print this out so it's clear which item failed
        print(f"working on {general_path}")
        if "socorro" in schema_item:
            # NOTE(willkg): this raises an exception if it fails and that'll trigger a
            # pytest failure
            jsonschema.validate(schema_item["socorro"], metadata_schema)

    traverse_schema(
        schema=PROCESSED_CRASH_SCHEMA,
        visitor_function=validate_metadata,
    )
