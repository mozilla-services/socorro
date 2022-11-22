#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Usage: python socorro/schemas/validate_raw_crash.py [DIR]

from itertools import zip_longest
import json
import os
import pathlib

import click
import jsonschema
import yaml

from socorro.lib.librequests import session_with_retries
from socorro.lib.libsocorrodataschema import (
    compile_pattern_re,
    get_schema,
    SocorroDataReducer,
    split_path,
    transform_schema,
    validate_instance,
)
from socorro.schemas import get_file_content


HERE = os.path.dirname(__file__)


RAW_CRASH_SCHEMA = get_schema("raw_crash.schema.yaml")


CRASH_ANNOTATIONS_URL = (
    "https://hg.mozilla.org/mozilla-central/raw-file/tip/toolkit/crashreporter/"
    + "CrashAnnotations.yaml"
)


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
    """Determines whether a key matches

    The schema_key can contain regex parts. This accounts for that.

    :arg str schema_key: the key from the schema which can contain regex parts
    :arg str document_key: the key from the document

    :returns: boolean

    """
    if "(re:" not in schema_key:
        return schema_key == document_key

    schema_parts = split_path(schema_key)
    doc_parts = split_path(document_key)

    for schema_part, doc_part in zip_longest(schema_parts, doc_parts, fillvalue=""):
        if "(re:" in schema_part:
            pattern_re = compile_pattern_re(schema_part[4:-1])
            if not pattern_re.match(doc_part):
                return False

        elif schema_part != doc_part:
            return False

    return True


@click.command()
@click.argument("crashdir")
@click.pass_context
def validate_and_test(ctx, crashdir):
    socorro_data_schema = get_file_content("socorro-data-1-0-0.schema.yaml")
    jsonschema.Draft7Validator.check_schema(socorro_data_schema)
    click.echo("socorro-data-1-0-0.schema.yaml is a valid jsonschema.")

    jsonschema.validate(instance=RAW_CRASH_SCHEMA, schema=socorro_data_schema)
    click.echo("raw crash schema is a valid socorro data schema.")

    # Fetch crash report data from a Super Search URL
    datapath = pathlib.Path(crashdir).resolve()
    if not datapath.is_dir():
        raise click.ClickException(f"{datapath} is not a directory.")

    click.echo(f"Fetching data from {datapath}...")

    uuids = list(datapath.glob("*"))

    # Figure out the schema keys to types mapping
    schema_key_logger = SchemaKeyLogger()
    transform_schema(schema=RAW_CRASH_SCHEMA, transform_function=schema_key_logger)

    schema_reducer = SocorroDataReducer(RAW_CRASH_SCHEMA)

    document_keys = DocumentKeys()
    reduced_keys = DocumentKeys()

    total_uuids = len(uuids)
    click.echo("")
    click.echo(f"Testing {total_uuids} recent crash reports.")
    for i, uuid in enumerate(uuids):
        click.echo(f"Working on {uuid} ({i}/{total_uuids})...")
        raw_crash = json.loads((datapath / uuid).read_text())

        # Log the keys
        document_keys.log_keys(raw_crash)

        # Reduce the document by the schema and remove whatever keys are in the document
        # which is what the schema knows about
        reduced_raw_crash = schema_reducer.traverse(raw_crash)
        reduced_keys.log_keys(reduced_raw_crash)

        validate_instance(raw_crash, RAW_CRASH_SCHEMA)

    click.echo("Done testing, all crash reports passed.")

    reduced_keys_keys = set([key for key, type_ in reduced_keys.keys])

    # Figure out which schema keys weren't in documents taking into account
    # pattern_property regexes
    keys_not_in_doc = set()
    for key, type_ in schema_key_logger.keys:
        is_in_reduced_keys = False
        for reduced_key in reduced_keys_keys:
            if match_key(key, reduced_key):
                is_in_reduced_keys = True
                break

        if not is_in_reduced_keys:
            keys_not_in_doc.add((key, type_))

    if keys_not_in_doc:
        click.echo(
            f"{len(keys_not_in_doc)} (out of {len(schema_key_logger.keys)}) "
            + "keys in JSON Schema, but never in any of the tested crashes:"
        )
        click.echo(f"  {'KEY':90}  TYPE(S)")
        for key, val in sorted(keys_not_in_doc):
            click.echo(f"  {key:90}  {val}")

    # Figure out which doc keys aren't in the schema; this also handles cases where the
    # key is in the schema, but is missing a type
    keys_not_in_schema = document_keys.keys - reduced_keys.keys
    if keys_not_in_schema:
        click.echo("")
        click.echo(
            f"{len(keys_not_in_schema)} keys in crash reports but not in schema:"
        )
        click.echo(f"  {'KEY':90}  TYPE(S)")
        for key, val in sorted(keys_not_in_schema):
            click.echo(f"  {key:90}  {val}")

    # Fetch CrashAnnotations.yaml
    resp = session_with_retries().get(CRASH_ANNOTATIONS_URL)
    data = yaml.load(resp.content, Loader=yaml.Loader)
    crash_annotations_keys = set(data.keys())

    schema_keys = set([key[1:] for key, type_ in schema_key_logger.keys])

    keys_not_in_crash_annotations = schema_keys - crash_annotations_keys
    if keys_not_in_crash_annotations:
        click.echo("")
        click.echo(
            f"{len(keys_not_in_crash_annotations)} keys not in CrashAnnotations.yaml:"
        )
        click.echo(f"  {'KEY'}")
        for key in sorted(keys_not_in_crash_annotations):
            click.echo(f"  {key}")

    keys_not_in_raw_crash_schema = crash_annotations_keys - schema_keys
    if keys_not_in_raw_crash_schema:
        click.echo("")
        click.echo(f"{len(keys_not_in_raw_crash_schema)} keys not in raw_crash_schema:")
        click.echo(f"  {'KEY'}")
        for key in sorted(keys_not_in_raw_crash_schema):
            click.echo(f"  {key}")


if __name__ == "__main__":
    validate_and_test()
