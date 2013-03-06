import psycopg2
import os, sys
import csv

search = "extensions_201"
connectionstring = "user=postgres dbname=breakpad host=127.0.0.1"

conn = psycopg2.connect(connectionstring)
cur = conn.cursor()

cur.execute("select relname from pg_class where relkind = 'r' and relname ~ '^%s'" % search)
tables = cur.fetchall()

for relname, in tables:
    print "Altering %s" % relname
    cur.execute("ALTER TABLE %s ADD COLUMN uuid TEXT" % relname)

cur.execute("ALTER TABLE extensions ADD COLUMN uuid TEXT")

conn.commit()

#print "The next part is going to take a while."
#for relname, in tables:
    #parts = relname.split('_')
    #print "Adding uuids to %s" % relname
    #cur.execute("update extensions_%s e SET uuid = r.uuid FROM reports_%s r WHERE r.id = e.report_id" % parts[1])
    #conn.commit()
