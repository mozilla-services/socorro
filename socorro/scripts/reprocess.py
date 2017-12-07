#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import os
import sys
import time
import urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from socorro.lib.util import chunkify
from socorro.scripts import WrappedTextHelpFormatter


DESCRIPTION = """
Sends specified crashes for reprocessing

This requires SOCORRO_REPROCESS_API_TOKEN to be set in the environment to a valid API token.

"""

DEFAULT_HOST = 'https://crash-stats.mozilla.com'
CHUNK_SIZE = 50
SLEEP_DEFAULT = 1


def session_with_retries(url):
    base_url = urlparse.urlparse(url).netloc
    scheme = urlparse.urlparse(url).scheme

    retries = Retry(total=32, backoff_factor=1, status_forcelist=[429])

    s = requests.Session()
    s.mount(scheme + '://' + base_url, HTTPAdapter(max_retries=retries))

    return s


def main(argv):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter,
        prog=os.path.basename(__file__),
        description=DESCRIPTION.strip(),
    )
    parser.add_argument(
        '--sleep',
        help='how long in seconds to sleep before submitting the next group',
        type=int,
        default=SLEEP_DEFAULT
    )
    parser.add_argument('--host', help='host for system to reprocess in', default=DEFAULT_HOST)
    parser.add_argument('crashid', nargs='*', help='one or more crash ids to fetch data for')

    args = parser.parse_args(argv)

    api_token = os.environ.get('SOCORRO_REPROCESS_API_TOKEN')
    if not api_token:
        print('You need to set SOCORRO_REPROCESS_API_TOKEN in the environment')
        return 1

    url = args.host.rstrip('/') + '/api/Reprocessing/'

    if args.crashid:
        crash_ids = args.crashid
    elif not sys.stdin.isatty():
        # If a script is piping to this script, then isatty() returns False. If there is no script
        # piping to this script, then isatty() returns True and if we do list(sys.stdin), it'll
        # block waiting for intput.
        crash_ids = list(sys.stdin)
    else:
        crash_ids = []

    # If there are no crashids, then print help and exit
    if not crash_ids:
        parser.print_help()
        return 0

    crash_ids = [item.strip() for item in crash_ids]

    print('Sending reprocessing requests to: %s' % url)
    session = session_with_retries(url)

    print('Reprocessing %s crashes sleeping %s seconds between groups...' % (
        len(crash_ids), args.sleep
    ))

    groups = list(chunkify(crash_ids, CHUNK_SIZE))
    for i, group in enumerate(groups):
        print('Processing group ending with %s ... (%s/%s)' % (group[-1], i + 1, len(groups)))
        resp = session.post(
            url,
            data={'crash_ids': group},
            headers={
                'Auth-Token': api_token
            }
        )
        if resp.status_code != 200:
            print('Got back non-200 status code: %s %s' % (resp.status_code, resp.content))
            continue

        # NOTE(willkg): We sleep here because the webapp has a bunch of rate limiting and we don't
        # want to trigger that. It'd be nice if we didn't have to do this.
        time.sleep(args.sleep)

    print('Done!')
