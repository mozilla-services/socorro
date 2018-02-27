#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import datetime
from functools import total_ordering
import sys
from urlparse import urlparse, parse_qs

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from socorro.lib.datetimeutil import utc_now
from socorro.scripts import WrappedTextHelpFormatter


DESCRIPTION = """
Fetches a set of crash ids using Super Search

There are two ways to run this. First is to use a url from an actual Super Search on crash-stats.
This script will then pull out the parameters and base the query on that. You can override those
parameters with command line arguments.

The second is to just specify command line arguments and the query will be based on that.

"""

HOST = 'https://crash-stats.mozilla.com'

MAX_PAGE = 1000


@total_ordering
class Infinity(object):
    """Infinity is greater than anything else except other Infinities

    NOTE(willkg): There are multiple infinities and not all infinities are equal, so what we're
    doing here is wrong, but it's helpful. We can rename it if someone gets really annoyed.

    """
    def __eq__(self, obj):
        return isinstance(obj, Infinity)

    def __lt__(self, obj):
        return False

    def __repr__(self):
        return 'Infinity'

    def __sub__(self, obj):
        if isinstance(obj, Infinity):
            return 0
        return self

    def __rsub__(self, obj):
        # We don't need to deal with negative infinities, so let's not
        raise ValueError('This Infinity does not support right-hand-side')


# For our purposes, there is only one infinity
INFINITY = Infinity()


def fetch_crashids(params, num_results):
    """Generator that returns crash ids

    :arg dict params: dict of super search parameters to base the query on
    :arg varies num: number of results to get or INFINITY

    :returns: generator of crash ids

    """
    url = HOST + '/api/SuperSearch/'

    # Set up retrying on 429s
    retries = Retry(total=32, backoff_factor=1, status_forcelist=[429])
    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    # Set up first page
    params['_results_offset'] = 0
    params['_results_number'] = min(MAX_PAGE, num_results)

    # Fetch pages of crash ids until we've gotten as many as we want or there aren't any more to get
    crashids_count = 0
    while True:
        resp = session.get(url, params=params)
        if resp.status_code != 200:
            raise Exception('Bad response: %s %s' % (resp.status_code, resp.content))

        hits = resp.json()['hits']

        for hit in hits:
            crashids_count += 1
            yield hit['uuid']

            # If we've gotten as many crashids as we need, we return
            if crashids_count >= num_results:
                return

        # If there are no more crash ids to get, we return
        total = resp.json()['total']
        if not hits or crashids_count >= total:
            return

        # Get the next page, but only as many results as we need
        params['_results_offset'] += MAX_PAGE
        params['_results_number'] = min(
            # MAX_PAGE is the maximum we can request
            MAX_PAGE,

            # The number of results Super Search can return to us that is hasn't returned so far
            total - crashids_count,

            # The numver of results we want that we haven't gotten, yet
            num_results - crashids_count
        )


def extract_params(url):
    """Parses out params from the query string and drops any that start with _"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    for key in list(params.keys()):
        # Remove any params that start with a _ except _sort since that's helpful
        if key.startswith('_') and key != '_sort':
            del params[key]

    return params


def main(argv=None):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter,
        description=DESCRIPTION.strip(),
    )
    parser.add_argument(
        '--date', default='yesterday',
        help='Date to pull crash ids from (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--signature-contains', default='', dest='signature',
        help='Signature contains this string'
    )
    parser.add_argument(
        '--url', default='',
        help='Super Search url to base query on'
    )
    parser.add_argument(
        '--num', default=100,
        help='The number of crash ids you want or "all" for all of them'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Increase verbosity of output'
    )

    if argv is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(argv)

    # Start with params from --url value or product=Firefox
    if args.url:
        params = extract_params(args.url)
    else:
        params = {
            'product': 'Firefox'
        }

    params['_columns'] = 'uuid'

    # Override with date if specified
    datestamp = args.date
    if 'date' not in params or datestamp != 'yesterday':
        if datestamp == 'yesterday':
            startdate = utc_now() - datetime.timedelta(days=1)
        else:
            startdate = datetime.datetime.strptime(datestamp, '%Y-%m-%d')

        enddate = startdate + datetime.timedelta(days=1)
        params['date'] = [
            '>=%s' % startdate.strftime('%Y-%m-%d'),
            '<%s' % enddate.strftime('%Y-%m-%d')
        ]

    # Override with signature-contains if specified
    sig = args.signature
    if sig:
        params['signature'] = '~' + sig

    num_results = args.num
    if num_results == 'all':
        num_results = INFINITY

    else:
        try:
            num_results = int(num_results)
        except ValueError:
            print('num needs to be an integer or "all"')
            return 1

    if args.verbose:
        print('Params: %s' % params)

    for crashid in fetch_crashids(params, num_results):
        print(crashid)

    return 0


if __name__ == '__main__':
    sys.exit(main())
