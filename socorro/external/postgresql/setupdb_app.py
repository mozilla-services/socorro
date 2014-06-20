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

from socorro.app.generic_app import App, main
from socorro.external.postgresql import fakedata
from socorro.external.postgresql.models import *


class PostgreSQLAlchemyManager(object):
    # TODO refactor to take a real config object
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

    def setup(self):
        self.session.execute('SET check_function_bodies = false')
        self.commit()

    def drop_database(self, db_config):
        try:
            # work around for autocommit behavior
            self.session.execute('commit')
            self.session.execute('DROP DATABASE %s' % db_config.database_name)
        except exc.ProgrammingError, e:
            if re.match(
                'database "%s" does not exist' % db_config.database_name,
                e.orig.pgerror.strip()):
                # already done, no need to rerun
                print "The DB %s doesn't exist" % db_config.database_name

    def create_database(self, db_config):
        self.session.execute('commit')
        self.session.execute('CREATE DATABASE %s' % db_config.database_name)

    def set_encoding(self, db_config):
        try:
            # work around for autocommit behavior
            self.session.execute('commit')
            self.session.execute("CREATE DATABASE %s ENCODING 'utf8'" %
                               db_config.database_name)
        # TODO is this the correct exception??
        except ProgrammingError, e:
            if re.match(
                'database "%s" already exists' % self.database_name,
                e.orig.pgerror.strip()):
                # already done, no need to rerun
                print "The DB %s already exists" % self.database_name
                return 0
            raise

    def create_extensions(self):
        print "creating extensions"
        self.session.execute('CREATE EXTENSION IF NOT EXISTS citext')
        self.session.execute('CREATE EXTENSION IF NOT EXISTS hstore')
        # we only need to create the json extension for pg9.2.*
        if not self.min_ver_check('9.3.0'):
            self.session.execute(
                'CREATE EXTENSION IF NOT EXISTS json_enhancements')
        self.commit()

    #def setup_schemas(self):
        #self.session.execute('CREATE SCHEMA bixie')
        #self.session.execute('CREATE SCHEMA base')
        #self.session.execute('CREATE SCHEMA normalized')
        #self.session.execute(
            #'GRANT ALL ON SCHEMA bixie, base, normalized, public TO breakpad_rw')
        #self.commit()

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

    def create_tables(self, schema='all'):
        status = ''
        if schema == 'all':
            for schema in ['bixie', 'base', 'normalized']:
                self.session.execute('CREATE SCHEMA IF NOT EXISTS %s' % schema)
                self.commit()
            status = self.metadata.create_all()
        else:
            for t in self.metadata.sorted_tables:
                if t.schema == schema:
                    self.session.execute('CREATE SCHEMA IF NOT EXISTS %s' % schema)
                    self.commit()
                    t.create(self.engine)
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
        cursor.execute("SET search_path TO base,public")
        cursor.copy_from(data, table, columns=columns, sep=sep)
        connection.commit()

    def set_default_owner(self, database_name):
        self.session.execute("""
                ALTER DATABASE %s OWNER TO breakpad_rw
            """ % database_name)

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

    def set_grants(self, config, schema='public'):
        """
        Grant access to configurable roles to all database tables
        TODO add support for column-level permission setting

        Everything inherits from two base roles:
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
        query = "REVOKE all ON all TABLES IN SCHEMA %s FROM %%s" % schema
        self.session.execute(query % 'PUBLIC')

        # set GRANTS on tables in schema
        roles = []
        query = "GRANT ALL ON all TABLES IN SCHEMA %s TO breakpad_rw" % schema
        roles.append(query)

        # TODO make this grant appropriate for RO user
        query = "GRANT SELECT ON all TABLES IN SCHEMA %s TO breakpad_ro" % schema
        roles.append(query)

        # set GRANTS for ROLEs
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

        # Set GRANTs on sequences
        sequences = self.session.execute("""
                SELECT n.nspname || '.' || c.relname
                FROM pg_catalog.pg_class c
                LEFT JOIN pg_catalog.pg_namespace n on n.oid = c.relnamespace
                WHERE c.relkind IN ('S')
                AND n.nspname IN ('%s')
                AND pg_catalog.pg_table_is_visible(c.oid);
            """ % schema).fetchall()
        for s, in sequences:
            self.session.execute("GRANT ALL ON SEQUENCE %s TO %s" % (s, rw))
            self.session.execute("GRANT SELECT ON SEQUENCE %s TO %s" % (s, ro))

        # Set GRANTS on views
        views = self.session.execute("""
                SELECT viewname FROM pg_views WHERE schemaname = '%s'
            """ % schema).fetchall()
        for v, in views:
            self.session.execute("GRANT ALL ON TABLE %s TO %s" % (v, rw))
            self.session.execute("GRANT SELECT ON TABLE %s TO %s" % (v, ro))

        self.commit()

    def commit(self):
        self.session.commit()

    def version(self):
        result = self.session.execute("SELECT version()")
        version_info = result.fetchone()
        return version_info["version"]

    # the version number is the second substring
    def version_number(self):
        return self.version().split()[1]

    # Parse the version as a tuple since the PG version string is "simple"
    # If we need a more "feature complete" version parser, we can use
    # distutils.version:StrictVersion or pkg_resources:parse_version
    def min_ver_check(self, version_required):
        return (tuple(map(int, self.version_number().split("."))) >=
                tuple(map(int, version_required.split("."))))

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

    def setup_fdw(self, config):
        session = self.session
        session.execute("""
            CREATE EXTENSION postgres_fdw
        """)
        session.execute("""
            CREATE SERVER %s FOREIGN DATA WRAPPER postgres_fdw
            OPTIONS (host '%s', dbname '%s', port '%s')
        """ % (config.secondarydb.database_fdw_name,
               config.secondarydb.database_hostname,
               config.secondarydb.database_name,
               config.secondarydb.database_port))

        session.execute("""
            CREATE USER MAPPING FOR %s SERVER %s
            OPTIONS (user '%s', password '%s')
        """ % (config.secondarydb.database_username,
               config.secondarydb.database_fdw_name,
               config.secondarydb.database_username,
               config.secondarydb.database_password)
        )

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

    required_config.add_option(
        name='splitschema',
        default=False,
        doc='Split the schema into two databases'
    )

    # TODO make a transaction executor class that uses SQLAlchemy
    # to make this config a bit less verbose and more like our other
    # external database libraries
    required_config.namespace('primarydb')
    required_config.primarydb.add_option(
        name='database_name',
        default='socorro_integration_test',
        doc='Name of database to manage',
    )

    required_config.primarydb.add_option(
        name='database_hostname',
        default='localhost',
        doc='Hostname to connect to database',
    )

    required_config.primarydb.add_option(
        name='database_username',
        default='breakpad_rw',
        doc='Username to connect to database',
    )

    required_config.primarydb.add_option(
        name='database_password',
        default='aPassword',
        doc='Password to connect to database',
    )

    required_config.primarydb.add_option(
        name='database_superusername',
        default='test',
        doc='Username to connect to database',
    )

    required_config.primarydb.add_option(
        name='database_superuserpassword',
        default='aPassword',
        doc='Password to connect to database',
    )

    required_config.primarydb.add_option(
        name='database_port',
        default='',
        doc='Port to connect to database',
    )

    required_config.primarydb.add_option(
        name='database_fdw_name',
        default='sandbox1',
        doc='Foreign Data Wrapper server name',
    )

    required_config.primarydb.add_option(
        name='database_type',
        default='all',
        doc='Type of tables to deploy [all, base]',
    )

    required_config.namespace('secondarydb')
    required_config.secondarydb.add_option(
        name='second_database_name',
        default='socorro_integration_test',
        doc='Name of database to manage',
    )

    required_config.secondarydb.add_option(
        name='second_database_hostname',
        default='localhost',
        doc='Hostname to connect to database',
    )

    required_config.secondarydb.add_option(
        name='second_database_username',
        default='breakpad_rw',
        doc='Username to connect to database',
    )

    required_config.secondarydb.add_option(
        name='second_database_password',
        default='aPassword',
        doc='Password to connect to database',
    )

    required_config.secondarydb.add_option(
        name='second_database_superusername',
        default='test',
        doc='Username to connect to database',
    )

    required_config.secondarydb.add_option(
        name='second_database_superuserpassword',
        default='aPassword',
        doc='Password to connect to database',
    )

    required_config.secondarydb.add_option(
        name='second_database_port',
        default='5432',
        doc='Port to connect to database',
    )

    required_config.secondarydb.add_option(
        name='second_database_fdw_name',
        default='sandbox2',
        doc='Foreign Data Wrapper server name',
    )

    required_config.secondarydb.add_option(
        name='database_type',
        default='none',
        doc='Type of tables to deploy [none, reporting]',
    )

    @staticmethod
    def generate_fakedata(db, fakedata_days):

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

            io = cStringIO.StringIO()
            for line in table.generate_rows():
                io.write('\t'.join([str(x) for x in line]))
                io.write('\n')
            io.seek(0)
            db.bulk_load(io, table.table, table.columns, '\t')

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


    def init_db(self, sa_url, db_config):
        print sa_url
        with PostgreSQLAlchemyManager(sa_url, self.config.logger,
                                      autocommit=False) as db:
            db.setup()

            if not db.min_ver_check("9.2.0"):
                print 'ERROR - unrecognized PostgreSQL version: %s' % \
                    db.version()
                print 'Only 9.2+ is supported at this time'
                return 1

            if self.config.get('dropdb'):
                if 'test' not in db_config.database_name and not self.force:
                    confirm = raw_input(
                        'drop database %s [y/N]: ' % db_config.database_name)
                    if not confirm == "y":
                        logging.warn('NOT dropping database')
                        return 2
                    else:
                        db.drop_database(db_config)
                else:
                    db.drop_database(db_config)

            print "creating database"
            db.set_encoding(db_config)

            # Set up a nice environment for the database
            db.commit()
            db.create_roles(self.config)
            #db.setup_schemas()
            db.commit()

    def connection_url(self, db_config, usertype='nosuperuser'):
        url_template = 'postgresql://'

        if usertype == 'superuser':
            if db_config.database_superusername:
                url_template += '%s' % db_config.database_superusername
            if db_config.database_password:
                url_template += ':%s' % db_config.database_superuserpassword
        else:
            if db_config.database_username:
                url_template += '%s' % db_config.database_username
            if db_config.database_password:
                url_template += ':%s' % db_config.database_password

        url_template += '@'
        if db_config.database_hostname:
            url_template += '%s' % db_config.database_hostname
        if db_config.database_port:
            url_template += ':%s' % db_config.database_port
        return url_template

    def setup_global(self, db):
        db.create_types()
        db.create_procs()
        db.set_sequence_owner('breakpad_rw')
        db.commit()

    def setup_schemas_for(self, db, database_type):
        schemas = []
        if database_type == 'base':
            db.setup_fdw(self.config)
            schemas = ['base', 'normalized']
        elif database_type == 'reporting':
            schemas = ['public', 'bixie']
        else:
            schemas = ['base', 'public', 'bixie']

        for schema in schemas:
            db.create_tables(schema)

    def deploy_socorro(self, db_config):
        """ Set up schemas, tables, types and procs """
        url_template = self.connection_url(db_config, 'superuser')
        sa_url = url_template + '/%s' % db_config.database_name

        alembic_cfg = Config(self.config.alembic_config)
        alembic_cfg.set_main_option("sqlalchemy.url", sa_url)

        print sa_url
        with PostgreSQLAlchemyManager(sa_url, self.config.logger) as db:
            db.setup()
            db.create_extensions()

            if self.no_schema:
                db.commit()
                return 0

            self.setup_global(db)
            self.setup_schemas_for(db, db_config.database_type)
            db.commit()

            if db_config.database_type != 'base':
                #db.create_views()
                # TODO set up grants for base database
                for schema in ['public', 'base', 'bixie']:
                    db.set_grants(self.config, schema)  # config has user lists
                db.commit()

                # Needs to be modified to support split schema
                #if self.config['fakedata']:
                    #self.generate_fakedata(db, self.config['fakedata_days'])
                db.commit()

            # Same for all database types
            command.stamp(alembic_cfg, "head")
            db.set_default_owner(db_config.database_name)
            db.session.close()

    def main(self):

        if not self.config.primarydb.database_name:
            print "Syntax error: --primarydb.database_name required"
            return 1

        self.no_schema = self.config.get('no_schema')
        self.force = self.config.get('force')

        # Override CreateTable in SQLAlchemy for special cases
        # TODO: sort out conflict between unlogged and splitschema
        if self.config.unlogged:
            @compiles(CreateTable)
            def create_table(element, compiler, **kw):
                text = compiler.visit_create_table(element, **kw)
                text = re.sub("^\sCREATE(.*TABLE)",
                              lambda m: "CREATE UNLOGGED %s" %
                              m.group(1), text)
                return text

        # Figure out which sets of database configs we're going to work with
        db_configs = []
        if self.config.splitschema:
            # Change our create table routine
            @compiles(CreateTable)
            def create_table(element, compiler, **kw):
                text = compiler.visit_create_table(element, **kw)
                if 'normalized.' in text:
                    text = re.sub("^\sCREATE(.*TABLE)",
                                  lambda m: "CREATE FOREIGN %s" % m.group(1), text)
                    text += "SERVER %s" % self.config.second_database_fdw_name
                return text

            db_configs = [self.config.primarydb, self.config.secondarydb]
        else:
            # Not splitting the schema, so only need primarydb config
            db_configs = [self.config.primarydb]


        # Set up core database using superuser
        for db_config in db_configs:
            url_template = self.connection_url(db_config, 'superuser')
            sa_url = url_template + '/%s' % 'postgres'
            self.init_db(sa_url, db_config)
            self.deploy_socorro(db_config)

        # TODO Set up rest of schema

        return 0

if __name__ == "__main__":
    sys.exit(main(SocorroDB))
