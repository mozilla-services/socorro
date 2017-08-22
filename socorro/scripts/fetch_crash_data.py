#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import json
import os
import os.path

import requests

from socorro.lib.datetimeutil import JsonDTEncoder
from socorro.scripts import WrappedTextHelpFormatter


EPILOG = """
Given a crash id, fetches crash data and puts it in specified directory

This requires an auth-token to be in the environment::

    SOCORRO_API_TOKEN=xyz

To create an API token for Socorro in -prod, visit:

    https://crash-stats.mozilla.com/api/tokens/

"""


class CrashDoesNotExist(Exception):
    pass


def create_dir_if_needed(d):
    if not os.path.exists(d):
        os.makedirs(d)


def fetch_crash(outputdir, api_token, crash_id):
    headers = {
        'Auth-Token': api_token
    }

    # Fetch raw crash metadata
    print('Fetching %s' % crash_id)
    resp = requests.get(
        'https://crash-stats.mozilla.com/api/RawCrash/',
        params={
            'crash_id': crash_id,
            'format': 'meta',
        },
        headers=headers,
    )
    if resp.status_code == 404:
        raise CrashDoesNotExist(crash_id)

    raw_crash = resp.json()

    # Fetch dumps from -prod
    dumps = {}
    dump_names = raw_crash.get('dump_checksums', {}).keys()
    for dump_name in dump_names:
        print('Fetching %s -> %s' % (crash_id, dump_name))
        if dump_name == 'upload_file_minidump':
            dump_name = 'dump'

        resp = requests.get(
            'https://crash-stats.mozilla.com/api/RawCrash/',
            params={
                'crash_id': crash_id,
                'format': 'raw',
                'name': dump_name
            },
            headers=headers,
        )

        if resp.status_code != 200:
            raise Exception('Something unexpected happened. status_code %s, content %s' % (
                resp.status_code, resp.content)
            )

        dumps[dump_name] = resp.content

    # Save everything to file system in the right place
    # http://antenna.readthedocs.io/en/latest/architecture.html#aws-s3-file-hierarchy

    # Save raw crash to file system
    fn = os.path.join(outputdir, 'v2', 'raw_crash', crash_id[0:3], '20' + crash_id[-6:], crash_id)
    create_dir_if_needed(os.path.dirname(fn))
    with open(fn, 'w') as fp:
        json.dump(raw_crash, fp, cls=JsonDTEncoder, indent=2, sort_keys=True)

    # Save dump_names to file system
    fn = os.path.join(outputdir, 'v1', 'dump_names', crash_id)
    create_dir_if_needed(os.path.dirname(fn))
    with open(fn, 'w') as fp:
        json.dump(dumps.keys(), fp)

    # Save dumps to file system
    for dump_name, data in dumps.items():
        if dump_name == 'upload_file_minidump':
            dump_name = 'dump'

        fn = os.path.join(outputdir, 'v1', dump_name, crash_id)
        create_dir_if_needed(os.path.dirname(fn))
        with open(fn, 'wb') as fp:
            fp.write(data)


def main(argv):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter,
        prog=os.path.basename(__file__),
        description='Fetches crash data from crash-stats.mozilla.com system',
        epilog=EPILOG.strip(),
    )
    parser.add_argument('outputdir', help='directory to place crash data in')
    parser.add_argument('crashid', nargs='+', help='one or more crash ids to fetch data for')

    args = parser.parse_args(argv)

    # Validate outputdir and exit if it doesn't exist or isn't a directory
    outputdir = args.outputdir
    if os.path.exists(outputdir) and not os.path.isdir(outputdir):
        print('%s is not a directory. Please fix. Exiting.' % outputdir)
        return 1

    api_token = os.environ.get('SOCORRO_API_TOKEN')
    print('Using api token: %s' % api_token)

    for crash_id in args.crashid:
        print('Working on %s...' % crash_id)
        fetch_crash(outputdir, api_token, crash_id)

    return 0
