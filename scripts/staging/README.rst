MiniDB Scripts
==============

This directory contains scripts for extracting and loading a smaller copy of the socorro PostgreSQL database ... called a "MiniDB" ... from production data.  This MiniDB is used for testing and staging.

All of these scripts are peculiar to the Mozilla environment, and would need adaptation to run elsewhere.

ExtractMiniDB
-------------

Purpose: create the raw data for a "mini" version of the breakpad database, containing only a few weeks of data.

::

	./extractMiniDB.py <numweeks>
	
<numweeks> the number of weeks of data to extract.  Optional, defaults to 2.

Notes: Produces a file called "extractdb.tgz" which must be loaded using LoadMiniDBonDev.py.  May take a couple hours to run.

LoadMiniDBonDev
---------------

Purpose: loads the file created by ExtractMiniDB.py onto DevDB.

::

	./loadMiniDBonDev.py <filename> <dbname> <postsqlscript>
	
<filename>: file to load from.   Defaults to exractdb.tgz in the current directory.
<dbname>: database to load into.  Defaults to "breakpad".
<postsqlscript>: location of script to run after load.  contains database objects not automatically created by load.  Defaults to /data/socorro/application/scripts/staging/postsql/postsql.sh

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

Contains several SQL scripts which create database objects which error out during load due to broken dependencies, particularly views based on matviews.  postdata.sh shell script calls these.  Intended to be called by loadMiniDB.py.

other scripts
-------------

The following scripts have been superceded by the above, and are now obsolete:

truncate56.py: cuts down some but not all tables in socorro to 56 days of data.  Delete-in-place on a running database, so do not run in production.

extractPartialDB.py: predecessor to extractMiniDB.py

loadExtractDB.py: predecessor to loadMiniDBonDev.py