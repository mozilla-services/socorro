#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

# Usage: python socorro/schemas/validate_telemetry_socorro_crash.py

import json
import os
from urllib.parse import urlparse

import click
import jsonschema
import requests

from socorro.external.boto.crashstorage import TelemetryBotoS3CrashStorage


API_BASE = "https://crash-stats.mozilla.org/api/{}/"
HERE = os.path.dirname(__file__)


class MockConn:
    def __init__(self):
        self.last_path = None
        self.last_data = None

    def save_file(self, path, data):
        self.last_path = path

        # We have to convert the data from bytes back to a dict so we can check it
        self.last_data = json.loads(data)


class MockedTelemetryBotoS3CrashStorage(TelemetryBotoS3CrashStorage):
    def __init__(self):
        # Deliberately not doing anything fancy with config. So no super call.
        resp = requests.get(API_BASE.format("SuperSearchFields"))
        click.echo("resp.url %s" % resp.url)
        self._all_fields = resp.json()
        self.conn = MockConn()

    def get_last_data(self):
        return self.conn.last_data


@click.command()
@click.option(
    "--crashes-per-url",
    default=20,
    type=int,
    help="number of crashes to download per supersearch url",
)
@click.argument("url", required=False)
@click.pass_context
def validate_and_test(ctx, crashes_per_url, url):
    # Load the schema validator and validate the schema
    file_path = os.path.join(HERE, "telemetry_socorro_crash.json")
    with open(file_path) as f:
        schema = json.load(f)
    jsonschema.Draft4Validator.check_schema(schema)
    click.echo("%s is a valid JSON schema." % file_path)

    # Fetch crash report data from a Super Search URL
    click.echo("Fetching data...")
    uuids = []
    if url:
        for this_url in url:
            if "://" not in this_url:
                raise click.BadParameter(
                    "url %s has no ://." % this_url, param="url", param_hint="url"
                )

            # To make it easy for people, if someone pastes the URL
            # of a regular SuperSearch page (and not the API URL), then
            # automatically convert it for them.
            parsed = urlparse(url)
            if parsed.path == "/search/":
                parsed = parsed._replace(path="/api/SuperSearch/")
                parsed = parsed._replace(fragment=None)
                url = parsed.geturl()
            resp = requests.get(
                url,
                params={
                    "_columns": ["uuid"],
                    "_facets_size": 0,
                    "_results_number": crashes_per_url,
                },
            )
            search = resp.json()
            if not search["total"]:
                click.echo("Warning! %s returned 0 UUIDs." % url)
            uuids.extend([x["uuid"] for x in search["hits"] if x["uuid"] not in uuids])

    else:
        resp = requests.get(
            API_BASE.format("SuperSearch"),
            params={
                "product": "Firefox",
                "_columns": ["uuid"],
                "_facets_size": 0,
                "_results_number": crashes_per_url,
            },
        )
        search = resp.json()
        uuids = [x["uuid"] for x in search["hits"]]

    crashstorage = MockedTelemetryBotoS3CrashStorage()

    all_keys = set()

    def log_all_keys(crash, prefix=""):
        for key, value in crash.items():
            if isinstance(value, dict):
                log_all_keys(value, prefix=f"{prefix}{key}.")
            else:
                all_keys.add(prefix + key)

    all_schema_types = {}

    def log_all_schema_keys(schema, prefix=""):
        for key, value in schema["properties"].items():
            if isinstance(value, dict) and "properties" in value:
                log_all_schema_keys(value, prefix=f"{prefix}{key}.")
            else:
                all_schema_types[prefix + key] = value["type"]

    log_all_schema_keys(schema)

    click.echo("Testing %s random recent crash reports." % len(uuids))
    for uuid in uuids:
        resp = requests.get(API_BASE.format("RawCrash"), params={"crash_id": uuid})
        click.echo("resp.url %s" % resp.url)
        raw_crash = resp.json()
        resp = requests.get(
            API_BASE.format("ProcessedCrash"), params={"crash_id": uuid}
        )
        click.echo("resp.url %s" % resp.url)
        processed_crash = resp.json()

        crashstorage.save_processed_crash(raw_crash, processed_crash)
        crash_report = crashstorage.get_last_data()
        log_all_keys(crash_report)
        jsonschema.validate(crash_report, schema)

    click.echo("Done testing, all crash reports passed.")

    keys_not_in_crashes = set(all_schema_types.keys()) - all_keys
    if keys_not_in_crashes:
        click.echo(
            "%s keys in JSON Schema, but never in any of the tested crashes:"
            % len(keys_not_in_crashes)
        )
        click.echo("  %s%s" % ("KEY".ljust(60), "TYPE(S)"))
        for k in sorted(keys_not_in_crashes):
            click.echo("  %s%s" % (k.ljust(60), all_schema_types[k]))


if __name__ == "__main__":
    validate_and_test()
