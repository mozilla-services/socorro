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

from socorro.lib.libjson import schema_reduce
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

    all_keys = {}

    def log_all_keys(processed_crash, prefix=None):
        prefix = prefix or []

        if isinstance(processed_crash, dict):
            for key, value in processed_crash.items():
                log_all_keys(value, prefix=prefix + [key])

        elif isinstance(processed_crash, list):
            for item in processed_crash:
                log_all_keys(item, prefix=prefix + ["[]"])

        # Add non-arrays to the keys set
        path = ".".join(prefix)
        if path and not path.endswith("[]"):
            # This is silly, but we want to end up with a sorted list of types that have
            # no duplicates; typically this should be [something] or
            # [something, NoneType]
            types = set(all_keys.get(path, []))
            types.add(type(processed_crash).__name__)
            all_keys[path] = list(sorted(types))

    schema_types = {}

    def logging_predicate(path, general_path, schema_item):
        if general_path == ".":
            return True

        # Add non-arrays to the schema types
        if not general_path.endswith("[]"):
            schema_types[general_path.lstrip(".")] = schema_item["type"]
        return True

    total_uuids = len(uuids)
    click.echo("")
    click.echo(f"Testing {total_uuids} recent crash reports.")
    for i, uuid in enumerate(uuids):
        click.echo(f"Working on {uuid} ({i}/{total_uuids})...")

        processed_crash = json.loads((datapath / uuid).read_text())

        # Capture all the keys
        log_all_keys(processed_crash)

        # Capture keys that the schema recognizes
        schema_reduce(
            schema=PROCESSED_CRASH_SCHEMA,
            document=processed_crash,
            include_predicate=logging_predicate,
        )

        # Validate the processed crash
        jsonschema.validate(processed_crash, PROCESSED_CRASH_SCHEMA)

    click.echo("Done testing, all crash reports passed.")

    # FIXME(willkg): compute the keys in the schema that aren't in the document

    # keys_not_in_crashes = set(schema_types.keys()) - all_keys
    # if keys_not_in_crashes:
    #     click.echo("")
    #     click.echo(
    #         f"{len(keys_not_in_crashes)} keys in processed_crash.json Schema, "
    #         + "but not in crash reports:"
    #     )
    #     click.echo("  %s%s" % ("KEY".ljust(60), "TYPE(S)"))
    #     for key in sorted(keys_not_in_crashes):
    #         click.echo("  %s%s" % (key.ljust(60), all_schema_types[key]))

    keys_not_in_schema = set(all_keys.keys()) - set(schema_types.keys())
    if keys_not_in_schema:
        click.echo("")
        click.echo(
            f"{len(keys_not_in_schema)} keys in crash reports but not in {schema_name}:"
        )
        click.echo("  %s%s" % ("KEY".ljust(70), "TYPE(S)"))
        for key in sorted(keys_not_in_schema):
            click.echo("  %s%s" % (key.ljust(70), all_keys[key]))


if __name__ == "__main__":
    validate_and_test()
