#!/usr/bin/env python

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import os
import os.path

import psycopg2

from socorro.cron.buildutil import insert_build
from socorro.scripts import get_envvar, WrappedTextHelpFormatter


EPILOG = """
This replays an ftpscraper log which will insert product_versions data without
having to run ftpscraper.
"""


def main(argv=None):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter,
        description='Replay an ftpscraper log',
        epilog=EPILOG.strip(),
    )
    parser.add_argument('ftpscraperlog', help='the ftpscraper log to replay')

    if argv is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(argv)

    ftpscraperlog = args.ftpscraperlog

    if not os.path.exists(ftpscraperlog):
        print('ftpscraper log "%s" does not exist. Exiting.' % ftpscraperlog)
        return 1

    database_url = get_envvar('DATABASE_URL')
    connection = psycopg2.connect(database_url)

    cursor = connection.cursor()

    with open(ftpscraperlog, 'r') as fp:
        for line in fp:
            if ' adding (' not in line or ')' not in line:
                continue

            line = line.strip()
            params = line[line.find('('):line.find(')') + 1]
            params = eval(params)

            print('(replay) adding %s' % (params,))
            insert_build(cursor, *params, ignore_duplicates=True)
