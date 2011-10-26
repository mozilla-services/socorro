#!/usr/bin/python

import sys
import os
import psycopg2
import psycopg2.extensions

# loads a file created with extractminidb.py

# intended only for use on DevDB, as it uses an experimental
# version of PostgreSQL's pg_restore which is installed there
# if you need a minidb on another server, restore this on devdb
# and then dump from there

# creates users without changing passwords
# takes two arguments, the archive name holding the data
# and optionally the database name to restore

# note that this script will fail unless you first kick
# all users off the database system.  on stagedb, try
# running kick_off_users.sh as root first

if len(sys.argv) < 2:
    tar_file = 'extractdb.tgz'
else:
    tar_file = sys.argv[1]

if len(sys.argv) > 2:
    database_name = sys.argv[2]
else:
    database_name = 'breakpad'

print "Loading data"

def runload(load_command):
    load_result = os.system(load_command)
    if load_result != 0:
        sys.exit(load_result)
        
matviews = ['raw_adu', 'releases_raw', 'product_adu', 'daily_crashes',
            'top_crashes_by_signature', 'top_crashes_by_url', 'top_crashes_by_url_signature',
            'tcbs']

# untar the file
runload('tar -xzf %s' % tar_file)

#connect to postgresql
conn = psycopg2.connect("dbname=postgres user=postgres")

conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

cur = conn.cursor()

print 'drop and recreate the database'

# drop the database and recreate it
try:
    cur.execute("""DROP DATABASE %s;""" % database_name  )
except psycopg2.Error as exc:
    code = exc.pgcode
    if code == '3D000':
        pass
    else:
        # if this failed, check why.
        sys.exit('unable to drop database %s probably because connections to it are still open: %s' % (database_name, code, ) )

cur.execute("""CREATE DATABASE %s""" % database_name )

print 'load users.  please ignore any errors you see here'

os.system('psql -q -v verbosity=terse -U postgres -f users.dump %s' % database_name)

print 'load most of the database'

# dump a list of objects

# load everything else but not indexes and constraints
# needs to ignore errors

os.system('/usr/local/pgsql/bin/pg_restore -j 3 -Fc --no-post-data -U postgres minidb.dump -d %s' % database_name)

print 'load the truncated materialized views'

# restore the matview schema
# needs to ignore errors

os.system('/usr/local/pgsql/bin/pg_restore -Fc --no-post-data -U postgres matview_schemas.dump -d %s' % database_name)

# restore matview data, one matview at a time

for matview in matviews:
    print "loading %s" % matview
    runload("""psql -c "\copy %s FROM %s.dump" -U postgres %s""" % ( matview, matview, database_name, ) )

# restore indexes and constraints

print 'restore indexes and constraints'

runload('/usr/local/pgsql/bin/pg_restore -j 3 -Fc --post-data-only -U postgres minidb.dump -d %s' % database_name)
runload('/usr/local/pgsql/bin/pg_restore -j 3 -Fc --post-data-only -U postgres matview_schemas.dump -d %s' % database_name)

# truncate soon-to-be-dropped tables
conn.disconnect();

conn = psycopg2.connect("dbname=%s user=postgres" % database_name)

conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

cur = conn.cursor()

cur.execute('TRUNCATE tcbs_ranking')

cur.execute("""
            DO $f$
            DECLARE tab TEXT;
            BEGIN
                FOR tab IN SELECT relname
                    FROM pg_stat_user_tables
                    WHERE relname LIKE 'frames%' LOOP
                    
                    EXECUTE 'TRUNCATE ' || tab;
                    
                END LOOP;
            END; $f$;
        """)
                

#delete all the dump files

runload('rm *.dump')

# analyze

cur.execute('ANALYZE')

print 'done loading database.'


