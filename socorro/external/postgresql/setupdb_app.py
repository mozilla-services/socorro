#! /usr/bin/env python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# TODO:
# https://etherpad.mozilla.org/DGZ5GELhRI

"""
Create, prepare and load schema for Socorro PostgreSQL database.
"""
from __future__ import unicode_literals

import sys
from glob import glob
import os
import psycopg2
import psycopg2.extensions
from psycopg2 import ProgrammingError
import re
import logging

from socorro.app.generic_app import App, main
from configman import Namespace

from models import *
from sqlalchemy import exc

###########################################
## Connection management
###########################################

class PostgreSQLManager(object):
    def __init__(self, dsn, config):
        self.conn = psycopg2.connect(dsn)
        self.conn.set_isolation_level(
            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        self.config = config
        self.logger = config.logger

    def execute(self, sql, allowable_errors=None):
        cur = self.conn.cursor()
        try:
            cur.execute(sql)
        except ProgrammingError, e:
            if not allowable_errors:
                raise
            dberr = e.pgerror.strip().split('ERROR:  ')[1]
            for err in allowable_errors:
                if re.match(err, dberr):
                    self.logger.warning(dberr)
                else:
                    raise

    def version(self):
        cur = self.conn.cursor()
        cur.execute("SELECT version()")
        version_info = cur.fetchall()[0][0].split()
        return version_info[1]

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.conn.close()

class PostgreSQLAlchemyManager(object):
    def __init__(self, sa_url, config):
        self.engine = create_engine(sa_url, implicit_returning=False, isolation_level="READ COMMITTED")
        self.conn = self.engine.connect()
        self.metadata = DeclarativeBase.metadata
        self.metadata.bind = self.engine
        self.session = sessionmaker(bind=self.engine)()
        self.config = config
        self.logger = config.logger

    def setup(self):
        self.session.execute('SET check_function_bodies = false')
        self.session.execute('CREATE EXTENSION IF NOT EXISTS citext')

    def create_types(self):
        # read files from 'raw_sql' directory
        app_path=os.getcwd()
        for myfile in sorted(glob(app_path + '/socorro/external/postgresql/raw_sql/types/*.sql')):
            custom_type = open(myfile).read()
            try:
                self.session.execute(custom_type)
        #        rows = self.session.execute("select * from pg_type where typname ~ 'release_enum' or typname ~ 'product_info_change' or typname ~ 'flash_process_dump_type'")
        #        for row in rows:
        #            print row
            except exc.SQLAlchemyError, e:
                print "Something went horribly wrong: %s" % e
                raise
        return True

    def create_tables(self):
        status = self.metadata.create_all()
        return status

    def create_procs(self):
        # read files from 'raw_sql' directory
        app_path=os.getcwd()
        for file in sorted(glob(app_path + '/socorro/external/postgresql/raw_sql/procs/*.sql')):
            procedure = open(file).read()
            try:
                self.session.execute(procedure)
            except exc.SQLAlchemyError, e:
                print "Something went horribly wrong: %s" % e
                raise
        return True

    def create_views(self):
        app_path=os.getcwd()
        for file in sorted(glob(app_path + '/socorro/external/postgresql/raw_sql/views/*.sql')):
            procedure = open(file).read()
            try:
                self.session.execute(procedure)
            except exc.SQLAlchemyError, e:
                print "Something went horribly wrong: %s" % e
                raise
        return True

    def create_roles(self, sql, allowable_errors=None):
        roles = []
        for ro in config.read_only_users:
            roles.append( """DO
$body$
BEGIN
   IF NOT EXISTS (
      SELECT *
      FROM   pg_catalog.pg_user
      WHERE  usename = '%s') THEN

      CREATE ROLE %s LOGIN PASSWORD '%p';
   END IF;
END
$body$ """)
        for rw in config.read_write_users:
            roles.append("GRANT SELECT ON TABLE %s TO %s" % (t, rw))

    def set_default_owner(self, database_name, database_user):
        ## TODO figure out how to specify the database owner in the configs
        self.session.execute('ALTER DATABASE %s OWNER TO %s' % (database_name, database_user))

    def set_roles(self, config):

        revoke = []
        # REVOKE everything to start
        for t in self.metadata.sorted_tables:
            revoke.append( "REVOKE ALL ON TABLE %s FROM %s" % (t, "PUBLIC"))
            for rw in config.read_write_users:
                revoke.append( "REVOKE ALL ON TABLE %s FROM %s" % (t, rw))

        for r in revoke:
            self.engine.execute(r)

        grant = []

        # set GRANTS for roles based on configuration
        for t in self.metadata.sorted_tables:
            for ro in config.read_only_users:
                grant.append( "GRANT ALL ON TABLE %s TO %s" % (t, ro))
            for rw in config.read_write_users:
                grant.append("GRANT SELECT ON TABLE %s TO %s" % (t, rw))

        # TODO add support for column-level permission setting

        views = self.session.execute("select viewname from pg_views where schemaname = 'public'").fetchall()
        for v, in views:
            for ro in config.read_only_users:
                grant.append( "GRANT ALL ON TABLE %s TO %s" % (v, ro))
            for rw in config.read_write_users:
                grant.append("GRANT SELECT ON TABLE %s TO %s" % (v, rw))

        for g in revoke:
            self.engine.execute(g)

    def execute(self, sql, allowable_errors=None):
        pass

    def version(self):
        pass

    def commit(self):
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
    required_config.namespace('database')

    required_config.add_option(
        name='database_name',
        default='',
        doc='Name of database to manage',
    )

    required_config.add_option(
        name='database_host',
        default='',
        doc='Hostname to connect to database',
    )

    required_config.add_option(
        name='database_user',
        default='breakpad_rw',
        doc='Username to connect to database',
    )

    required_config.add_option(
        name='database_owner',
        default='',
        doc='Name of database owner',
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
        name='force',
        default=False,
        doc='Whether or not to override safety checks',
        exclude_from_print_conf=True,
        exclude_from_dump_conf=True
    )

    required_config.add_option(
        name='citext',
        default='/usr/share/postgresql/9.0/contrib/citext.sql',
        doc='Name of citext.sql file',
    )

    required_config.add_option(
        name='read_write_users',
        default=['postgres', 'breakpad_rw', 'monitor'],
        doc='Name of database to manage',
    )

    required_config.add_option(
        name='read_only_users',
        default=['breakpad_ro', 'breakpad', 'analyst'],
        doc='Name of database to manage',
    )


    def main(self):

        if not self.config.database_name:
            print "Syntax error: --database_name required"
            return 1

        self.no_schema = self.config.get('no_schema')
        self.citext = self.config.get('citext')

        self.force = self.config.get('force')

        dsn_template = 'dbname=%s'
        url_template = 'postgresql://'

        self.database_username = self.config.get('database_user')
        if self.database_username:
            dsn_template += ' user=%s' % self.database_username
            url_template += '%s' % self.database_username
        self.database_password = self.config.get('database_password')
        if self.database_password:
            dsn_template += ' password=%s' % self.database_password
            url_template += ':%s' % self.database_password
        self.database_hostname = self.config.get('database_host')
        if self.database_hostname:
            dsn_template += ' host=%s' % self.database_hostname
            url_template += '@%s' % self.database_hostname
        self.database_port = self.config.get('database_port')
        if self.database_port:
            dsn_template += ' port=%s' % self.database_port
            url_template += ':%s' % self.database_port

        dsn = dsn_template % 'template1'

        # Using the old connection manager style
        with PostgreSQLManager(dsn, self.config) as db:
            db_version = db.version()
            if not re.match(r'9\.[2][.*]', db_version):
                print 'ERROR - unrecognized PostgreSQL version: %s' % db_version
                print 'Only 9.2 is supported at this time'
                return 1
            if self.config.get('dropdb'):
                if 'test' not in self.config.database_name and not self.force:
                    confirm = raw_input(
                        'drop database %s [y/N]: ' % self.config.database_name)
                    if not confirm == "y":
                        logging.warn('NOT dropping table')
                        return 2

                db.execute('DROP DATABASE %s' % self.config.database_name,
                    ['database "%s" does not exist' % self.config.database_name])
                db.execute('DROP SCHEMA pgx_diag',
                           ['schema "pgx_diag" does not exist'])

            try:
                db.execute('CREATE DATABASE %s' % self.config.database_name)
            except ProgrammingError, e:
                if re.match(
                       'database "%s" already exists' % self.config.database_name,
                       e.pgerror.strip().split('ERROR:  ')[1]):
                    # already done, no need to rerun
                    print "The DB %s already exists" % self.config.database_name
                    return 0
                raise
            db.execute('CREATE EXTENSION IF NOT EXISTS citext')

        #dsn = dsn_template % self.config.database_name
        sa_url = url_template + '/%s' % self.config.database_name

        # Connect with SQL Alchemy and our new models
        with PostgreSQLAlchemyManager(sa_url, self.config) as db2:
            db2.setup()
            db2.create_types()
            db2.commit()
            db2.create_procs()
            db2.create_tables()
            db2.create_views()
            db2.set_roles(self.config) # config has user lists
            # Basically, if this user is defined, set this, otherwise leave it alone
            if self.config.database_user:
                db2.set_default_owner(self.config.database_name, self.config.database_user)
            db2.commit()

        return 0


if __name__ == "__main__":
    sys.exit(main(SocorroDB))
