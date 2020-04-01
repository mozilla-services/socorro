#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import json
import os
import sys
from urllib.parse import urlparse

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
        print(resp.url)
        self._all_fields = resp.json()
        self.conn = MockConn()

    def save_processed_crash(self, raw_crash, processed_crash):
        super().save_processed_crash(raw_crash, processed_crash)
        return self.conn.last_data


def run(no_crashes, *urls):
    # Load the schema validator and validate the schema
    file_path = os.path.join(HERE, "crash_report.json")
    with open(file_path) as f:
        schema = json.load(f)
    jsonschema.Draft4Validator.check_schema(schema)
    print("{} is a valid JSON schema".format(file_path))

    # Fetch crash report data from a Super Search URL
    print("Fetching data...")
    uuids = []
    if urls:
        for url in urls:
            assert "://" in url, url

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
                    "_results_number": no_crashes,
                },
            )
            search = resp.json()
            if not search["total"]:
                print("Warning! {} returned 0 UUIDs".format(url))
            uuids.extend([x["uuid"] for x in search["hits"] if x["uuid"] not in uuids])

    else:
        resp = requests.get(
            API_BASE.format("SuperSearch"),
            params={
                "product": "Firefox",
                "_columns": ["uuid"],
                "_facets_size": 0,
                "_results_number": no_crashes,
            },
        )
        search = resp.json()
        uuids = [x["uuid"] for x in search["hits"]]

    crashstorage = MockedTelemetryBotoS3CrashStorage()

    all_keys = set()

    def log_all_keys(crash, prefix=""):
        for key, value in crash.items():
            if isinstance(value, dict):
                log_all_keys(value, prefix=prefix + "{}.".format(key))
            else:
                all_keys.add(prefix + key)

    all_schema_types = {}

    def log_all_schema_keys(schema, prefix=""):
        for key, value in schema["properties"].items():
            if isinstance(value, dict) and "properties" in value:
                log_all_schema_keys(value, prefix=prefix + "{}.".format(key))
            else:
                all_schema_types[prefix + key] = value["type"]

    log_all_schema_keys(schema)

    print("Testing {} random recent crash reports".format(len(uuids)))
    for uuid in uuids:
        resp = requests.get(API_BASE.format("RawCrash"), params={"crash_id": uuid})
        print(resp.url)
        raw_crash = resp.json()
        resp = requests.get(
            API_BASE.format("ProcessedCrash"), params={"crash_id": uuid}
        )
        print(resp.url)
        processed_crash = resp.json()

        crash_report = crashstorage.save_processed_crash(raw_crash, processed_crash)
        log_all_keys(crash_report)
        jsonschema.validate(crash_report, schema)

    print("\nDone testing, all crash reports passed.\n")

    keys_not_in_crashes = set(all_schema_types.keys()) - all_keys
    if keys_not_in_crashes:
        print(
            "%s keys in JSON Schema, but never in any of the tested crashes:"
            % len(keys_not_in_crashes)
        )
        print("  %s%s" % ("KEY".ljust(60), "TYPE(S)"))
        for k in sorted(keys_not_in_crashes):
            print("  %s%s" % (k.ljust(60), all_schema_types[k]))


def main():
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--crashes-per-url",
        "-n",
        help="Number of crashes to download per SuperSearch URL",
        default=20,
    )
    argparser.add_argument(
        "urls", help="SuperSearch API URL(s) to use instead of the default", nargs="*"
    )
    args = argparser.parse_args()
    run(args.crashes_per_url, *args.urls)


if __name__ == "__main__":
    sys.exit(main())
