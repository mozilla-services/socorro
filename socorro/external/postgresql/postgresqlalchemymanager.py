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
        self.session.execute(
            'GRANT ALL ON SCHEMA public TO breakpad_rw')

    def setup(self):
        self.session.execute('SET check_function_bodies = false')

    def create_types(self):
        types_dir = os.path.normpath(os.path.join(
            __file__,
            '..',
            'raw_sql/types',
            '*.sql'
        ))
        for myfile in sorted(glob(types_dir)):
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
        procs_dir = os.path.normpath(os.path.join(
            __file__,
            '..',
            'raw_sql/procs',
            '*.sql'
        ))
        for file in sorted(glob(procs_dir)):
            procedure = open(file).read()
            try:
                self.session.execute(procedure)
            except exc.SQLAlchemyError, e:
                print "Something went horribly wrong: %s" % e
                raise
        return True

    def create_views(self):
        views_dir = os.path.normpath(os.path.join(
            __file__,
            '..',
            'raw_sql/views',
            '*.sql'
        ))
        for file in sorted(glob(views_dir)):
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
                AND n.nspname IN ('public')
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
                AND n.nspname IN ('public')
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
                REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %s
            """ % "PUBLIC")

        # set GRANTS for roles based on configuration
        roles = []
        roles.append("""
                GRANT ALL ON ALL TABLES IN SCHEMA public
                TO breakpad_rw
            """)
        roles.append("""
                GRANT SELECT ON ALL TABLES IN SCHEMA public
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
                AND n.nspname IN ('public')
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
