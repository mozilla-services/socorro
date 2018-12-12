# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import argparse
import os

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from six.moves.urllib.parse import urlparse

from socorro.scripts import WrappedTextHelpFormatter


DESCRIPTION = 'Manages databases'


def create_database():
    dsn = os.environ['DATABASE_URL']

    parsed = urlparse(os.environ['DATABASE_URL'])
    db_name = parsed.path[1:]
    adjusted_dsn = dsn[:-(len(db_name) + 1)]

    conn = psycopg2.connect(adjusted_dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    try:
        cursor.execute('CREATE DATABASE %s' % db_name)
        print('Created database "%s".' % db_name)
    except psycopg2.ProgrammingError:
        print('Database "%s" already exists.' % db_name)
        return 1


def drop_database():
    dsn = os.environ['DATABASE_URL']

    parsed = urlparse(os.environ['DATABASE_URL'])
    db_name = parsed.path[1:]
    adjusted_dsn = dsn[:-(len(db_name) + 1)]

    conn = psycopg2.connect(adjusted_dsn)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    try:
        cursor.execute('DROP DATABASE %s' % db_name)
        print('Database "%s" dropped.' % db_name)
    except psycopg2.ProgrammingError:
        print('Database "%s" does not exist.' % db_name)
        return 1


def main(argv=None):
    parser = argparse.ArgumentParser(
        formatter_class=WrappedTextHelpFormatter,
        description=DESCRIPTION.strip()
    )
    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True
    subparsers.add_parser('drop', help='drop an existing database')
    subparsers.add_parser('create', help='create an existing database')

    args = parser.parse_args()

    if args.cmd == 'drop':
        return drop_database()
    elif args.cmd == 'create':
        return create_database()
