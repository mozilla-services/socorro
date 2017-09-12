#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import datetime
import json
import os
import os.path

import requests

from socorro.lib.datetimeutil import JsonDTEncoder, utc_now
from socorro.scripts import WrappedTextHelpFormatter


DESCRIPTION = """
Fetches data for specific crashes or most recent crashes
"""

EPILOG = """
This script has two modes: fetching specific crashes and fetching arbitrary crashes.

If you specify crash ids, then it fetches data for those specific crashes. This mode requires an
auth-token to be in the environment. For example:

    $ SOCORRO_API_TOKEN=xyz ./scripts/fetch_crash_data.py CRASHID

To create an API token for Socorro in -prod, visit:

    https://crash-stats.mozilla.com/api/tokens/

If you don't specify any crashes, then this will fetch N number of crashes. This will not use your
API token. This will only fetch publicly available raw crash data. For example:

    $ ./scripts/fetch_crash_data.py --num=10

"""

# FIXME(willkg): Hard-coded host that we might want to make configurable some day
HOST = 'https://crash-stats.mozilla.com'


class CrashDoesNotExist(Exception):
    pass


def create_dir_if_needed(d):
    if not os.path.exists(d):
        os.makedirs(d)


def fetch_crash(outputdir, api_token, crash_id):
    if api_token:
        headers = {
            'Auth-Token': api_token
        }
    else:
        headers = {}

    # Fetch raw crash metadata
    print('Fetching %s' % crash_id)
    resp = requests.get(
        HOST + '/api/RawCrash/',
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
            HOST + '/api/RawCrash/',
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


def fetch_crashids(outputdir, datestamp, num):
    if datestamp == 'yesterday':
        startdate = utc_now() - datetime.timedelta(days=1)
    else:
        startdate = datetime.datetime.strptime(datestamp, '%Y-%m-%d')

    enddate = startdate + datetime.timedelta(days=1)

    url = HOST + '/api/SuperSearch/'
    params = {
        'product': 'Firefox',
        '_results_number': 1000,
        '_columns': 'uuid',
        'date': ['>=%s' % startdate.strftime('%Y-%m-%d'), '<%s' % enddate.strftime('%Y-%m-%d')],
    }

    resp = requests.get(url, params)
    if resp.status_code == 200:
        crashids = []
        for hit in resp.json()['hits']:
            crash_id = hit['uuid']
            fn = os.path.join(
                outputdir, 'v2', 'raw_crash', crash_id[0:3], '20' + crash_id[-6:], crash_id
            )
            if os.path.exists(fn):
                continue

            crashids.append(crash_id)
            if len(crashids) >= num:
                break

        return crashids

    raise Exception('Bad response: %s %s' % (resp.status_code, resp.content))


def main(argv):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter,
        prog=os.path.basename(__file__),
        description=DESCRIPTION.strip(),
        epilog=EPILOG.strip(),
    )
    parser.add_argument(
        '--num', default=10, type=int,
        help=(
            'if you are not specifying specific crash ids, this is the number of crashes to '
            'fetch'
        )
    )
    parser.add_argument(
        '--date', default='yesterday',
        help=(
            'if you are not specifying specific crash ids, this is the date to retreive crashes '
            'from (YYYY-MM-DD)'
        )
    )
    parser.add_argument(
        '--outputdir', default='crashdata',
        help='directory to place crash data in; defaults to "crashdata"'
    )
    parser.add_argument('crashid', nargs='*', help='one or more crash ids to fetch data for')

    args = parser.parse_args(argv)

    # Validate outputdir and exit if it doesn't exist or isn't a directory
    outputdir = args.outputdir
    if os.path.exists(outputdir) and not os.path.isdir(outputdir):
        print('%s is not a directory. Please fix. Exiting.' % outputdir)
        return 1

    crashes = []
    if args.crashid:
        api_token = os.environ.get('SOCORRO_API_TOKEN')
        print('Using api token: %s' % api_token)

        crashes = args.crashid
    else:
        api_token = None
        crashes = fetch_crashids(outputdir, args.date, args.num)

    for crash_id in crashes:
        print('Working on %s...' % crash_id)
        fetch_crash(outputdir, api_token, crash_id)

    return 0
