#!/usr/bin/python
import sys
import psycopg2, psycopg2.extensions

# this script truncates the database down to 56 to 62 days of data
# for use in staging and/or dev environments

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

# get a list of reports partitions older than 62 days

cur.execute("""
   select relname from pg_stat_user_tables
   where relname like 'reports_20%%'
   and relname < 'reports_' || to_char(current_date - 62, 'YYYYMMDD')
   order by relname
   """ )

# drop all of the old partitions
# use cascade so it takes out frames, extensions, etc. too

partitions = [ x for ( x, ) in cur.fetchall() ]

for partition in partitions:
    cur.execute("DROP TABLE %s CASCADE" % ( partition, ))
	print "%s dropped." % partition

# delete data from top crashers

cur.execute("""
	DELETE FROM top_crashes_by_url_signature
	USING top_crashes_by_url
	WHERE top_crashes_by_url_id = top_crashes_by_url.id
	AND window_end < ( now() - interval '60 days')
	""")

cur.execute("""
	VACUUM FULL top_crashes_by_url_signature
	""")

cur.execute("""
	DELETE FROM top_crashes_by_url
	WHERE window_end < ( now() - interval '60 days')
	""")

cur.execute("""
	VACUUM FULL top_crashes_by_url
	""")

print "top crashes by url truncated"

cur.execute("""
	DELETE FROM top_crashes_by_signature
	WHERE window_end < ( now() - interval '60 days')
	""")

cur.execute("""
	VACUUM FULL top_crashes_by_signature
	""")

print "top_crashes_by_signature truncated"

# truncate raw_adu

cur.execute("""
	DELETE FROM raw_adu
	WHERE "date" < ( now() - interval '60 days')
	""")

cur.execute("""
	VACUUM FULL raw_adu
	""")

print "raw_adu truncated"

# analyze

cur.execute("""
	ANALYZE
	""")

print "done truncating"
