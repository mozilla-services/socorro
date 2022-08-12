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

from socorro.lib.libjson import transform_socorro_data_schema
from socorro.schemas import PROCESSED_CRASH_SCHEMA


HERE = os.path.dirname(__file__)


class InvalidSchemaError(Exception):
    pass


@click.command()
@click.argument("crashdir")
@click.pass_context
def validate_and_test(ctx, crashdir):
    schema_name = PROCESSED_CRASH_SCHEMA["$id"]

    jsonschema.Draft4Validator.check_schema(PROCESSED_CRASH_SCHEMA)
    click.echo(f"{schema_name} is a valid JSON schema.")

    # Fetch crash report data from a Super Search URL
    datapath = pathlib.Path(crashdir).resolve()
    if not datapath.is_dir():
        raise click.ClickException(f"{datapath} is not a directory.")

    click.echo(f"Fetching data from {datapath}...")

    uuids = list(datapath.glob("*"))

    # Figure out the schema keys to types mapping
    schema_keys_to_types = {}

    def log_schema_keys(path, schema):
        if path and not path.endswith(".[]"):
            schema_keys_to_types[path] = schema["type"]
        return schema

    transform_socorro_data_schema(
        schema=PROCESSED_CRASH_SCHEMA,
        transform_function=log_schema_keys,
    )

    document_keys_to_types = {}

    def log_document_keys(crash, path=""):
        if isinstance(crash, dict):
            for key, value in crash.items():
                log_document_keys(value, path=f"{path}.{key}")

        elif isinstance(crash, list):
            for item in crash:
                log_document_keys(item, path=f"{path}.[]")

        # Add non-arrays to the keys set
        if path and not path.endswith(".[]"):
            # This is silly, but we want to end up with a sorted list of types that have
            # no duplicates; typically this should be [something] or
            # [something, NoneType]
            types = set(document_keys_to_types.get(path, []))
            types.add(type(crash).__name__)
            document_keys_to_types[path] = list(sorted(types))

    total_uuids = len(uuids)
    click.echo("")
    click.echo(f"Testing {total_uuids} recent crash reports.")
    for i, uuid in enumerate(uuids):
        click.echo(f"Working on {uuid} ({i}/{total_uuids})...")

        processed_crash = json.loads((datapath / uuid).read_text())
        log_document_keys(processed_crash)
        jsonschema.validate(processed_crash, PROCESSED_CRASH_SCHEMA)

    click.echo("Done testing, all crash reports passed.")

    keys_not_in_crashes = set(schema_keys_to_types.keys()) - set(
        document_keys_to_types.keys()
    )
    if keys_not_in_crashes:
        click.echo(
            f"{len(keys_not_in_crashes)} (out of {len(schema_keys_to_types)}) keys "
            + "in JSON Schema, but never in any of the tested crashes:"
        )
        click.echo("  %s%s" % ("KEY".ljust(60), "TYPE(S)"))
        for k in sorted(keys_not_in_crashes):
            click.echo("  %s%s" % (k.ljust(60), schema_keys_to_types[k]))

    keys_not_in_schema = set(document_keys_to_types.keys()) - set(
        schema_keys_to_types.keys()
    )
    if keys_not_in_schema:
        click.echo("")
        click.echo(
            f"{len(keys_not_in_schema)} keys in crash reports but not in {schema_name}:"
        )
        click.echo("  %s%s" % ("KEY".ljust(70), "TYPE(S)"))
        for key in sorted(keys_not_in_schema):
            click.echo("  %s%s" % (key.ljust(70), document_keys_to_types[key]))


if __name__ == "__main__":
    validate_and_test()
