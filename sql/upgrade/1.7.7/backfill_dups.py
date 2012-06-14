#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import sys
import psycopg2, psycopg2.extensions
import time, datetime

start_timestamp = datetime.datetime.fromtimestamp(time.mktime(time.strptime(sys.argv[1], '%Y-%m-%d %H:%M:%S')))
end_timestamp = datetime.datetime.now() - datetime.timedelta(hours=2)

print "Starting timestamp: %s" % str(start_timestamp)
print "Ending timestamp: %s" % str(end_timestamp)

conn = psycopg2.connect("dbname=breakpad user=postgres")

conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

cur = conn.cursor()

cur.execute("""
   SET work_mem = '128 MB'                                                                                                                                                             """)

cur.execute("""
   SET maintenance_work_mem = '256 MB'
   """)

cur.execute("""
   SET temp_buffers = '128 MB'
   """)


cur.execute("""
   create temporary table new_reports_duplicates (
      uuid text, duplicate_of text, date_processed timestamp )
   """)

current_timestamp = start_timestamp

while current_timestamp <= end_timestamp:
   cur.execute("""
      select backfill_reports_duplicates(%s, %s)
      """, (current_timestamp - datetime.timedelta(hours=1), current_timestamp, ))
   ( duplicates, ) = cur.fetchone()

   print "%s duplicates found for %s " % ( duplicates, current_timestamp, )
   current_timestamp += datetime.timedelta(minutes=30)
