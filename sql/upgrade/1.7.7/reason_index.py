#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import sys
import psycopg2, psycopg2.extensions

start_partition = sys.argv[1]
recent_partition = sys.argv[2]

print "Start partition: ", start_partition
print "Recent partition: ", recent_partition

conn = psycopg2.connect("dbname=breakpad user=postgres")

conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

cur = conn.cursor()

cur.execute("""
   SET work_mem = '128 MB'
""")

cur.execute("""
   SET maintenance_work_mem = '256 MB'
""")

cur.execute("""
   SET temp_buffers = '128 MB'
""")


cur.execute("""
   select relname from pg_stat_user_tables
      where relname like 'reports_20%%'
         and relname >= %s
      order by relname
   """, ( start_partition, ) )

partitions = [ x for ( x, ) in cur.fetchall() ]

for partition in partitions:
   index_name = "%s_reason" % partition

   cur.execute("select indisvalid from pg_index join pg_class on pg_class.oid = pg_index.indexrelid where pg_class.relname=%s",
      ( index_name, ) )

   valid_check = cur.fetchone()

   if valid_check is not None:
      ( is_valid, ) = valid_check
      if is_valid:
         continue
      else:
         print "%s exists but is invalid, dropping and recreating... " % index_name
         cur.execute("drop index %s" % index_name)
   else:
      print "%s does not exist, creating..." % index_name

   if partition >= recent_partition:
      cur.execute("CREATE INDEX CONCURRENTLY %s ON %s (reason)" % (index_name, partition, ) )
      print "%s created concurrently." % partition
   else:
      cur.execute("CREATE INDEX %s ON %s (reason)" % (index_name, partition, ))
      print "%s created." % partition
