#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Create, prepare and load schema for Socorro PostgreSQL database.
"""
from __future__ import unicode_literals

import cStringIO
import os
import re
import sys

from alembic import command
from alembic.config import Config
from configman import Namespace, class_converter
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.schema import CreateTable

from socorro.app.socorro_app import App, main
from socorro.external.postgresql import staticdata
from socorro.external.postgresql.connection_context import (
    get_field_from_pg_database_url
)
#from socorro.external.postgresql.models import *
from socorro.external.postgresql.postgresqlalchemymanager import (
    PostgreSQLAlchemyManager
)


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
        'database_class',
        default='socorro.external.postgresql.connection_context.ConnectionContext',
        doc='the class responsible for connecting to Postgres',
        reference_value_from='resource.postgresql',
        from_string_converter=class_converter
    )

    required_config.add_option(
        name='database_superusername',
        default=get_field_from_pg_database_url('username', 'test'),
        doc='Username to connect to database',
    )

    required_config.add_option(
        name='database_superuserpassword',
        default=get_field_from_pg_database_url('password', 'aPassword'),
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

    def create_connection_url(self, database_name, username, password):
        """Takes a URL to connect to Postgres and updates database name
            or superuser name/password as indicated
           from PG Docs:
           postgresql://[user[:password]@][netloc][:port][/dbname]"""

        hostname = self.config.get('database_hostname')
        port = self.config.get('database_port')

        # construct a URL
        url = 'postgresql://'
        if username:
            url += '%s' % username
            if password:
                url += ':%s' % password
            url += '@'
        if hostname:
            url += '%s' % hostname
        if port:
            url += ':%s' % port
        if database_name:
            url += '/%s' % database_name
        return url

    def handle_dropdb(self, superuser_pg_url, database_name):
        """Handles dropping the database

        If the database is not a test database, this will prompt the user to make sure the user is
        ok with dropping the database.

        :arg string superuser_pg_url: the postgres url for the superuser user
        :arg string database_name: the name of the database to drop

        :returns: True if everything is good, False if the user said "don't drop this"

        """
        self.config.logger.info('drop database section with %s', superuser_pg_url)
        with PostgreSQLAlchemyManager(
                superuser_pg_url,
                self.config.logger,
                autocommit=False
        ) as db:
            if 'test' not in database_name and not self.config.force:
                confirm = raw_input(
                    'drop database %s [y/N]: ' % database_name
                )
                if not confirm == "y":
                    self.config.logger.warning('NOT dropping table')
                    return False
            db.drop_database(database_name)
            db.commit()
        return True

    def handle_createdb(self, superuser_normaldb_pg_url, superuser_pg_url, normal_user_pg_url,
                        database_name):
        """Handles creating the database and populating it with critical stuff

        :arg string superuser_normaldb_pg_url: super creds for working db
        :arg string superuser_pg_url: superuser creds for overall db
        :arg string normal_user_pg_url: normal user creds
        :arg string database_name: the name of the database to create

        :returns: True if everything worked

        """
        self.config.logger.info('create database section with %s', superuser_pg_url)
        with PostgreSQLAlchemyManager(
            superuser_pg_url,
            self.config.logger,
            autocommit=False
        ) as db:
            db.create_database(database_name)
            if self.config.no_roles:
                self.config.logger.info("Skipping role creation")
            else:
                db.create_roles(self.config)
            db.commit()

        # database extensions section
        self.config.logger.info('database extensions section with %s', superuser_normaldb_pg_url)
        with PostgreSQLAlchemyManager(
            superuser_normaldb_pg_url,
            self.config.logger,
            autocommit=False
        ) as db:
            db.setup_extensions()
            db.grant_public_schema_ownership(self.config.database_username)
            db.commit()

        # database schema section
        if self.config.no_schema:
            self.config.logger.info("not adding a schema")
            return True

        alembic_cfg = Config(self.config.alembic_config)
        alembic_cfg.set_main_option('sqlalchemy.url', normal_user_pg_url)

        self.config.logger.info('database schema section with %s', normal_user_pg_url)
        with PostgreSQLAlchemyManager(
            normal_user_pg_url,
            self.config.logger,
            autocommit=False
        ) as db:
            # Order matters below
            db.turn_function_body_checks_off()
            db.load_raw_sql('types')
            db.load_raw_sql('procs')
            # We need to commit to make a type visible for table creation
            db.commit()

            db.create_tables()
            db.commit()

            if not self.config.get('no_staticdata'):
                self.import_staticdata(db)
            db.commit()
            command.stamp(alembic_cfg, "heads")
            db.session.close()

        # database owner section
        self.config.logger.info('database extensions section with %s', superuser_normaldb_pg_url)
        with PostgreSQLAlchemyManager(
            superuser_normaldb_pg_url,
            self.config.logger,
            autocommit=False
        ) as db:
            db.set_table_owner(self.config.database_username)
            db.set_default_owner(database_name, self.config.database_username)
            db.set_grants(self.config)  # config has user lists
        return True

    def main(self):
        database_name = self.config.database_name

        if not database_name:
            self.config.logger.error('"database_name" cannot be an empty string')
            return 1

        # superuser credentials for overall database
        superuser_pg_url = self.create_connection_url(
            'postgres',
            self.config.database_superusername,
            self.config.database_superuserpassword
        )

        # superuser credentials for working database
        superuser_normaldb_pg_url = self.create_connection_url(
            database_name,
            self.config.database_superusername,
            self.config.database_superuserpassword
        )

        # normal user credentials
        normal_user_pg_url = self.create_connection_url(
            database_name,
            self.config.database_username,
            self.config.database_password
        )

        # table logging section
        if self.config.unlogged:
            @compiles(CreateTable)
            def create_table(element, compiler, **kw):
                text = compiler.visit_create_table(element, **kw)
                text = re.sub("^\sCREATE(.*TABLE)",
                              lambda m: "CREATE UNLOGGED %s" %
                              m.group(1), text)
                return text

        # Postgres version check section
        self.config.logger.info('Postgres version check section with %s', superuser_pg_url)
        with PostgreSQLAlchemyManager(
            superuser_pg_url,
            self.config.logger,
            autocommit=False
        ) as db:
            if not db.min_ver_check(90200):
                self.config.logger.error(
                    'unrecognized PostgreSQL version: %s',
                    db.version_string()
                )
                self.config.logger.error('Only 9.2+ is supported at this time')
                return 1

        # At this point, we're done with setup and we can perform actions requested by the user

        if self.config.dropdb:
            # If this doesn't return True (aka everything worked fine), then return exit code 2
            if not self.handle_dropdb(superuser_pg_url, database_name):
                return 2

        if self.config.createdb:
            # If this doesn't return True (aka everything worked fine), then return exit code 1
            if not self.handle_createdb(
                superuser_normaldb_pg_url, superuser_pg_url, normal_user_pg_url, database_name
            ):
                return 1

        return 0


if __name__ == "__main__":
    sys.exit(main(SocorroDBApp))
