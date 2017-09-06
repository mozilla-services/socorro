# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from __future__ import print_function

import argparse
import csv
import logging
import logging.config
import os
import sys

import requests

from socorro.lib.treelib import tree_get
from socorro.signature import SignatureGenerator


DESCRIPTION = """
Given crash ids, pulls down information from Socorro, generates signatures, and prints
signature information.
"""

EPILOG = """
Note: In order for the SignatureJitCategory rule to work, you need a valid API token from
Socorro that has "View Personally Identifiable Information" permission.
"""

logger = logging.getLogger('socorro.signature')


# FIXME(willkg): This hits production. We might want it configurable.
API_URL = 'https://crash-stats.mozilla.com/api/'


def setup_logging(logging_level):
    dc = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'bare': {
                'format': '%(levelname)s: %(message)s'
            }
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'bare',
            },
        },
        'loggers': {
            'socorro': {
                'propagate': False,
                'handlers': ['console'],
                'level': logging_level,
            },
        },
    }
    logging.config.dictConfig(dc)


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


def main(args):
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
        'crashids', metavar='crashid', nargs='+', help='crash id to generate signatures for'
    )
    args = parser.parse_args()

    if args.format == 'csv':
        outputter = CSVOutput
    else:
        outputter = TextOutput

    if args.verbose:
        logging_level = 'DEBUG'
    else:
        logging_level = 'INFO'

    api_token = os.environ.get('SOCORRO_API_TOKEN', '')

    setup_logging(logging_level)

    generator = SignatureGenerator(debug=args.verbose)

    with outputter() as out:
        for crash_id in args.crashids:
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

            raw_crash_minimal = {
                'JavaStackTrace': raw_crash.get('JavaStackTrace', None),
                'OOMAllocationSize': raw_crash.get('OOMAllocationSize', None),
                'AbortMessage': raw_crash.get('AbortMessage', None),
                'AsyncShutdownTimeout': raw_crash.get('AsyncShutdownTimeout', None),
                'ipc_channel_error': raw_crash.get('ipc_channel_error', None),
                'additional_minidumps': raw_crash.get('additional_minidumps', None),
                'IPCMessageName': raw_crash.get('IPCMessageName', None),
            }

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

            processed_crash_minimal = {
                'hang_type': processed_crash.get('hang_type', None),
                'json_dump': {
                    'threads': tree_get(processed_crash, 'json_dump.threads', default=[]),
                    'system_info': {
                        'os': tree_get(processed_crash, 'json_dump.system_info.os', default=''),
                    },
                    'crash_info': {
                        'crashing_thread': tree_get(
                            processed_crash, 'json_dump.crash_info.crashing_thread', default=None
                        ),
                    },
                },
                # NOTE(willkg): Classifications aren't available via the public API.
                'classifications': {
                    'jit': {
                        'category': tree_get(processed_crash, 'classifications.jit.category', ''),
                    },
                },
                'mdsw_status_string': processed_crash.get('mdsw_status_string', None),

                # This needs to be an empty string--the signature generator fills it in.
                'signature': ''
            }

            ret = generator.generate(raw_crash_minimal, processed_crash_minimal)

            out.data(crash_id, old_signature, ret['signature'], ret['notes'])


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
