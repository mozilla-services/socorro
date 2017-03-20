#!/usr/bin/env python
from __future__ import print_function

from urlparse import urlparse
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


def run(no_crashes, *urls):
    file_path = os.path.join(HERE, 'crash_report.json')
    with open(file_path) as f:
        schema = json.load(f)
    jsonschema.Draft4Validator.check_schema(schema)
    print('{} is a valid JSON schema'.format(file_path))

    print('Fetching data...')
    uuids = []
    for url in urls:
        assert '://' in url, url

        # To make it easy for people, if someone pastes the URL
        # of a regular SuperSearch page (and not the API URL), then
        # automatically convert it for them.
        parsed = urlparse(url)
        if parsed.path == '/search/':
            parsed = parsed._replace(path='/api/SuperSearch/')
            parsed = parsed._replace(fragment=None)
            url = parsed.geturl()
        r = requests.get(
            url,
            params={
                '_columns': ['uuid'],
                '_facets_size': 0,
                '_results_number': no_crashes,
            }
        )
        search = r.json()
        if not search['total']:
            print('Warning! {} returned 0 UUIDs'.format(
                url
            ))
        uuids.extend(
            [x['uuid'] for x in search['hits'] if x['uuid'] not in uuids]
        )
    if not urls:
        r = requests.get(
            API_BASE.format('SuperSearch'),
            params={
                'product': 'Firefox',
                '_columns': ['uuid'],
                '_facets_size': 0,
                '_results_number': no_crashes,
            }
        )
        search = r.json()
        uuids = [x['uuid'] for x in search['hits']]

    processor = MockedTelemetryBotoS3CrashStorage()

    all_keys = set()

    def log_all_keys(crash, prefix=''):
        for key, value in crash.items():
            if isinstance(value, dict):
                log_all_keys(value, prefix=prefix + '{}.'.format(key))
            else:
                all_keys.add(prefix + key)

    all_schema_types = {}

    def log_all_schema_keys(schema, prefix=''):
        for key, value in schema['properties'].items():
            if isinstance(value, dict) and 'properties' in value:
                log_all_schema_keys(value, prefix=prefix + '{}.'.format(key))
            else:
                all_schema_types[prefix + key] = value['type']
    log_all_schema_keys(schema)

    print('Testing {} random recent crash reports'.format(len(uuids)))
    for uuid in uuids:
        r = requests.get(
            API_BASE.format('RawCrash'),
            params={'crash_id': uuid}
        )
        print(r.url)
        raw_crash = r.json()
        r = requests.get(
            API_BASE.format('ProcessedCrash'),
            params={'crash_id': uuid}
        )
        print(r.url)
        processed_crash = r.json()

        processor.save_raw_and_processed(
            raw_crash,
            (),  # dumps
            processed_crash,
            uuid,
        )
        log_all_keys(processor.combined)

        jsonschema.validate(processor.combined, schema)

    print('\nDone testing, all crash reports passed.\n')

    keys_not_in_crashes = set(all_schema_types.keys()) - all_keys
    if keys_not_in_crashes:
        print(
            len(keys_not_in_crashes),
            'keys in JSON Schema, but never in any of the tested crashes:'
        )
        print('  ', 'KEY'.ljust(60), 'TYPE(S)')
        for k in sorted(keys_not_in_crashes):
            print('  ', k.ljust(60), all_schema_types[k])


def main():
    import argparse
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        '--crashes-per-url', '-n',
        help='Number of crashes to download per SuperSearch URL',
        default=20,
    )
    argparser.add_argument(
        'urls',
        help='SuperSearch API URL(s) to use instead of the default',
        nargs='*',
    )
    args = argparser.parse_args()
    run(args.crashes_per_url, *args.urls)


if __name__ == '__main__':
    import sys
    sys.exit(main())
