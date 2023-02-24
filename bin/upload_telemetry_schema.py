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
from socorro.schemas import TELEMETRY_SOCORRO_CRASH_SCHEMA


METRICS = markus.get_metrics("processor")


@click.command()
@click.option(
    "--destination_key",
    default="telemetry_socorro_crash.json",
    help="the key in the S3 bucket to save the schema to",
)
@click.pass_context
def upload(ctx, destination_key):
    """Uploads schema to S3 bucket for Telemetry

    We always send a copy of the crash (mainly processed crash) to a S3 bucket
    meant for Telemetry to ingest. When they ingest, they need a copy of our
    telemetry_socorro_crash.json JSON Schema file.

    They use that not to understand the JSON we store but the underlying
    structure (types, nesting etc.) necessary for storing it in .parquet files
    in S3.

    To get a copy of the telemetry_socorro_crash.json they can take it from the git
    repository but that's fragile since it depends on github.com always being available.

    By uploading it to S3 not only do we bet on S3 being more read-reliable
    that github.com's server but by being in S3 AND unavailable that means the
    whole ingestion process has to halt/pause anyway.

    """
    telemetry_settings = settings.CRASH_DESTINATIONS["telemetry"]
    crashstorage = build_instance_from_settings(telemetry_settings)

    data = json.dumps(TELEMETRY_SOCORRO_CRASH_SCHEMA, indent=2, sort_keys=True)

    crashstorage.save_file(path=destination_key, data=data.encode("utf-8"))
    click.echo("Success: Schema uploaded!")


def main(argv=None):
    argv = argv or []
    upload(argv)


if __name__ == "__main__":
    upload()
