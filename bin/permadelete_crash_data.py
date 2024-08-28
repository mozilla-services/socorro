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
from socorro.lib.librequests import session_with_retries


logging.basicConfig()

logger = logging.getLogger(__name__)


HOSTS = {
    # NOTE(willkg): this script runs in a docker container in the local dev environment
    "local": "http://webapp:8000",
    "stage": "https://crash-stats.allizom.org",
    "prod": "https://crash-stats.mozilla.org",
}


def crashid_generator(fn):
    """Lazily yield crash ids."""
    with open(fn) as fp:
        for line in fp:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            yield line


@click.command()
@click.argument("env", nargs=1)
@click.argument("crashidsfile", nargs=1)
@click.pass_context
def cmd_permadelete(ctx, env, crashidsfile):
    """
    Permanently deletes crash report data from crash storage.

    The env should be either "local", "stage", or "prod".

    The crashidsfile should be a complete path to the file with
    crashids in it--one per line. This will skip lines prefixed
    with a # treating them like comments.

    """
    if env not in ["local", "stage", "prod"]:
        click.echo('env should be either "local", "stage", or "prod".', err=True)
        ctx.exit(1)

    if not os.path.exists(crashidsfile):
        click.echo(f"File {crashidsfile!r} does not exist.", err=True)
        ctx.exit(1)

    crashverify_url = f"{HOSTS[env]}/api/CrashVerify/"
    session = session_with_retries()
    headers = {"User-Agent": "socorro-permadelete/1.0"}

    crashstorage = build_instance_from_settings(settings.STORAGE)
    es_crashstorage = build_instance_from_settings(settings.ES_STORAGE)

    crashids = crashid_generator(crashidsfile)

    for crashid in crashids:
        click.echo(f"Working on {crashid!r}")
        start_time = datetime.datetime.now()
        resp = session.get(
            crashverify_url, headers=headers, params={"crash_id": crashid}
        )
        click.echo(f">>> before: {resp.json()}")
        # delete from storage
        click.echo(">>> Deleting from storage ...")
        crashstorage.delete_crash(crashid)
        # delete from es
        click.echo(">>> Deleting from Elasticsearch ...")
        es_crashstorage.delete_crash(crashid)
        end_time = datetime.datetime.now()
        resp = session.get(
            crashverify_url, headers=headers, params={"crash_id": crashid}
        )
        click.echo(f">>> after: {resp.json()}")
        click.echo(f">>> Time: {end_time - start_time}")
        click.echo("")

    click.echo("Done!")


if __name__ == "__main__":
    cmd_permadelete()
