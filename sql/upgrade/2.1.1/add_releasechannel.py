#!/usr/bin/python
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import sys
import time
import psycopg2, psycopg2.extensions, psycopg2.errorcodes

conn = psycopg2.connect("dbname=breakpad user=postgres")

cur = conn.cursor()

#try to exclusively lock the reports table.  This will take multiple attempts

lock_tries = 1

while lock_tries < 100:
   print "locking reports table, try %s of 100" % (lock_tries , )
   try:
      cur.execute("LOCK TABLE reports IN ACCESS EXCLUSIVE MODE NOWAIT;")
      break
   except Exception, e:
      if e.pgcode == psycopg2.errorcodes.LOCK_NOT_AVAILABLE:
         conn.rollback()
         lock_tries += 1
         time.sleep(3)
      else:
         raise e
else:
   sys.exit("unable to lock table reports")



cur.execute("""
   ALTER TABLE reports ADD COLUMN release_channel TEXT;
   """)

conn.commit()

print "column releasechannel added"
