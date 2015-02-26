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

from alembic import command
from alembic.config import Config
from configman import Namespace
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateTable

from socorro.app.socorro_app import App, main
from socorro.external.postgresql import staticdata, fakedata
from socorro.external.postgresql.models import *
from socorro.external.postgresql.postgresqlalchemymanager import (
    PostgreSQLAlchemyManager
)


###########################################
##  Database creation object
###########################################
class SocorroDBApp(App):
    """
    SocorroDBApp
        This function creates a base PostgreSQL schema

    Notes:
        All functions declared need '%' to be escaped as '%%'

    """
    app_name = 'setupdb'
    app_version = '0.2'
    app_description = __doc__
    metadata = ''

    required_config = Namespace()

    required_config.add_option(
        name='database_url',
        default=None,
        doc='URL of database to connect to',
    )
    required_config.add_option(
        name='on_heroku',
        default=False,
        doc='Setup on a Heroku Postgres instance',
    )
    required_config.add_option(
        name='database_name',
        default='socorro_integration_test',
        doc='Name of database to manage',
    )

    required_config.add_option(
        name='database_hostname',
        default='localhost',
        doc='Hostname to connect to database',
    )

    required_config.add_option(
        name='database_username',
        default='breakpad_rw',
        doc='Username to connect to database',
    )

    required_config.add_option(
        name='database_password',
        default='aPassword',
        doc='Password to connect to database',
        secret=True,
    )

    required_config.add_option(
        name='database_superusername',
        default='test',
        doc='Username to connect to database',
    )

    required_config.add_option(
        name='database_superuserpassword',
        default='aPassword',
        doc='Password to connect to database',
        secret=True,
    )

    required_config.add_option(
        name='database_port',
        default=5432,
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
        name='createdb',
        default=False,
        doc='Whether or not to create database_name',
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

    def create_connection_url(self, database_name, username, password):
        """ helper method to manage superuser and regular user db access """
        hostname = self.config.get('database_hostname')
        port = self.config.get('database_port')

        sa_url = 'postgresql://%s:%s@%s:%s/%s' % (
            username, password, hostname, port, database_name
        )

        return sa_url

    def main(self):

        connection_url = ''

        # If we've got a database_url, use that instead of separate args
        self.database_url = self.config.database_url
        self.database_name = self.config.database_name

        if self.database_url:
            connection_url = self.database_url
        else:
            if not self.database_name:
                print "Syntax error: --database_name required"
                return 1
            connection_url = self.create_connection_url(
                'postgres',
                self.config.get('database_superusername'),
                self.config.get('database_superuserpassword')
            )

        self.no_schema = self.config.no_schema
        self.on_heroku = self.config.on_heroku
        database_name = self.config.database_name
        database_username = self.config.database_username
        database_password = self.config.database_password

        if self.config.unlogged:
            @compiles(CreateTable)
            def create_table(element, compiler, **kw):
                text = compiler.visit_create_table(element, **kw)
                text = re.sub("^\sCREATE(.*TABLE)",
                              lambda m: "CREATE UNLOGGED %s" %
                              m.group(1), text)
                return text

        # Verify we've got the right version of Postgres
        with PostgreSQLAlchemyManager(connection_url, self.config.logger,
                                      autocommit=False) as db:
            if not db.min_ver_check(90200):
                print 'ERROR - unrecognized PostgreSQL version: %s' % \
                    db.version_string()
                print 'Only 9.2+ is supported at this time'
                return 1

        # We can only do the following if the DB is not Heroku
        # XXX Might add the heroku commands for resetting a DB here
        if self.config.dropdb and not self.on_heroku:
            with PostgreSQLAlchemyManager(connection_url, self.config.logger,
                                          autocommit=False) as db:
                if 'test' not in self.database_name and not self.config.force:
                    confirm = raw_input(
                        'drop database %s [y/N]: ' % self.database_name)
                    if not confirm == "y":
                        logging.warn('NOT dropping table')
                        return 2
                db.drop_database(self.database_name)

        if self.config.createdb:
            with PostgreSQLAlchemyManager(connection_url, self.config.logger,
                                          autocommit=False) as db:
                db.create_database(self.database_name)
                db.create_roles(self.config)

        # Reconnect to set up extensions and things requiring superuser privs
        if not self.database_url:
            connection_url = self.create_connection_url(
                database_name,
                self.config.get('database_superusername'),
                self.config.get('database_superuserpassword')
            )

        alembic_cfg = Config(self.config.alembic_config)
        alembic_cfg.set_main_option('sqlalchemy.url', connection_url)

        with PostgreSQLAlchemyManager(connection_url, self.config.logger,
                                      False, self.on_heroku) as db:
            db.setup_extensions()
            db.grant_public_schema_ownership(database_username)
            db.commit()

        if self.no_schema:
            return 0

        # Reconnect as a regular user to set up schema, types and procs
        if not self.database_url:
            connection_url = self.create_connection_url(
                database_name,
                database_username,
                database_password
            )

        with PostgreSQLAlchemyManager(connection_url, self.config.logger,
                                      False, self.on_heroku) as db:
            # Order matters below
            db.turn_function_body_checks_off()
            db.load_raw_sql('types')
            db.load_raw_sql('procs')
            # We need to commit to make a type visible for table creation
            db.commit()

            db.create_tables()
            db.load_raw_sql('views')
            db.commit()

            if not self.config.get('no_staticdata'):
                self.import_staticdata(db)
            if self.config.get('fakedata'):
                self.generate_fakedata(db, self.config.get('fakedata_days'))
            db.commit()
            command.stamp(alembic_cfg, "heads")
            db.session.close()

        # Reconnect to clean up permissions
        if not self.database_url:
            connection_url = self.create_connection_url(
                database_name,
                self.config.get('database_superusername'),
                self.config.get('database_superuserpassword')
            )

        with PostgreSQLAlchemyManager(connection_url, self.config.logger,
                                      False, self.on_heroku) as db:
            db.set_table_owner(database_username)
            db.set_default_owner(self.database_name, database_username)
            db.set_grants(self.config)  # config has user lists

        return 0

if __name__ == "__main__":
    sys.exit(main(SocorroDBApp))
