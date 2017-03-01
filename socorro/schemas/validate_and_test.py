#!/usr/bin/env python
from __future__ import print_function

import json
import os

import jsonschema
import requests

from socorro.external.boto.crashstorage import TelemetryBotoS3CrashStorage

API_BASE = 'https://crash-stats.mozilla.com/api/{}/'
HERE = os.path.dirname(__file__)


class MockedTelemetryBotoS3CrashStorage(TelemetryBotoS3CrashStorage):

    def __init__(self):
        # Deliberately not doing anything fancy with config. So no super call.
        # Prep the self._all_fields so it's available when
        # self.save_raw_and_processed() is called.
        r = requests.get(
            API_BASE.format('SuperSearchFields'),
        )
        print(r.url)
        self._all_fields = r.json()

    def _get_all_fields(self):
        return self._all_fields

    def save_processed(self, crash):
        self.combined = crash


def main():
    file_path = os.path.join(HERE, 'crash_report.json')
    with open(file_path) as f:
        schema = json.load(f)
    jsonschema.Draft4Validator.check_schema(schema)
    print('{} is a valid JSON schema'.format(file_path))

    print('Fetching data...')
    r = requests.get(
        API_BASE.format('SuperSearch'),
        params={
            'product': 'Firefox',
            '_columns': ['uuid'],
            '_facets_size': 0
        }
    )
    search = r.json()

    processor = MockedTelemetryBotoS3CrashStorage()

    print('Testing {} random recent crash reports'.format(len(search['hits'])))
    for hit in search['hits']:
        r = requests.get(
            API_BASE.format('RawCrash'),
            params={'crash_id': hit['uuid']}
        )
        print(r.url)
        raw_crash = r.json()
        r = requests.get(
            API_BASE.format('ProcessedCrash'),
            params={'crash_id': hit['uuid']}
        )
        print(r.url)
        processed_crash = r.json()
        processor.save_raw_and_processed(
            raw_crash,
            (),  # dumps
            processed_crash,
            hit['uuid'],
        )
        jsonschema.validate(processor.combined, schema)

    print('Done testing, all crash reports passed.')


if __name__ == '__main__':
    main()
