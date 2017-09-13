#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import datetime
import os
import os.path
from urlparse import urlparse, parse_qs

import requests

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


def fetch_crashids(params):
    url = HOST + '/api/SuperSearch/'

    resp = requests.get(url, params)
    if resp.status_code == 200:
        hits = resp.json()['hits']
        crashids = [hit['uuid'] for hit in hits]
        return crashids

    raise Exception('Bad response: %s %s' % (resp.status_code, resp.content))


def extract_params(url):
    """Parses out params from the query string and drops any that start with _"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    for key in list(params.keys()):
        # Remove any params that start with a _ except _sort since that's helpful
        if key.startswith('_') and key != '_sort':
            del params[key]

    return params


def main(argv):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter,
        prog=os.path.basename(__file__),
        description=DESCRIPTION.strip(),
    )
    parser.add_argument(
        '--date', default='yesterday',
        help='Date to pull crash ids from (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--url', default='',
        help='Super Search url to pull crash ids from'
    )
    parser.add_argument(
        '--num', default=100, type=int,
        help='The number of crash ids you want'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Increase verbosity of output'
    )

    args = parser.parse_args(argv)

    if args.url:
        params = extract_params(args.url)
    else:
        params = {
            'product': 'Firefox'
        }

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

    params.update({
        '_results_number': args.num,
        '_columns': 'uuid'
    })
    if args.verbose:
        print('Params: %s' % params)

    crashids = fetch_crashids(params)
    for crashid in crashids:
        print(crashid)

    return 0
