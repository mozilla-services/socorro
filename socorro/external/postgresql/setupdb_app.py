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
from configman import Namespace
from psycopg2 import ProgrammingError
from sqlalchemy import create_engine, exc
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable

from socorro.app.generic_app import App, main as configman_main
from socorro.external.postgresql import staticdata, fakedata
from socorro.external.postgresql.models import *


class PostgreSQLAlchemyManager(object):
    """
        Connection management for PostgreSQL using SQLAlchemy
    """
    def __init__(self, sa_url, logger, autocommit=False):
        self.engine = create_engine(sa_url,
                                    implicit_returning=False,
                                    isolation_level="READ COMMITTED")
        self.conn = self.engine.connect().execution_options(
            autocommit=autocommit)
        self.metadata = DeclarativeBase.metadata
        self.metadata.bind = self.engine
        self.session = sessionmaker(bind=self.engine)()
        self.logger = logger

    def setup_admin(self):
        self.session.execute('SET check_function_bodies = false')
        self.session.execute('CREATE EXTENSION IF NOT EXISTS citext')
        self.session.execute('CREATE EXTENSION IF NOT EXISTS hstore')
        # we only need to create the json extension for pg9.2.*
        if not self.min_ver_check(90300):
            self.session.execute(
                'CREATE EXTENSION IF NOT EXISTS json_enhancements')
        self.session.execute('CREATE SCHEMA bixie')
        self.session.execute(
            'GRANT ALL ON SCHEMA bixie, public TO breakpad_rw')

    def setup(self):
        self.session.execute('SET check_function_bodies = false')

    def create_types(self):
        # read files from 'raw_sql' directory
        app_path = os.getcwd()
        full_path = app_path + \
            '/socorro/external/postgresql/raw_sql/types/*.sql'
        for myfile in sorted(glob(full_path)):
            custom_type = open(myfile).read()
            try:
                self.session.execute(custom_type)
            except exc.SQLAlchemyError, e:
                print "Something went horribly wrong: %s" % e
                raise
        return True

    def create_tables(self):
        status = self.metadata.create_all()
        return status

    def create_procs(self):
        # read files from 'raw_sql' directory
        app_path = os.getcwd()
        full_path = app_path + \
            '/socorro/external/postgresql/raw_sql/procs/*.sql'
        for file in sorted(glob(full_path)):
            procedure = open(file).read()
            try:
                self.session.execute(procedure)
            except exc.SQLAlchemyError, e:
                print "Something went horribly wrong: %s" % e
                raise
        return True

    def create_views(self):
        app_path = os.getcwd()
        full_path = app_path + \
            '/socorro/external/postgresql/raw_sql/views/*.sql'
        for file in sorted(glob(full_path)):
            procedure = open(file).read()
            try:
                self.session.execute(procedure)
            except exc.SQLAlchemyError, e:
                print "Something went horribly wrong: %s" % e
                raise
        return True

    def bulk_load(self, data, table, columns, sep):
        connection = self.engine.raw_connection()
        cursor = connection.cursor()
        cursor.copy_from(data, table, columns=columns, sep=sep)
        connection.commit()

    def set_default_owner(self, database_name):
        self.session.execute("""
                ALTER DATABASE %s OWNER TO breakpad_rw
            """ % database_name)

    def set_table_owner(self, owner):
        for table in self.metadata.sorted_tables:
            self.session.execute("""
                    ALTER TABLE %s OWNER TO %s
                """ % (table, owner))

    def set_sequence_owner(self, owner):
        sequences = self.session.execute("""
                SELECT n.nspname || '.' || c.relname
                FROM pg_catalog.pg_class c
                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('S')
                AND n.nspname IN ('public', 'bixie')
                AND pg_catalog.pg_table_is_visible(c.oid);
            """).fetchall()

        for sequence, in sequences:
            self.session.execute("""
                    ALTER SEQUENCE %s OWNER TO %s
                """ % (sequence, owner))

    def set_type_owner(self, owner):
        types = self.session.execute("""
                SELECT
                  n.nspname || '.' || pg_catalog.format_type(t.oid, NULL)
                    AS "Name",
                FROM pg_catalog.pg_type t
                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = t.typnamespace
                WHERE (t.typrelid = 0 OR
                    (SELECT c.relkind = 'c' FROM pg_catalog.pg_class c
                    WHERE c.oid = t.typrelid))
                AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_type el
                    WHERE el.oid = t.typelem AND el.typarray = t.oid)
                AND n.nspname IN ('public', 'bixie')
                AND pg_catalog.pg_type_is_visible(t.oid)
            """).fetchall()

        for pgtype, in types:
            self.session.execute("""
                    ALTER TYPE %s OWNER to %s
                """ % (types, owner))

    def set_grants(self, config):
        """
        Grant access to configurable roles to all database tables
        TODO add support for column-level permission setting

        Everything is going to inherit from two base roles:
            breakpad_ro
            breakpad_rw

        Non-superuser users in either of these roles are configured with:
            config.read_write_users
            config.read_only_users

        Here's our production hierarchy of roles:

            breakpad
                breakpad_metrics
                breakpad_ro
                breakpad_rw
                    bootstrap
                    collector
                    processor
                    monitor
                        processor
                    reporter
            django

            monitoring -- superuser
                nagiosdaemon
                ganglia

            postgres -- superuser
        """

        # REVOKE everything to start
        self.session.execute("""
                REVOKE ALL ON ALL TABLES IN SCHEMA bixie, public FROM %s
            """ % "PUBLIC")

        # set GRANTS for roles based on configuration
        roles = []
        roles.append("""
                GRANT ALL ON ALL TABLES IN SCHEMA bixie, public
                TO breakpad_rw
            """)
        roles.append("""
                GRANT SELECT ON ALL TABLES IN SCHEMA bixie, public
                TO breakpad_ro
            """)

        for rw in config.read_write_users.split(','):
            roles.append("GRANT breakpad_rw TO %s" % rw)

        for ro in config.read_only_users.split(','):
            roles.append("GRANT breakpad_ro TO %s" % ro)

        errors = [
            'ERROR:  role "breakpad_rw" is a member of role "breakpad_rw"',
            'ERROR:  role "breakpad_ro" is a member of role "breakpad_ro"',
            'ERROR:  role "breakpad_ro" is a member of role "breakpad"'
        ]

        for r in roles:
            try:
                self.session.begin_nested()
                self.session.execute(r)
                self.session.commit()
            except exc.DatabaseError, e:
                if e.orig.pgerror.strip() in errors:
                    self.session.rollback()
                    continue
                else:
                    raise

        # Now, perform the GRANTs for configured roles
        ro = 'breakpad_ro'
        rw = 'breakpad_rw'

        # Grants to tables
        for t in self.metadata.sorted_tables:
            self.session.execute("GRANT ALL ON TABLE %s TO %s" % (t, rw))
            self.session.execute("GRANT SELECT ON TABLE %s TO %s" % (t, ro))

        # Grants to sequences
        sequences = self.session.execute("""
                SELECT n.nspname || '.' || c.relname
                FROM pg_catalog.pg_class c
                LEFT JOIN pg_catalog.pg_namespace n on n.oid = c.relnamespace
                WHERE c.relkind IN ('S')
                AND n.nspname IN ('public', 'bixie')
                AND pg_catalog.pg_table_is_visible(c.oid);
            """).fetchall()

        for s, in sequences:
            self.session.execute("GRANT ALL ON SEQUENCE %s TO %s" % (s, rw))
            self.session.execute("GRANT SELECT ON SEQUENCE %s TO %s" % (s, ro))

        # Grants to views
        views = self.session.execute("""
                SELECT viewname FROM pg_views WHERE schemaname = 'public'
            """).fetchall()
        for v, in views:
            self.session.execute("GRANT ALL ON TABLE %s TO %s" % (v, rw))
            self.session.execute("GRANT SELECT ON TABLE %s TO %s" % (v, ro))

        self.session.commit()

    def commit(self):
        self.session.commit()

    # get the postgres version as a sortable integer
    def version_number(self):
        result = self.session.execute("SELECT setting::INT as version FROM pg_settings WHERE name = 'server_version_num'")
        version_info = result.fetchone()
        return version_info["version"]

    # get the version as a user-readable string
    def version_string(self):
        result = self.session.execute("SELECT setting FROM pg_settings WHERE name = 'server_version'")
        version_info = result.fetchone()
        return version_info["setting"]

    # compare the actual server version number to a required server version number
    # version required should be an integer, in the format 90300 for 9.3
    def min_ver_check(self, version_required):
        return self.version_number() >= version_required

    def create_roles(self, config):
        """
            This function creates two roles: breakpad_ro, breakpad_rw

            Then it creates roles defined in the config:
                config.read_write_users
                config.read_only_users

            Which all inherit from the two base roles.
        """
        roles = []
        roles.append("""
            CREATE ROLE breakpad_ro WITH NOSUPERUSER
                INHERIT NOCREATEROLE NOCREATEDB LOGIN
        """)
        roles.append("""
            CREATE ROLE breakpad_rw WITH NOSUPERUSER
                INHERIT NOCREATEROLE NOCREATEDB LOGIN
        """)

        # Now create everything that inherits from those
        for rw in config.read_write_users.split(','):
            roles.append("CREATE ROLE %s IN ROLE breakpad_rw" % rw)
            # Set default password per old roles.sql
            roles.append("ALTER ROLE %s WITH PASSWORD '%s'" %
                         (rw, config.default_password))

        for ro in config.read_only_users.split(','):
            roles.append("CREATE ROLE %s IN ROLE breakpad_ro" % ro)
            # Set default password per old roles.sql
            roles.append("ALTER ROLE %s WITH PASSWORD '%s'" %
                         (rw, config.default_password))

        for r in roles:
            try:
                self.session.begin_nested()
                self.session.execute(r)
                self.session.commit()
            except exc.ProgrammingError, e:
                if 'already exists' not in e.orig.pgerror.strip():
                    raise
                self.session.rollback()
                continue
            except exc.DatabaseError, e:
                raise

        # Need to close the outer transaction
        self.session.commit()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.conn.close()


###########################################
##  Database creation object
###########################################
class SocorroDB(App):
    """
    SocorroDB
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
            'logging.stderr_error_logging_level': 50
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

    def main(self):

        self.database_name = self.config['database_name']
        if not self.database_name:
            print "Syntax error: --database_name required"
            return 1

        self.no_schema = self.config.get('no_schema')

        self.force = self.config.get('force')

        def connection_url():
            url_template = 'postgresql://'
            if self.database_username:
                url_template += '%s' % self.database_username
            if self.database_password:
                url_template += ':%s' % self.database_password
            url_template += '@'
            if self.database_hostname:
                url_template += '%s' % self.database_hostname
            if self.database_port:
                url_template += ':%s' % self.database_port
            return url_template

        self.database_username = self.config.get('database_superusername')
        self.database_password = self.config.get('database_superuserpassword')
        self.database_hostname = self.config.get('database_hostname')
        self.database_port = self.config.get('database_port')

        url_template = connection_url()
        sa_url = url_template + '/%s' % 'postgres'

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

            db.create_roles(self.config)
            connection.close()

        # Reconnect to set up bixie schema, types and procs
        sa_url = url_template + '/%s' % self.database_name
        alembic_cfg = Config(self.config.alembic_config)
        alembic_cfg.set_main_option("sqlalchemy.url", sa_url)
        with PostgreSQLAlchemyManager(sa_url, self.config.logger) as db:
            connection = db.engine.connect()
            db.setup_admin()
            if self.no_schema:
                db.commit()
                return 0
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
            command.stamp(alembic_cfg, "head")
            db.set_default_owner(self.database_name)
            db.session.close()

        return 0

def main():
    return configman_main(SocorroDB)

if __name__ == "__main__":
    sys.exit(main())
