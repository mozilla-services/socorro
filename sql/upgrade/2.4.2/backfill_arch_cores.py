#!/usr/bin/python

import sys
import os
import psycopg2
import psycopg2.extensions
import psycopg2.extras
from optparse import OptionParser

# backfills architecture and core information into reports_clean
# upgrade script for 2.4.X
# note that the columns should be created in a separate SQL statement

parser = OptionParser()
parser.add_option("-s", "--start", dest="startdate",
                  help="oldest date to backfill to", metavar="DATE",
                  default="2011-12-23")
parser.add_option("-d", "--database", dest="database_name",
                  help="database to be extracted", metavar="DBNAME",
                  default="breakpad")
parser.add_option("-m", "--memory", dest="dbmemory",
                  help="amount of memory to set for operations", metavar="MEM",
                  default="1GB")
(options, args) = parser.parse_args()

print "Backfilling reports_clean, one week at a time."

#connect to postgresql
conn = psycopg2.connect("dbname=%s user=postgres" % options.database_name)

conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

cur.execute("""SET maintenance_work_mem = %s""", ( options.dbmemory, ) )

#check if we've already been run
cur.execute("""SELECT count(*) FROM (
	SELECT architecture, cores 
	FROM reports_clean 
	WHERE date_processed > %s 
	LIMIT 100) 
	WHERE architecture IS NOT NULL""")
	
if cur.fetchone()[0] > 50:
	print "architecture and cores are already backfilled, exiting"
	exit

cur.execute("""SELECT rcparts.relname as rcname, repparts.relname as repname
FROM pg_stat_user_tables AS rcparts
	JOIn pg_stat_user_tables AS repparts
		ON week_begins_partition(rcparts.relname) =
			week_begins_partition(repparts.relname)
WHERE rcparts.relname LIKE 'reports_clean_20%%'
	and repparts.relname LIKE 'reports_20%%'
	and week_ends_partition(rcparts.relname) >= %s
ORDER BY rcparts.relname;""", ( options.startdate, ))

partitions = cur.fetchall()

for partition in partitions:
    print "updating %s" % partition['rcname']
    
    #fill both columns
    fillsql = """
    UPDATE %s as reports_clean
		SET architecture = cpu_name,
		cores = get_cores(cpu_info)
	FROM %s as reports
	WHERE reports.uuid = reports_clean.uuid
		AND reports_clean.date_processed > '%s'
		AND reports.date_processed > '%s'
        """ % (partition['rcname'], partition['repname'], options.startdate, options.startdate,)
    cur.execute(fillsql)
    
    #vacuum analyze the table
    cur.execute("""VACUUM ANALYZE %s""" % partition['rcname'])
    
    #build the index
    indsql = "CREATE INDEX %s_arch_cores ON %s (architecture, cores)" % (partition['rcname'], partition['rcname'],)
    cur.execute(indsql)
    
print 'done backfilling archtecture and cores'
