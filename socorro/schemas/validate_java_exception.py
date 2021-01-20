#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: python socorro/schemas/validate_java_exception.py

import json
import os

import click
import jsonschema


HERE = os.path.dirname(__file__)


@click.command()
@click.pass_context
def validate_and_test(ctx):
    # Load the schema validator and validate the schema
    file_path = os.path.join(HERE, "java_exception.json")
    with open(file_path) as f:
        schema = json.load(f)
    jsonschema.Draft4Validator.check_schema(schema)
    click.echo("%s is a valid JSON schema." % file_path)


if __name__ == "__main__":
    validate_and_test()
