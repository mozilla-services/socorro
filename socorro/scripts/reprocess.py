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

from socorro.scripts import WrappedTextHelpFormatter


DESCRIPTION = """
Sends specified crashes for reprocessing

This requires SOCORRO_REPROCESS_API_TOKEN to be set in the environment to a valid API token.

"""

DEFAULT_HOST = 'https://crash-stats.mozilla.com'
CHUNK_SIZE = 50
SLEEP = 1


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
    parser.add_argument('--host', help='host for system to reprocess in', default=DEFAULT_HOST)
    parser.add_argument('crashid', nargs='*', help='one or more crash ids to fetch data for')

    args = parser.parse_args(argv)

    # FIXME(willkg): Rethink this?
    api_token = os.environ.get('SOCORRO_REPROCESS_API_TOKEN')
    if not api_token:
        print('You need to set SOCORRO_REPROCESS_API_TOKEN in the environment')
        return 1

    url = args.host.rstrip('/') + '/api/Reprocessing/'

    # NOTE(willkg): This will pause until all crash ids are available which won't work for some
    # situations.
    crash_ids = list(args.crashid or sys.stdin)
    crash_ids = [item.strip() for item in crash_ids]
    print('Processing %s crashes...' % len(crash_ids))

    groups = list(chunkify(crash_ids, CHUNK_SIZE))
    for i, group in enumerate(groups):
        print('Processing group... (%s/%s)' % (i + 1, len(groups)))
        resp = session_with_retries(url).post(
            url,
            data={'crash_ids': group},
            headers={
                'Auth-Token': api_token
            }
        )
        if resp.status_code != 200:
            print('Got back non-200 status code: %s %s' % (resp.status_code, resp.content))
            continue

        time.sleep(SLEEP)

    print('Done!')
