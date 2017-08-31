# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Given crash ids, returns signatures and signature notes.

Usage:

    python -m socorro.signature <CRASHID> [<CRASHID>...]

"""

import argparse
import logging
import logging.config
import sys

import requests

from socorro.lib.treelib import tree_get
from socorro.signature import SignatureGenerator


logger = logging.getLogger('socorro.signature')


# FIXME(willkg): This hits production. We might want it configurable.
API_URL = 'https://crash-stats.mozilla.com/api/'


def main(args):
    """
    Takes crash data via args and generates a Socorro signature
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v', '--verbose', help='increase output verbosity', action='store_true'
    )
    parser.add_argument(
        'crashids', metavar='crashid', nargs='+', help='crash id to generate signatures for'
    )
    args = parser.parse_args()

    if args.verbose:
        logging_level = 'DEBUG'
    else:
        logging_level = 'INFO'

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

    for crash_id in args.crashids:
        print('Working on: %s' % crash_id)

        ret = requests.get(API_URL + '/RawCrash/', params={'crash_id': crash_id})
        if ret.status_code == 404:
            logger.warning('WARNING: Crash %s does not exist.' % crash_id)
            continue

        raw_crash = ret.json()

        raw_crash_minimal = {
            'JavaStackTrace': raw_crash.get('JavaStackTrace', None),
            'OOMAllocationSize': raw_crash.get('OOMAllocationSize', None),
            'AbortMessage': raw_crash.get('AbortMessage', None),
            'AsyncShutdownTimeout': raw_crash.get('AsyncShutdownTimeout', None),
            'ipc_channel_error': raw_crash.get('ipc_channel_error', None),
            'additional_minidumps': raw_crash.get('additional_minidumps', None),
            'IPCMessageName': raw_crash.get('IPCMessageName', None),
        }

        ret = requests.get(API_URL + '/ProcessedCrash/', params={'crash_id': crash_id})
        processed_crash = ret.json()

        old_signature = processed_crash['signature']
        crashing_thread = tree_get(processed_crash, 'json_dump.crash_info.crashing_thread')

        processed_crash_minimal = {
            'hang_type': processed_crash.get('hang_type', None),
            'json_dump': {
                'threads': tree_get(processed_crash, 'json_dump.threads', []),
                'system_info': {
                    'os': tree_get(processed_crash, 'json_dump.system_info.os', ''),
                },
                'crash_info': {
                    'crashing_thread': crashing_thread,
                },
                'classifications': {
                    'jit': {
                        'category': tree_get(processed_crash, 'classifications.jit.category', ''),
                    }
                },
            },
            'mdsw_status_string': processed_crash.get('mdsw_status_string', None),

            # This needs to be an empty string--the signature generator fills it in.
            'signature': ''
        }

        ret = SignatureGenerator().generate(raw_crash_minimal, processed_crash_minimal)

        # NOTE(willkg): We use print here instead of logging because we might want to change the
        # output format and this is the place for that.
        print('Original: %s' % old_signature)
        print('New:      %s' % ret['signature'])
        if ret['notes']:
            print('Notes: (%d)' % len(ret['notes']))
            for note in ret['notes']:
                print('   %s' % note)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
