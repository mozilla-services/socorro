#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Given a set of crash reports ids via a file, removes all crash report data from
all crash storage:

* Crash storage

  * raw crash
  * dump_names
  * minidump files
  * processed crash

* Elasticsearch

  * crash report document

Notes:

1. This **deletes** crash data permanently. Once deleted, this data can't be undeleted.
2. This doesn't delete any data from cache. Caches will expire data eventually.

Usage::

    python bin/permadelete_crash_data.py CRASHIDSFILE

"""

import datetime
import logging
import os

import click

from socorro import settings
from socorro.libclass import build_instance_from_settings


logging.basicConfig()

logger = logging.getLogger(__name__)


def crashid_generator(fn):
    """Lazily yield crash ids."""
    with open(fn) as fp:
        for line in fp:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            yield line


@click.command()
@click.argument("crashidsfile", nargs=1)
@click.pass_context
def cmd_permadelete(ctx, crashidsfile):
    """
    Permanently deletes crash report data from crash storage.

    The crashidsfile should be a complete path to the file with
    crashids in it--one per line. This will skip lines prefixed
    with a # treating them like comments.

    """
    if not os.path.exists(crashidsfile):
        click.echo(f"File {crashidsfile!r} does not exist.", err=True)
        ctx.exit(1)

    crashstorage = build_instance_from_settings(settings.STORAGE)
    es_crashstorage = build_instance_from_settings(settings.ES_STORAGE)
    legacy_es_crashstorage = None
    if settings.ELASTICSEARCH_MODE == "PREFER_NEW":
        legacy_es_crashstorage = build_instance_from_settings(
            settings.LEGACY_ES_STORAGE
        )

    crashids = crashid_generator(crashidsfile)

    for crashid in crashids:
        click.echo(f"Working on {crashid!r}")
        start_time = datetime.datetime.now()

        data = crashstorage.catalog_crash(crash_id=crashid)
        data.extend(es_crashstorage.catalog_crash(crash_id=crashid))
        if legacy_es_crashstorage:
            data.extend(
                f"legacy_{v}"
                for v in legacy_es_crashstorage.catalog_crash(crash_id=crashid)
            )
        click.echo(f">>> before: {data}")

        # Delete from storage
        click.echo(">>> Deleting from storage ...")
        crashstorage.delete_crash(crashid)
        click.echo(">>> Deleting from Elasticsearch ...")
        es_crashstorage.delete_crash(crashid)
        if legacy_es_crashstorage:
            click.echo(">>> Deleting from legacy Elasticsearch ...")
            legacy_es_crashstorage.delete_crash(crashid)

        data = crashstorage.catalog_crash(crash_id=crashid)
        data.extend(es_crashstorage.catalog_crash(crash_id=crashid))
        if legacy_es_crashstorage:
            data.extend(
                f"legacy_{v}"
                for v in legacy_es_crashstorage.catalog_crash(crash_id=crashid)
            )
        click.echo(f">>> after: {data}")

        end_time = datetime.datetime.now()
        click.echo(f">>> Time: {end_time - start_time}")
        click.echo("")

    click.echo("Done!")


if __name__ == "__main__":
    cmd_permadelete()
