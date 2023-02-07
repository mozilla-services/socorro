#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# Script to upload schema to Telemetry crash storage location.
#
# Usage: socorro-cmd upload_telemetry_schema

import json
from pathlib import Path

import click
from fillmore.libsentry import set_up_sentry
from fillmore.scrubber import Scrubber, SCRUB_RULES_DEFAULT
import markus

from socorro import settings
from socorro.libclass import build_instance_from_settings
from socorro.lib.libdockerflow import get_release_name
from socorro.schemas import TELEMETRY_SOCORRO_CRASH_SCHEMA


METRICS = markus.get_metrics("processor")


def count_sentry_scrub_error(msg):
    METRICS.incr("sentry_scrub_error", 1)


def configure_sentry(basedir, host_id, sentry_dsn):
    release = get_release_name(basedir)
    scrubber = Scrubber(
        rules=SCRUB_RULES_DEFAULT,
        error_handler=count_sentry_scrub_error,
    )
    set_up_sentry(
        sentry_dsn=sentry_dsn,
        release=release,
        host_id=host_id,
        # Disable frame-local variables
        with_locals=False,
        # Scrub sensitive data
        before_send=scrubber,
    )


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

    basedir = Path(__file__).resolve().parent.parent

    configure_sentry(
        basedir,
        host_id=settings.HOST_ID,
        sentry_dsn=settings.SENTRY_DSN,
    )

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
