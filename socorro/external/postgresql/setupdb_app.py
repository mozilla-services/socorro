#! /usr/bin/env python
"""
Create, prepare and load schema for Socorro PostgreSQL database.
"""
import sys
import psycopg2
import psycopg2.extensions
from psycopg2 import ProgrammingError
import re
import logging

from socorro.app.generic_app import App, main
from configman import Namespace


class PostgreSQLManager(object):
    def __init__(self, dsn, logger):
        self.conn = psycopg2.connect(dsn)
        self.conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.logger = logger

    def execute(self, sql, allowable_errors=None):
        cur = self.conn.cursor()
        try:
            cur.execute(sql)
        except ProgrammingError, e:
            if not allowable_errors:
                raise
            dberr = e.pgerror.strip().split('ERROR:  ')[1]
            if allowable_errors:
                for err in allowable_errors:
                    if re.match(err, dberr):
                        self.logger.warning(dberr)
                    else:
                        raise

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.conn.close()


class SocorroDB(App):
    app_name = 'setupdb'
    app_version = '0.2'
    app_description = __doc__

    required_config = Namespace()

    required_config.add_option(
        name='database_name',
        default='',
        doc='Name of database to manage',
    )

    required_config.add_option(
        name='database_hostname',
        default='',
        doc='Hostname to connect to database',
    )

    required_config.add_option(
        name='database_username',
        default='',
        doc='Username to connect to database',
    )

    required_config.add_option(
        name='database_password',
        default='',
        doc='Password to connect to database',
    )

    required_config.add_option(
        name='database_port',
        default='',
        doc='Port to connect to database',
    )

    required_config.add_option(
        name='dropdb',
        default=False,
        doc='Whether or not to drop database_name',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
    )

    required_config.add_option(
        name='no_schema',
        default=False,
        doc='Whether or not to load schema',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
    )

    required_config.add_option(
        name='citext',
        default='/usr/share/postgresql/9.0/contrib/citext.sql',
        doc='Name of citext.sql file',
    )

    def main(self):

        self.database_name = self.config['database_name']
        if not self.database_name:
            print "Syntax error: --database_name required"
            return 1

        self.no_schema = self.config.get('no_schema')
        self.citext = self.config.get('citext')

        dsn_template = 'dbname=%s'

        self.database_username = self.config.get('database_username')
        if self.database_username:
            dsn_template += ' user=%s' % self.database_username
        self.database_password = self.config.get('database_password')
        if self.database_password:
            dsn_template += ' password=%s' % self.database_password
        self.database_hostname = self.config.get('database_hostname')
        if self.database_hostname:
            dsn_template += ' host=%s' % self.database_hostname
        self.database_port = self.config.get('database_port')
        if self.database_port:
            dsn_template += ' port=%s' % self.database_port

        dsn = dsn_template % 'template1'

        with PostgreSQLManager(dsn, self.config.logger) as db:
            if self.config.get('dropdb'):
                if 'test' not in self.database_name:
                    confirm = raw_input(
                        'drop database %s [y/N]: ' % self.database_name)
                    if not confirm == "y":
                        logging.warn('NOT dropping table')
                        return 2

                db.execute('DROP DATABASE %s' % self.database_name,
                    ['database "%s" does not exist' % self.database_name])
                db.execute('DROP SCHEMA pgx_diag', ['schema "pgx_diag" does not exist'])

            db.execute('CREATE DATABASE %s' % self.database_name,
                       ['database "%s" already exists' % self.database_name])

        dsn = dsn_template % self.database_name

        with PostgreSQLManager(dsn, self.config.logger) as db:
            with open('sql/roles.sql') as f:
                db.execute(f.read())

            for lang in ['plpgsql', 'plperl']:
                db.execute('CREATE LANGUAGE "%s"' % lang,
                           ['language "%s" already exists' % lang])

            if not self.no_schema:
                with open('sql/schema.sql') as f:
                    db.execute(f.read(), ['schema "pgx_diag" already exists'])

                db.execute('SELECT weekly_report_partitions()')
            else:
                with open(self.citext) as f:
                    db.execute(f.read())
                db.execute(
                    'ALTER DATABASE %s OWNER TO breakpad_rw' %
                    self.database_name)
        return 0

if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(SocorroDB))
