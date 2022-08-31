#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Usage: python socorro/schemas/validate_processed_crash.py

import json
import os
import pathlib

import click
import jsonschema

from socorro.lib.libsocorrodataschema import transform_schema, SocorroDataReducer
from socorro.schemas import PROCESSED_CRASH_SCHEMA


HERE = os.path.dirname(__file__)


class InvalidSchemaError(Exception):
    pass


class SchemaKeyLogger:
    def __init__(self):
        # Set of (key, type)
        self.keys = set()

    def __call__(self, path, schema):
        if path and not path.endswith(".[]"):
            types = schema["type"]
            if not isinstance(schema["type"], list):
                types = [types]
            for type_ in types:
                self.keys.add((path, type_))
        return schema


PYTHON_TO_DATA = {
    str: "string",
    float: "number",
    int: "integer",
    type(None): "null",
    bool: "boolean",
    list: "array",
    dict: "object",
}


class DocumentKeys:
    def __init__(self):
        # Set of (key, type)
        self.keys = set()

    def log_keys(self, crash):
        def traverse(crash, path):
            if isinstance(crash, dict):
                for key, value in crash.items():
                    traverse(value, path=f"{path}.{key}")

            elif isinstance(crash, list):
                for item in crash:
                    traverse(item, path=f"{path}.[]")

            # Add non-arrays to the keys set
            if path and not path.endswith(".[]"):
                type_ = PYTHON_TO_DATA[type(crash)]
                self.keys.add((path, type_))

        traverse(crash, path="")


@click.command()
@click.argument("crashdir")
@click.pass_context
def validate_and_test(ctx, crashdir):
    jsonschema.Draft4Validator.check_schema(PROCESSED_CRASH_SCHEMA)
    click.echo("processed crash schema is a valid JSON schema.")

    # Fetch crash report data from a Super Search URL
    datapath = pathlib.Path(crashdir).resolve()
    if not datapath.is_dir():
        raise click.ClickException(f"{datapath} is not a directory.")

    click.echo(f"Fetching data from {datapath}...")

    uuids = list(datapath.glob("*"))

    # Figure out the schema keys to types mapping
    schema_key_logger = SchemaKeyLogger()
    transform_schema(
        schema=PROCESSED_CRASH_SCHEMA, transform_function=schema_key_logger
    )

    schema_reducer = SocorroDataReducer(PROCESSED_CRASH_SCHEMA)

    document_keys = DocumentKeys()
    reduced_keys = DocumentKeys()

    total_uuids = len(uuids)
    click.echo("")
    click.echo(f"Testing {total_uuids} recent crash reports.")
    for i, uuid in enumerate(uuids):
        click.echo(f"Working on {uuid} ({i}/{total_uuids})...")
        processed_crash = json.loads((datapath / uuid).read_text())

        # Log the keys
        document_keys.log_keys(processed_crash)

        # Reduce the document by the schema and remove whatever keys are in the document
        # which is what the schema knows about
        reduced_processed_crash = schema_reducer.traverse(processed_crash)
        reduced_keys.log_keys(reduced_processed_crash)

        jsonschema.validate(processed_crash, PROCESSED_CRASH_SCHEMA)

    click.echo("Done testing, all crash reports passed.")

    reduced_keys_keys = set([key for key, type_ in reduced_keys.keys])

    keys_not_in_doc = set()
    for key, type_ in schema_key_logger.keys:
        # We have to iterate over these one at a time because of pattern_properties
        # matching by regex
        if "(re:" in key:
            click.echo(f"{key} is a pattern_property ... ignoring")
            continue

        if key not in reduced_keys_keys:
            keys_not_in_doc.add((key, type_))

    if keys_not_in_doc:
        click.echo(
            f"{len(keys_not_in_doc)} (out of {len(schema_key_logger.keys)} "
            + "keys in JSON Schema, but never in any of the tested crashes:"
        )
        click.echo(f"  {'KEY':90}  TYPE(S)")
        for key, val in sorted(keys_not_in_doc):
            click.echo(f"  {key:90}  {val}")

    keys_not_in_schema = document_keys.keys - reduced_keys.keys
    if keys_not_in_schema:
        click.echo("")
        click.echo(
            f"{len(keys_not_in_schema)} keys in crash reports but not in schema:"
        )
        click.echo(f"  {'KEY':90}  TYPE(S)")
        for key, val in sorted(keys_not_in_schema):
            click.echo(f"  {key:90}  {val}")


if __name__ == "__main__":
    validate_and_test()
