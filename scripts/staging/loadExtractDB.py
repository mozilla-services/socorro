#!/usr/bin/env python
import sys, os
import psycopg2, psycopg2.extensions

# loads a file created with extract_partial_db.py
# does not currently handle creating users
# takes two arguments, the archive name holding the data
# and optionally the database name to restore

if len(sys.argv) < 2:
    tar_file = 'extractdb.tgz'
else:
    tar_file = sys.argv[1]

if len(sys.argv) > 2:
    database_name = sys.argv[2]
else:
    database_name = 'breakpad'

print "Loading data"

def runload(load_command, db_name):
    print load_command % db_name
    load_result = os.system(load_command % db_name)
    if load_result != 0:
        sys.exit(load_result)

# untar the file
runload('tar -xzf %s', tar_file)

#connect to postgresql
conn = psycopg2.connect("dbname=postgres user=postgres")

conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

cur = conn.cursor()

print 'drop and recreate the database'

# drop the database and recreate it
try:
    cur.execute("""DROP DATABASE %s;
       """ % database_name  )
except psycopg2.Error as exc:
    code = exc.pgcode
    if code == '3D000':
        pass
    else:
        # if this failed, check why.
        sys.exit('unable to drop database %s probably because connections to it are still open: %s' % database_name,code)

cur.execute("""CREATE DATABASE %s;
   """ % database_name )

print 'load users.  please ignore any errors you see here'

os.system('psql -q -v verbosity=terse -U postgres -f users.dump %s' % database_name)

print 'load most of the database'

runload('pg_restore -j 2 -Fc -U postgres -d %s extractdb.dump', database_name)

print 'load the truncated materialized views'

#load matview DDL
runload('pg_restore -Fc -U postgres -d %s matviews.dump', database_name)

# load raw_adu data
runload('psql -c "\copy raw_adu FROM raw_adu.dump" -U postgres %s', database_name )

# load tcbs data
runload('psql -c "\copy top_crashes_by_signature FROM tcbs.dump" -U postgres %s', database_name )

# load tcbu data
runload('psql -c "\copy top_crashes_by_url FROM tcbu.dump" -U postgres %s', database_name )

# load tcbu_s data
runload('psql -c "\copy top_crashes_by_url_signature FROM tcbu_s.dump" -U postgres %s', database_name )

#delete all the dump files

os.system('rm extractdb.dump matviews.dump raw_adu.dump tcbs.dump tcbu.dump tcbu_s.dump users.dump')

print 'done loading database.'


