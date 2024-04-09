#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Script to upload schema to Telemetry crash storage location.
#
# Usage: python bin/cmd upload_telemetry_schema

import json

import click
import markus

from socorro import settings
from socorro.libclass import build_instance_from_settings
from socorro.schemas import get_file_content


METRICS = markus.get_metrics("processor")


@click.command()
@click.option(
    "--destination_key",
    default="telemetry_socorro_crash.json",
    help="the key in the bucket to save the schema to",
)
@click.pass_context
def upload(ctx, destination_key):
    """Uploads schema to bucket for Telemetry

    We always send a copy of the crash (mainly processed crash) to a bucket
    meant for Telemetry to ingest. When they ingest, they need a copy of our
    telemetry_socorro_crash.json JSON Schema file.

    They use that not to understand the JSON we store but the underlying
    structure (types, nesting etc.) necessary for storing it in .parquet files.

    To get a copy of the telemetry_socorro_crash.json they can take it from the git
    repository but that's fragile since it depends on github.com always being available.

    By uploading it not only do we bet on the bucket being more read-reliable
    than github.com's server but by being in the bucket AND unavailable that means the
    whole ingestion process has to halt/pause anyway.

    """
    crashstorage = build_instance_from_settings(settings.TELEMETRY_STORAGE)

    schema = get_file_content("telemetry_socorro_crash.json")
    data = json.dumps(schema, indent=2, sort_keys=True)

    click.echo(f"Saving schema to {destination_key!r} in {crashstorage.bucket!r}")
    crashstorage.save_file(path=destination_key, data=data.encode("utf-8"))
    click.echo("Success: Schema uploaded!")


def main(argv=None):
    argv = argv or []
    upload(argv)


if __name__ == "__main__":
    upload()
