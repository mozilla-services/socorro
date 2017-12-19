#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

"""
Create, prepare and load schema for Socorro PostgreSQL database.
"""
from __future__ import unicode_literals

import os
import re
from glob import glob

from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker

from socorro.external.postgresql.models import DeclarativeBase


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

    def setup_extensions(self):
        self.logger.debug('creating extensions')
        self.session.execute('CREATE EXTENSION IF NOT EXISTS citext')
        self.session.execute('CREATE EXTENSION IF NOT EXISTS hstore')
        # we only need to create the json extension for pg9.2.*
        if not self.min_ver_check(90300):
            self.session.execute(
                'CREATE EXTENSION IF NOT EXISTS json_enhancements')

    def grant_public_schema_ownership(self, username):
        self.logger.debug('granting ownership of public schema')
        self.session.execute(
            'GRANT ALL ON SCHEMA public TO %s' % username)

    def turn_function_body_checks_off(self):
        self.logger.debug('setting body checks off')
        self.session.execute('SET check_function_bodies = false')

    def load_raw_sql(self, directory):
        self.logger.debug('trying to load raw sql with dir %s' % directory)
        sqlfile_path = os.path.normpath(os.path.join(
            __file__,
            '..',
            'raw_sql',
            directory,
            '*.sql'
        ))
        for myfile in sorted(glob(sqlfile_path)):
            self.logger.debug('trying to load file %s' % myfile)
            raw_sql = open(myfile).read()
            try:
                self.session.execute(raw_sql)
            except exc.SQLAlchemyError as e:
                self.logger.error("Something went horribly wrong: %s" % e)
                raise
        return True

    def create_tables(self):
        self.logger.debug('creating all tables')
        status = self.metadata.create_all()
        return status

    def bulk_load(self, data, table, columns, sep):
        self.logger.debug('bulk loading data into %s', table)
        connection = self.engine.raw_connection()
        with connection.cursor() as cursor:
            cursor.copy_from(data, table, columns=columns, sep=sep)
        connection.commit()

    def set_default_owner(self, database_name, username):
        self.logger.debug('setting database %s owner to %s' % (
            database_name, username
        ))
        self.session.execute("""
                ALTER DATABASE %s OWNER TO %s
            """ % (database_name, username))

    def set_table_owner(self, owner):
        self.logger.debug('setting all tables owner to %s' % (owner))
        for table in self.metadata.sorted_tables:
            self.session.execute("""
                    ALTER TABLE %s OWNER TO %s
                """ % (table, owner))

    def set_sequence_owner(self, owner):
        self.logger.debug('setting all sequences owner to %s' % (owner))
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
        self.logger.debug('setting all types owner to %s' % (owner))
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

        Our production hierarchy of roles:

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

        self.logger.debug('revoking all grants')
        # REVOKE everything to start
        self.session.execute("""
                REVOKE ALL ON ALL TABLES IN SCHEMA public FROM %s
            """ % "PUBLIC")

        self.logger.debug('granting ALL to configured roles')
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
            except exc.DatabaseError as e:
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

        self.session.commit()

    def commit(self):
        self.session.commit()

    # get the postgres version as a sortable integer
    def version_number(self):
        result = self.session.execute("""
            SELECT setting::INT as version FROM pg_settings
            WHERE name = 'server_version_num'
        """)
        version_info = result.fetchone()
        return version_info["version"]

    # get the version as a user-readable string
    def version_string(self):
        result = self.session.execute("""
            SELECT setting FROM pg_settings WHERE name = 'server_version'
        """)
        version_info = result.fetchone()
        return version_info["setting"]

    # compare the server version number to a required server version number
    # version required should be an integer, eg: 90300 for 9.3
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
        self.logger.debug('creating roles from config')
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
            except exc.ProgrammingError as e:
                if 'already exists' not in e.orig.pgerror.strip():
                    raise
                self.session.rollback()
                continue
            except exc.DatabaseError as e:
                raise

        # Need to close the outer transaction
        self.session.commit()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.conn.close()

    def drop_database(self, database_name):
        self.logger.debug('dropping database %s' % database_name)
        connection = self.engine.connect()
        try:
            # work around for autocommit behavior
            connection.execute('commit')
            connection.execute('DROP DATABASE %s' % database_name)
        except (exc.OperationalError, exc.ProgrammingError) as e:
            if re.search(
                'database "%s" does not exist' % database_name,
                e.orig.pgerror.strip()
            ):
                # already done, no need to rerun
                self.logger.warning("The DB %s doesn't exist" % database_name)

    def create_database(self, database_name):
        self.logger.debug('creating database %s' % database_name)
        connection = self.engine.connect()
        try:
            # work around for autocommit behavior
            connection.execute('commit')
            connection.execute("CREATE DATABASE %s ENCODING 'utf8'" %
                               database_name)
        except (exc.OperationalError, exc.ProgrammingError) as e:
            if re.search(
                'database "%s" already exists' % database_name,
                e.orig.pgerror.strip()
            ):
                # already done, no need to rerun
                self.logger.warning("The DB %s already exists" % database_name)
                return 0
            raise
