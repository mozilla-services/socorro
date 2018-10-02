# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function

import argparse
import csv
import os
import sys

import requests

from .generator import SignatureGenerator
from .utils import convert_to_crash_data


DESCRIPTION = """
Given one or more crash ids via command line or stdin (one per line), pulls down information from
Socorro, generates signatures, and prints signature information.
"""

EPILOG = """
Note: In order for the SignatureJitCategory rule to work, you need a valid API token from
Socorro that has "View Personally Identifiable Information" permission.
"""

# FIXME(willkg): This hits production. We might want it configurable.
API_URL = 'https://crash-stats.mozilla.com/api'


class OutputBase:
    """Base class for outputter classes

    Outputter classes are context managers. If they require start/top or begin/end semantics, they
    should implement ``__enter__`` and ``__exit__``.

    Otherwise they can just implement ``data`` and should be fine.

    """
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def warning(self, line):
        """Prints out a warning line to stderr

        :arg str line: the line to print to stderr

        """
        print('WARNING: %s' % line, file=sys.stderr)

    def data(self, crash_id, old_sig, new_sig, notes):
        """Outputs a data point

        :arg str crash_id: the crash id for the signature generated

        :arg str old_sig: the old signature retrieved in the processed crash

        :arg str new_sig: the new generated signature

        :arg list notes: any processor notes

        """
        pass


class TextOutput(OutputBase):
    def data(self, crash_id, old_sig, new_sig, notes):
        print('Crash id: %s' % crash_id)
        print('Original: %s' % old_sig)
        print('New:      %s' % new_sig)
        print('Same?:    %s' % (old_sig == new_sig))

        if notes:
            print('Notes:    (%d)' % len(notes))
            for note in notes:
                print('          %s' % note)


class CSVOutput(OutputBase):
    def __enter__(self):
        self.out = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)
        self.out.writerow(['crashid', 'old', 'new', 'same?', 'notes'])
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.out = None

    def data(self, crash_id, old_sig, new_sig, notes):
        self.out.writerow([crash_id, old_sig, new_sig, str(old_sig == new_sig), notes])


def fetch(endpoint, crash_id, api_token=None):
    kwargs = {
        'params': {
            'crash_id': crash_id
        }
    }
    if api_token:
        kwargs['headers'] = {
            'Auth-Token': api_token
        }

    return requests.get(API_URL + endpoint, **kwargs)


def main(argv=None):
    """Takes crash data via args and generates a Socorro signature

    """
    parser = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG)
    parser.add_argument(
        '-v', '--verbose', help='increase output verbosity', action='store_true'
    )
    parser.add_argument(
        '--format', help='specify output format: csv, text (default)'
    )
    parser.add_argument(
        '--different-only', dest='different', action='store_true',
        help='limit output to just the signatures that changed',
    )
    parser.add_argument(
        'crashids', metavar='crashid', nargs='*', help='crash id to generate signatures for'
    )

    if argv is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(argv)

    if args.format == 'csv':
        outputter = CSVOutput
    else:
        outputter = TextOutput

    api_token = os.environ.get('SOCORRO_API_TOKEN', '')

    generator = SignatureGenerator(debug=args.verbose)
    if args.crashids:
        crashids_iterable = args.crashids
    elif not sys.stdin.isatty():
        # If a script is piping to this script, then isatty() returns False. If
        # there is no script piping to this script, then isatty() returns True
        # and if we do list(sys.stdin), it'll block waiting for input.
        crashids_iterable = list(sys.stdin)
    else:
        crashids_iterable = []

    if not crashids_iterable:
        parser.print_help()
        return 0

    with outputter() as out:
        for crash_id in crashids_iterable:
            crash_id = crash_id.strip()

            resp = fetch('/RawCrash/', crash_id, api_token)
            if resp.status_code == 404:
                out.warning('%s: does not exist.' % crash_id)
                continue
            if resp.status_code == 429:
                out.warning('API rate limit reached. %s' % resp.content)
                # FIXME(willkg): Maybe there's something better we could do here. Like maybe wait a
                # few minutes.
                return 1
            if resp.status_code == 500:
                out.warning('HTTP 500: %s' % resp.content)
                continue

            raw_crash = resp.json()

            # If there's an error in the raw crash, then something is wrong--probably with the API
            # token. So print that out and exit.
            if 'error' in raw_crash:
                out.warning('Error fetching raw crash: %s' % raw_crash['error'])
                return 1

            resp = fetch('/ProcessedCrash/', crash_id, api_token)
            if resp.status_code == 404:
                out.warning('%s: does not have processed crash.' % crash_id)
                continue
            if resp.status_code == 429:
                out.warning('API rate limit reached. %s' % resp.content)
                # FIXME(willkg): Maybe there's something better we could do here. Like maybe wait a
                # few minutes.
                return 1
            if resp.status_code == 500:
                out.warning('HTTP 500: %s' % resp.content)
                continue

            processed_crash = resp.json()

            # If there's an error in the processed crash, then something is wrong--probably with the
            # API token. So print that out and exit.
            if 'error' in processed_crash:
                out.warning('Error fetching processed crash: %s' % processed_crash['error'])
                return 1

            old_signature = processed_crash['signature']
            crash_data = convert_to_crash_data(raw_crash, processed_crash)

            ret = generator.generate(crash_data)

            if not args.different or old_signature != ret['signature']:
                out.data(crash_id, old_signature, ret['signature'], ret['notes'])
