#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Create, prepare and load schema for Socorro PostgreSQL database.
"""
from __future__ import unicode_literals

import cStringIO
import logging
import os
import re
import sys
from glob import glob

from alembic import command
from alembic.config import Config
from configman import Namespace, class_converter
from psycopg2 import ProgrammingError
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable

from socorro.app.socorro_app import App, main
from socorro.external.postgresql import staticdata, fakedata
from socorro.external.postgresql.connection_context import default_from_url
from socorro.external.postgresql.models import *
from socorro.external.postgresql.postgresqlalchemymanager import PostgreSQLAlchemyManager


###########################################
##  Database creation object
###########################################
class SocorroDBApp(App):
    """
    SocorroDBApp
        This function creates a base PostgreSQL schema for Socorro

    Notes:

        All functions declared need '%' to be escaped as '%%'

    """
    app_name = 'setupdb'
    app_version = '0.2'
    app_description = __doc__
    metadata = ''

    required_config = Namespace()

    required_config.add_option(
        'database_class',
        default=
            'socorro.external.postgresql.connection_context.ConnectionContext',
        doc='the class responsible for connecting to Postgres',
        reference_value_from='resource.postgresql',
        from_string_converter=class_converter
    )

    required_config.add_option(
        name='database_superusername',
        default=default_from_url('username', 'test'),
        doc='Username to connect to database',
    )

    required_config.add_option(
        name='database_superuserpassword',
        default=default_from_url('password', 'aPassword'),
        doc='Password to connect to database',
        secret=True,
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
        name='force',
        default=False,
        doc='Whether or not to override safety checks',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
    )

    required_config.add_option(
        name='read_write_users',
        default='postgres, breakpad_rw, monitor',
        doc='Name of database to manage',
    )

    required_config.add_option(
        name='read_only_users',
        default='breakpad_ro, breakpad, analyst',
        doc='Name of database to manage',
    )

    required_config.add_option(
        name='no_staticdata',
        default=False,
        doc='Whether or not to fill in static data Socorro needs to function',
    )

    required_config.add_option(
        name='fakedata',
        default=False,
        doc='Whether or not to fill the data with synthetic test data',
    )

    required_config.add_option(
        name='fakedata_days',
        default=7,
        doc='How many days of synthetic test data to generate'
    )

    required_config.add_option(
        name='alembic_config',
        default=os.path.abspath('config/alembic.ini'),
        doc='Path to alembic configuration file'
    )

    required_config.add_option(
        name='default_password',
        default='aPassword',
        doc='Default password for roles created by setupdb_app.py',
        secret=True,
    )

    required_config.add_option(
        name='unlogged',
        default=False,
        doc='Create all tables with UNLOGGED for running tests',
    )

    required_config.add_option(
        name='no_roles',
        default=False,
        doc='Whether or not to set up roles',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
    )

    @staticmethod
    def get_application_defaults():
        """since this app is more of an interactive app than the others, the
        logging of config information is rather disruptive.  Override the
        default logging level to one that is less annoying."""
        return {
            'logging.stderr_error_logging_level': 40  # only ERROR or worse
        }

    def bulk_load_table(self, db, table):
        io = cStringIO.StringIO()
        for line in table.generate_rows():
            io.write('\t'.join([str(x) for x in line]))
            io.write('\n')
        io.seek(0)
        db.bulk_load(io, table.table, table.columns, '\t')

    def import_staticdata(self, db):
        for table in staticdata.tables:
            table = table()
            self.bulk_load_table(db, table)

    def generate_fakedata(self, db, fakedata_days):
        # Set up partitions before loading report data
        db.session.execute("""
                SELECT weekly_report_partitions(4, now()-'2 weeks'::interval)
        """)

        start_date = end_date = None
        for table in fakedata.tables:
            table = table(days=fakedata_days)

            if start_date:
                if start_date > table.start_date:
                    start_date = table.start_date
            else:
                start_date = table.start_date

            if end_date:
                if end_date < table.start_date:
                    end_date = table.end_date
            else:
                end_date = table.end_date

            self.bulk_load_table(db, table)


        db.session.execute("""
                SELECT backfill_matviews(cast(:start as DATE),
                cast(:end as DATE))
            """, dict(zip(["start", "end"], list((start_date, end_date)))))

        db.session.execute("""
                UPDATE product_versions
                SET featured_version = TRUE
                WHERE version_string IN (:one, :two, :three, :four)
            """, dict(zip(["one", "two", "three", "four"],
                      list(fakedata.featured_versions))))

    def construct_db_url(self, dbname=None, superuser=False):
        """Takes a URL to connect to Postgres and updates database name
            or superuser name/password as indicated"""
        database_username = self.config.get('database_username')
        database_password = self.config.get('database_password')
        database_hostname = self.config.get('database_hostname')
        database_port = self.config.get('database_port')
        database_name = dbname

        if superuser:
            database_username = self.config.get('database_superusername')
            database_password = self.config.get('database_superuserpassword')

        # construct a URL
        url = 'postgresql://'
        if database_username:
            url += '%s' % database_username
        if database_password:
            url += ':%s' % database_password
        url += '@'
        if database_hostname:
            url += '%s' % database_hostname
        if database_port:
            url += ':%s' % database_port
        url += '/%s' % dbname
        return url

    def main(self):
        self.database_name = self.config.get('database_name')
        if not self.database_name:
            print "Syntax error: --database_name required"
            return 1

        self.no_schema = self.config.get('no_schema')
        self.no_roles = self.config.get('no_roles')

        self.force = self.config.get('force')

        # self.database_url = self.config.get('database_url')

        sa_url = self.construct_db_url('postgres', True)

        if self.config.unlogged:
            @compiles(CreateTable)
            def create_table(element, compiler, **kw):
                text = compiler.visit_create_table(element, **kw)
                text = re.sub("^\sCREATE(.*TABLE)",
                              lambda m: "CREATE UNLOGGED %s" %
                              m.group(1), text)
                return text

        with PostgreSQLAlchemyManager(sa_url, self.config.logger,
                                      autocommit=False) as db:
            if not db.min_ver_check(90200):
                print 'ERROR - unrecognized PostgreSQL version: %s' % \
                    db.version_string()
                print 'Only 9.2+ is supported at this time'
                return 1

            connection = db.engine.connect()
            if self.config.get('dropdb'):
                if 'test' not in self.database_name and not self.force:
                    confirm = raw_input(
                        'drop database %s [y/N]: ' % self.database_name)
                    if not confirm == "y":
                        logging.warn('NOT dropping table')
                        return 2

                try:
                    # work around for autocommit behavior
                    connection.execute('commit')
                    connection.execute('DROP DATABASE %s' % self.database_name)
                except exc.ProgrammingError, e:
                    if re.search(
                        'database "%s" does not exist' % self.database_name,
                        e.orig.pgerror.strip()):
                        # already done, no need to rerun
                        print "The DB %s doesn't exist" % self.database_name

            try:
                # work around for autocommit behavior
                connection.execute('commit')
                connection.execute("CREATE DATABASE %s ENCODING 'utf8'" %
                                   self.database_name)
            except exc.ProgrammingError, e:
                if re.search(
                    'database "%s" already exists' % self.database_name,
                    e.orig.pgerror.strip()):
                    # already done, no need to rerun
                    print "The DB %s already exists" % self.database_name
                    return 0
                raise

            if self.no_roles:
                print "Skipping role creation"
            else:
                db.create_roles(self.config)
            connection.close()

        # Reconnect to set up schema, types and procs
        sa_url = self.construct_db_url(self.database_name, False)
        alembic_cfg = Config(self.config.alembic_config)
        alembic_cfg.set_main_option("sqlalchemy.url", sa_url)
        with PostgreSQLAlchemyManager(sa_url, self.config.logger) as db:
            connection = db.engine.connect()
            db.setup_admin()
            if self.no_schema:
                db.commit()
                return 0
            # Order matters with what follows
            db.create_types()

            db.create_procs()
            db.set_sequence_owner('breakpad_rw')
            db.commit()

            db.create_tables()
            db.set_table_owner('breakpad_rw')
            db.create_views()
            db.commit()

            db.set_grants(self.config)  # config has user lists
            if not self.config['no_staticdata']:
                self.import_staticdata(db)
            if self.config['fakedata']:
                self.generate_fakedata(db, self.config['fakedata_days'])
            db.commit()
            command.stamp(alembic_cfg, "heads")
            db.set_default_owner(self.database_name)
            db.session.close()

        return 0

if __name__ == "__main__":
    sys.exit(main(SocorroDBApp))
