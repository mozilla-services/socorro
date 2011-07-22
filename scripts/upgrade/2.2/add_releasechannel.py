#!/usr/bin/python

import sys
import time
import psycopg2, psycopg2.extensions, psycopg2.errorcodes

conn = psycopg2.connect("dbname=breakpad user=postgres")

cur = conn.cursor()

#try to exclusively lock the reports table.  This will take multiple attempts

lock_tries = 1

while lock_tries < 100:
   print "locking reports table, try %s of 100",lock_tries
   try:
      cur.execute("LOCK TABLE reports IN ACCESS EXCLUSIVE MODE;")
      break
   except Exception, e:
      pgerr = errorcodes.lookup(e.pgcode)
      if pgerr == "LOCK_NOT_AVAILABLE":
         conn.rollback()
         lock_tries += 1
         time.sleep(3)
      else:
         sys.exit("unexpected postgresql error encountered: %s",pgerr)
else:
   sys.exit("unable to lock table reports")
         
         
cur.execute("""                                                                                                                                                                    
   ALTER TABLE reports ADD COLUMN releasechannel TEXT;                                                                                                                                              
   """)

conn.commit()

print "column releasechannel added"