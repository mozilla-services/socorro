#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Usage: python socorro/schemas/validate_processed_crash.py [DIR]

import json
import os
import pathlib
import re
import textwrap

import click
import jsonschema

from socorro.lib.libsocorrodataschema import (
    get_schema,
    SocorroDataReducer,
    split_path,
    transform_schema,
    validate_instance,
)
from socorro.schemas import get_file_content


HERE = os.path.dirname(__file__)


PROCESSED_CRASH_SCHEMA = get_schema("processed_crash.schema.yaml")


def wrapped(ctx, text):
    width = min(ctx.terminal_width or 78, 78)
    return "\n".join(textwrap.wrap(text, width=width))


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


def match_key(schema_key, document_key):
    """Determines whether a schema key matches a document key

    The schema_key can contain regex parts. This accounts for that.

    :arg str schema_key: the key from the schema which can contain regex parts
    :arg str document_key: the key from the document

    :returns: boolean

    """
    # This is the easy case where the two keys match
    if "(re:" not in schema_key:
        return schema_key == document_key

    # This case is hard because one of the parts of the key can be a regex. So what we
    # do is convert the entire schema key into a regex by doing some sleight-of-hand
    # with the pattern_properties regexes particularly with the ^ and $. Then we use
    # that regex to match the document_key. That handles schema keys like:
    #
    # .telemetry_environment.settings.userPrefs.(re:^.+$)
    #
    # which needs to match something like this:
    #
    # .telemetry_environment.settings.userPrefs.browser.startup.homepage
    #
    # because the keys have dots, too.
    #
    # Another way to do this matching thing is to store the path as a list of string
    # parts rather than a .-delimited string, but that involves rewriting a bunch of
    # stuff about paths and traversals and such.
    schema_parts = []
    for part in split_path(schema_key):
        if part.startswith("(re:"):
            part = part[4:-1]
            if part.startswith("^"):
                part = part[1:]
            else:
                part = ".*?" + part
            if part.endswith("$"):
                part = part[:-1]
            else:
                part = part + ".*?"

    # Now that we have a re, we can match it and move along.
    schema_re = re.compile(r"\.".join(schema_parts))
    return bool(schema_re.match(document_key))


@click.command()
@click.argument("crashdir")
@click.pass_context
def validate_and_test(ctx, crashdir):
    socorro_data_schema = get_file_content("socorro-data-1-0-0.schema.yaml")
    jsonschema.Draft7Validator.check_schema(socorro_data_schema)
    click.echo("socorro-data-1-0-0.schema.yaml is a valid jsonschema.")

    jsonschema.validate(instance=PROCESSED_CRASH_SCHEMA, schema=socorro_data_schema)
    click.echo("processed crash schema is a valid socorro data schema.")

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
    click.echo(
        wrapped(
            ctx,
            f"Validating processed crash schema against {total_uuids} crash reports. "
            + "Validation errors usually indicate a problem with the schema.",
        )
    )
    click.echo("")
    for i, uuid in enumerate(uuids):
        click.echo(f"Working on {uuid} ({i}/{total_uuids})...")
        processed_crash = json.loads((datapath / uuid).read_text())

        # Log the keys
        document_keys.log_keys(processed_crash)

        # Reduce the document by the schema and remove whatever keys are in the document
        # which is what the schema knows about
        reduced_processed_crash = schema_reducer.traverse(processed_crash)
        reduced_keys.log_keys(reduced_processed_crash)

        validate_instance(processed_crash, PROCESSED_CRASH_SCHEMA)

    click.echo("")
    click.echo("Done checking schema against crash reports.")

    # Figure out which schema keys weren't in documents taking into account
    # pattern_property regexes
    keys_not_in_doc = set()
    for key, type_ in schema_key_logger.keys:
        is_in_reduced_keys = False
        for reduced_key, reduced_type_ in reduced_keys.keys:
            if match_key(key, reduced_key):
                is_in_reduced_keys = True
                break

        if not is_in_reduced_keys:
            keys_not_in_doc.add((key, type_))

    if keys_not_in_doc:
        click.echo("")
        click.echo(
            wrapped(
                ctx,
                f"{len(keys_not_in_doc)} (out of {len(schema_key_logger.keys)}) "
                + "keys in JSON Schema, but never in any of the tested crashes. "
                + "Sometimes fields are no longer in crash reports, so you can remove "
                + "them from the schema and where they're used in the codebase. "
                + "If you're adding a new field and the new field pops up in this list, "
                + "it might indicate there's a typo or an error in the bit you added.",
            )
        )
        click.echo("")
        click.echo(f"{'KEY':90}  TYPE(S)")
        for key, val in sorted(keys_not_in_doc):
            click.echo(f"{key[1:]:90}  {val}")

    # Figure out which doc keys aren't in the schema; this also handles cases where the
    # key is in the schema, but is missing a type
    keys_not_in_schema = document_keys.keys - reduced_keys.keys

    if keys_not_in_schema:
        click.echo("")
        click.echo(
            wrapped(
                ctx,
                f"{len(keys_not_in_schema)} keys in crash reports but not in schema. "
                + "Fields that we haven't added support for show up in this list.",
            )
        )
        click.echo("")
        click.echo(f"{'KEY':90}  TYPE(S)")
        for key, val in sorted(keys_not_in_schema):
            click.echo(f"{key[1:]:90}  {val}")


if __name__ == "__main__":
    validate_and_test()
