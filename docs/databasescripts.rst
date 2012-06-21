.. index:: database

.. _databasescripts-chapter:

Database Management Scripts
===========================

There are a number of python and shell scripts, in the /scripts/ directory and elsewhere,
which are used to manage socorro in a staging and development environment, as well as to
deploy upgrades.   These scripts are detailed below.

Upgrade Scripts
===============

These scripts are used on a weekly basis to upgrade the various socorro PostgreSQL database servers.

auto-upgrade.py
---------------

Location: /sql/upgrade/

Purpose: to "auto-upgrade" StageDB and Crash-Stats-Dev after each automatic refresh of the
data in each database.

Called By: auto-refresh cron job

::

	auto-upgrade.py [options]

	options:
  	-P DIRPATH, --path=DIRPATH  path to the upgrade directory
  		default: /data/socorro/application/sql/upgrade
  	-D DBNAME, --database=DBNAME  database to upgrade
  	    default: breakpad
  	-p DBPORT, --port=DBPORT  database port
  	    default: 5432
  	-H DBHOST, --host=DBHOST  database hostname
  	    default: localhost
  	-l LOGFILE, --log=LOGFILE logfile location for output
  	    default: socorro_upgrade.log in the current directory

  	auto-upgrade.py -P /data/socorro/application/sql/upgrade \
  		-l /var/log/upgrade/db_upgrade.log -D breakpad

auto-upgrade queries the socorro_db_version.current_version field in the database to
determine the current database version.  It then walks the path given, running
upgrade.sh from each numbered directory in sorted version order.  If it hits an error
in any upgrade, it stops.

Note: must be run as the "postgres" user, in its shell environment.

upgrade.sh
----------

Location: /sql/upgrade/#.#/

Called By: auto-upgrade script or manually by DBA

::

	upgrade.sh [dbname]

dbname parameter is optional. Defaults to "breakpad" if not supplied.

An upgrade.sh script exists in each numbered upgrade directory, and is used to upgrade
the database from one database version to another.  For example, 15.0/upgrade.sh will
upgrade the database from 14.0 to 15.0.

All upgrade scripts are designed to quit on the first error.  To run them against a database
on an alternate port, you must set the PGPORT environment variable.  They are designed to
be run by the database superuser and won't run otherwise.


MiniDB Scripts
==============

This directory contains scripts for extracting and loading a smaller copy of the socorro PostgreSQL database ... called a "MiniDB" ... from production data.  This MiniDB is used for testing and staging.

All of these scripts are peculiar to the Mozilla environment, and would need adaptation to run elsewhere.

ExtractMiniDB
-------------

Location: /scripts/staging

Purpose: create the raw data for a "mini" version of the breakpad database, containing only a few weeks of data.

::

	extractMiniDB.py --weeks 2 --database breakpad --file extractdb.tgz
	extractMiniDB.py -w 2 -d breakpad -f extractdb.tgz

weeks
	the number of weeks of data to extract.  Optional, defaults to 2.

database
	database to connect to.  optional, defaults to 'breakpad'

file
	tarball file to create.  optional, defaults to 'extractdb.tgz'

Notes: Produces a file called "extractdb.tgz" which must be loaded using LoadMiniDBonDev.py.  May take a couple hours to run.

LoadMiniDBonDev
---------------

Purpose: loads the file created by ExtractMiniDB.py onto DevDB.

::

	loadMiniDBonDev.py --file extractdb.tgz --database breakpad --postscript postsql.sh
	loadMiniDBonDev.py -f extractdb.tgz -d breakpad -P postsql.sh

file
	file to load from.   Defaults to exractdb.tgz in the current directory.

database
	database to load into.  Defaults to "breakpad".

postscript
	location of script to run after load.  contains database objects not automatically created by load.  Defaults to "/data/socorro/application/scripts/staging/postsql/postsql.sh"

Notes: the extractdb.tgz file will be uncompressed into the current directory, creating several GB of files.  If the script errors out, these files will need to be cleaned up manually; for convenience they are all named *.dump.  Can take several hours to complete.

loadprep.sh
-----------

Script to be run on StageDB in order to prep it for loading a new database copy buy kicking off all users and automation.  Must be run as root.

Shuts down pgbouncer and restarts PostgreSQL.

afterload.sh
------------

Script to be run after database is loaded on StageDB, which updates authentication and then restores Postgres to testing condition.  Must be run as root.

Restarts PostgreSQL and pgbouncer.

backupdatadir.sh
----------------

Creates a copy of /pgdata/9.0/data for backup so that it can be restored later for testing.  Intended for DevDB and StageDB.

postsql directory
-----------------

Contains several SQL scripts which create database objects which error out during load due to broken dependencies, particularly views based on matviews.  postsql.sh shell script calls these.  Intended to be called by loadMiniDBonDev.py.