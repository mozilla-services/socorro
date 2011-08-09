#!/usr/bin/python

import sys
import os, os.path
import re
import psycopg2, psycopg2.extensions, psycopg2.errorcodes

conn = psycopg2.connect("dbname=breakpad user=postgres")

cur = conn.cursor()

# create the table

cur.execute("DROP TABLE IF EXISTS backfill_temp");
cur.execute("DROP TABLE IF EXISTS releasechannel_backfill");
cur.execute("CREATE TABLE backfill_temp ( uuid text, release_channel citext, blank text)");

# walk the files downloaded from hbase and copy them all in

# walk the files and copy them all in                                                                                                                      

dir = '/tmp'

for root, dirs, files in os.walk(dir):
    for f in files:
        fullpath = os.path.join(root, f)
        if re.search('output\.201106.*/part-r-\d+',fullpath):
            try:
                cur.execute( '''COPY backfill_temp FROM %s;''', (fullpath, ) )
                print '%s loaded' % ( fullpath, )
                conn.commit()
            except Exception, e:
                print 'ERROR: failed to load %s' % fullpath
                conn.rollback()

            
# create cleaned table and create index

print 'Cleaning data and creating indexes'
cur.execute('''CREATE TABLE releasechannel_backfill AS
	SELECT substr(uuid,8,100), release_channel
	FROM backfill_temp;''')
cur.execute("SET work_mem = '512MB'")
cur.execute("SET maintenance_work_mem = '512MB'")
cur.execute("ANALYZE releasechannel_backfill;")
cur.execute("CREATE INDEX releasechannel_backfill_uuid ON releasechannel_backfill(uuid);");

conn.commit();
            
# update the reports tables, one at a time

cur.execute("""
   select relname from pg_stat_user_tables
      where relname like 'reports_20%%'
         and relname >= 'reports_20110701'
      order by relname
   """ )

partitions = [ x for ( x, ) in cur.fetchall() ]

for partition in partitions:

   upquery = "UPDATE %s SET release_channel = backfill.release_channel FROM releasechannel_backfill as backfill WHERE %s.uuid = backfill.uuid" % ( partition, partition )
   cur.execute( upquery )
   conn.commit()
   
   print "%s updated" % partition
   



            


