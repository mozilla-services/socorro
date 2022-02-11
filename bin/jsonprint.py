#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Prints a JSON file out with two-space indents and sorted.

Usage::

    python bin/jsonprint.py FILE.json

"""

import json

import click


@click.command()
@click.argument("jsonfile", type=click.File("rb"))
@click.pass_context
def cmd_jsonprint(ctx, jsonfile):
    json_data = json.loads(jsonfile.read())
    print(json.dumps(json_data, indent=2, sort_keys=True))


if __name__ == "__main__":
    cmd_jsonprint()
